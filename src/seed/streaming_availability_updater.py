import sys
from os.path import abspath, dirname, join

# Adds root folder as a working directory.
# This is needed so that imports can be found.
root_dir = abspath(join(dirname(__file__), '../../'))  # nopep8
sys.path.append(root_dir)  # nopep8

# --------------------------------------------------

import time

import requests

from src.adapters.streaming_availability_adapter import \
    store_movie_and_streaming_options
from src.app import RAPID_API_KEY, create_app
from src.exceptions.StreamingAvailabilityApiError import \
    StreamingAvailabilityApiError
from src.models.common import connect_db, db
from src.models.country_service import CountryService
from src.seed.common_constants import (
    STREAMING_AVAILABILITY_API_REQUEST_RATE_LIMIT_PER_DAY,
    STREAMING_AVAILABILITY_API_REQUEST_RATE_LIMIT_PER_SECOND)
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
    """

    countries_services = db.session.query(CountryService).all()
    countries_services = CountryService.convert_list_to_dict(countries_services)

    from_timestamps = read_json_file_helper(next_timestamps_file_location)

    num_requests = 0
    for country_code, service_ids in countries_services.items():
        has_more = True

        while has_more:
            for i in range(STREAMING_AVAILABILITY_API_REQUEST_RATE_LIMIT_PER_SECOND):
                try:
                    has_more, next_from_timestamp = get_updated_movies_and_streams_from_one_request(
                        country_code, service_ids, from_timestamps.get(country_code))
                except StreamingAvailabilityApiError:
                    return

                num_requests += 1

                if next_from_timestamp:
                    from_timestamps[country_code] = next_from_timestamp
                    write_json_file_helper(next_timestamps_file_location, from_timestamps)

                if num_requests >= STREAMING_AVAILABILITY_API_REQUEST_RATE_LIMIT_PER_DAY * 0.8:
                    return

                if not has_more:
                    break

            if has_more:
                # sleep needed due to Streaming Availability API request rate limit per second
                time.sleep(1)


def get_updated_movies_and_streams_from_one_request(
        country_code: str, service_ids: list[str], from_timestamp: int = None
) -> tuple[bool, int | None]:
    """
    Updates records for movies and streaming_options tables with data from one API request.  Can optionally accept
    a "from" timestamp to start getting changes from.

    If "from" timestamp is too old, Streaming Availability API will return a response with status code 400.
    This function will attempt to make another call, but without the "from" timestamp.

    If there are no updates, then this function will exit immediately, indicating that there is no more data to
    retrieve, as well as no next "from" timestamp to start at.  Otherwise, a next "from" timestamp will be returned, so
    that the same updates are not retrieved again from SA API.

    Returns a boolean, indicating if there are more to retrieve, and an integer if there is a timestamp to save or None
    if there isn't.  This can also raise an exception if the response has an unexpected status code.

    :param country_code: The country's code to get data for.
    :param service_ids: A list of streaming service IDs.  This can not be empty.
    :param from_timestamp: An optional timestamp to use for the "from" query parameter for fetching changes from
        Streaming Availability API.  This is the start time to begin looking up changes and must be within 31 days
        from right now.
    :return: A tuple with first item indicating if there is more data to retrieve and second item being the next "from"
        timestamp to start at.  The second item can be None, such as when there aren't any changes found.
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
    logger.info(f'Called {url} and received status {resp.status_code}.')

    # handle response
    body = resp.json()
    if resp.status_code == 200:

        # if there are no updates, then exit immediately
        if not body['shows']:
            logger.warn(f'There are no updates for {country_code}.')
            return (False, None)

        # store data
        for show in body['shows'].values():
            store_movie_and_streaming_options(show)

        if body['hasMore']:
            # if there's another page of data, return first part of next cursor
            next_from_timestamp = int(body['nextCursor'].split(':', 1)[0])
            logger.debug('Response has more results.')
        else:
            # else return last change's timestamp + 1
            next_from_timestamp = body['changes'][-1]['timestamp'] + 1
            logger.debug('Response has no more results.')

        logger.info(f'Next "from" timestamp is {next_from_timestamp}.')
        return (body['hasMore'], next_from_timestamp)

    elif resp.status_code == 400 and 'parameter "from" cannot be more than 31 days in the past' in body['message']:
        # if "from" timestamp is too old, try again without "from" attribute
        logger.warn('"from" timestamp is too old, retrying without "from".')
        return get_updated_movies_and_streams_from_one_request(country_code, service_ids)

    else:
        logger.error(f'Unsuccessful response from API: '
                     f'status code {resp.status_code}: {body.get('message')}.')
        raise StreamingAvailabilityApiError(f'Status code {resp.status_code}: {body.get('message')}.')


# ==================================================


if __name__ == "__main__":
    app = create_app("freestreammovies")
    connect_db(app)
    with app.app_context():
        get_updated_movies_and_streaming_options()
