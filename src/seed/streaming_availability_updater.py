import sys
from os.path import abspath, dirname, join

# Adds root folder as a working directory.
# This is needed so that imports can be found.
root_dir = abspath(join(dirname(__file__), '../../'))  # nopep8
sys.path.append(root_dir)  # nopep8

# --------------------------------------------------

import time

import requests

from src.app import RAPID_API_KEY, create_app
from src.exceptions.StreamingAvailabilityApiError import \
    StreamingAvailabilityApiError
from src.exceptions.UpsertError import UpsertError
from src.models.common import connect_db, db
from src.models.country_service import CountryService
from src.models.movie import Movie
from src.models.movie_poster import MoviePoster
from src.models.streaming_option import StreamingOption
from src.seed.seed_updater_constants import (
    SA_API_PREFERRED_REQUEST_RATE_LIMIT_PER_DAY,
    STREAMING_AVAILABILITY_API_REQUEST_RATE_LIMIT_PER_SECOND)
from src.seed.seeder_updater_helpers import (
    delete_country_movie_streaming_options, make_unique_transformed_show_data)
from src.util.file_handling import (read_json_file_helper,
                                    write_json_file_helper)
from src.util.logger import create_logger

# ==================================================

next_timestamps_file_location = 'src/seed/streaming_availability_updater_next_timestamps.json'

logger = create_logger(__name__, 'src/logs/update.log')

# --------------------------------------------------


def get_updated_movies_and_streaming_options() -> None:
    """
    Updates records for movies and streaming options for all countries and free streaming services. This will
    make multiple calls to Streaming Availability API, up to 80% of the daily limit.

    This will retrieve and save the next timestamps to start at.  The timestamps will be saved into a JSON file.
    Timestamps will be in the format {country: timestamp}, because all streaming services at SA API will be queried for
    a given country.  If a new service is introduced in SA API, its movies will be added at a later timestamp, and
    therefore, will be covered using this format.

    If the rate limit is reached or if there is an exception when retrieving updated data, then this function will
    save all data retrieved so far and exit.
    """

    countries_services = db.session.query(CountryService).all()
    countries_services = CountryService.convert_list_to_dict(countries_services)

    from_timestamps = read_json_file_helper(next_timestamps_file_location)

    data_for_all_shows = {'movies': {}, 'movie_posters': {}, 'streaming_options': {}}

    num_requests = 0
    should_continue = True
    for country_code, service_ids in countries_services.items():
        has_more = True

        while has_more and should_continue:
            for i in range(STREAMING_AVAILABILITY_API_REQUEST_RATE_LIMIT_PER_SECOND):
                # make a request
                try:
                    transformed_request_data = get_updated_movies_and_streams_from_one_request(
                        country_code, service_ids, from_timestamps.get(country_code))
                except StreamingAvailabilityApiError:
                    should_continue = False
                    break

                # update and check total number of requests made
                num_requests += 1
                if num_requests >= SA_API_PREFERRED_REQUEST_RATE_LIMIT_PER_DAY:
                    should_continue = False

                # add transformed movie and etc. data to data_for_all_shows
                for k in data_for_all_shows:
                    if k in transformed_request_data:
                        data_for_all_shows[k].update(transformed_request_data[k])

                # saving the next from_timestamp
                if transformed_request_data['next_from_timestamp']:
                    from_timestamps[country_code] = transformed_request_data['next_from_timestamp']
                    write_json_file_helper(next_timestamps_file_location, from_timestamps)

                has_more = transformed_request_data['has_more']

                if not has_more:
                    break

            if has_more and should_continue:
                # sleep needed due to Streaming Availability API request rate limit per second
                time.sleep(1)

        if not should_continue:
            break

    logger.info(f'Number of requests made: {num_requests}.')

    # adding movie, poster, and streaming option data to database
    Movie.upsert_database(list(data_for_all_shows['movies'].values()))
    MoviePoster.upsert_database(list(data_for_all_shows['movie_posters'].values()))
    StreamingOption.insert_database(list(data_for_all_shows['streaming_options'].values()))

    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        message = 'Exception encountered when committing updated movie data.'
        logger.error(f'{message}\n'
                     f'Error is {type(e)}:\n'
                     f'{e}')
        raise UpsertError(message)


def get_updated_movies_and_streams_from_one_request(
        country_code: str, service_ids: list[str], from_timestamp: int = None
) -> dict:
    """
    Updates records for movies and streaming_options tables with data from one API request.  Can optionally accept
    a "from" timestamp to start getting changes from.

    If "from" timestamp is too old, Streaming Availability API will return a response with status code 400.
    This function will attempt to make another call, but without the "from" timestamp.

    If there are no updates, then this function will exit immediately, indicating that there is no more data to
    retrieve, as well as no next "from" timestamp to start at.  Otherwise, a next "from" timestamp will be returned, so
    that the same updates are not retrieved again from SA API.

    Returns a dict, containing movie and etc. data, an indication if there are more to retrieve, and an integer if there
    is a timestamp to save or None if there isn't.  This can also raise an exception if the response has an unexpected
    status code.

    :param country_code: The country's code to get data for.
    :param service_ids: A list of streaming service IDs.  This can not be empty.
    :param from_timestamp: An optional timestamp to use for the "from" query parameter for fetching changes from
        Streaming Availability API.  This is the start time to begin looking up changes and must be within 31 days
        from right now.
    :return: A dict containing movie and etc. data, whether there is more data to get, and the next timestamp to
        start at.
        {
            'movies': {
                'movie identifier': {movie attributes}
            },
            'movie_posters': {
                'poster identifier': {movie poster attributes},
                ...
            },
            'streaming_options': {
                'streaming options identifier': {streaming option attributes},
                ...
            },
            'has_more': bool,
            'next_from_timestamp': int | None
        }
    :raise StreamingAvailabilityApiError: If Streaming Availability API returns a response with status code that is
        not 200, or a response that does not indicate that it is due to client error.
    """

    # set up variables
    url = 'https://streaming-availability.p.rapidapi.com/changes'
    headers = {'X-RapidAPI-Key': RAPID_API_KEY}

    catalogs = ', '.join([service_id + '.free' for service_id in service_ids])
    querystring = {'change_type': 'updated', 'country': country_code, 'item_type': 'show',
                   'show_type': 'movie', 'catalogs': catalogs}
    if from_timestamp:
        querystring['from'] = from_timestamp

    # call API
    resp = requests.get(url, headers=headers, params=querystring)
    logger.info(f'Called {url} for country "{country_code}" and received status {resp.status_code}.')

    # handle response
    body = resp.json()
    if resp.status_code == 200:

        # if there are no updates, then exit immediately
        if not body['shows']:
            logger.warn(f'There are no updates for {country_code}.')
            return {
                'has_more': False,
                'next_from_timestamp': None
            }

        # store data
        output = {
            'movies': {},
            'movie_posters': {},
            'streaming_options': {},
            'has_more': None,
            'next_from_timestamp': None
        }

        for show in body['shows'].values():
            delete_country_movie_streaming_options(show['id'], country_code)
            unique_transformed_show_data = make_unique_transformed_show_data(show)
            for k in unique_transformed_show_data:
                output[k].update(unique_transformed_show_data[k])

        if body['hasMore']:
            # if there's another page of data, return first part of next cursor
            next_from_timestamp = int(body['nextCursor'].split(':', 1)[0])
            logger.debug('Response has more results.')
        else:
            # else return last change's timestamp + 1
            next_from_timestamp = body['changes'][-1]['timestamp'] + 1
            logger.debug('Response has no more results.')

        logger.info(f'Next "from" timestamp is {next_from_timestamp}.')
        output['next_from_timestamp'] = next_from_timestamp

        output['has_more'] = body['hasMore']

        return output

    elif resp.status_code == 400 and 'parameter "from" cannot be more than 31 days in the past' in body['message']:
        # if "from" timestamp is too old, try again without "from" attribute
        logger.warn('"from" timestamp is too old, retrying without "from".')
        return get_updated_movies_and_streams_from_one_request(country_code, service_ids)

    else:
        logger.error(f'Unsuccessful response from API: '
                     f'status code {resp.status_code}: {body.get('message')}.')
        raise StreamingAvailabilityApiError(body.get('message'), resp.status_code)


# ==================================================


if __name__ == "__main__":
    app = create_app("freestreammovies")
    connect_db(app)
    with app.app_context():
        get_updated_movies_and_streaming_options()
