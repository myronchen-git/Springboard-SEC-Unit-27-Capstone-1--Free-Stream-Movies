import sys
from os.path import abspath, dirname, join

# Adds root folder as a working directory.
# This is needed so that imports can be found.
root_dir = abspath(join(dirname(__file__), '../../'))  # nopep8
sys.path.append(root_dir)  # nopep8

# --------------------------------------------------

import time

import requests
from requests.exceptions import RequestException
from sqlalchemy.exc import DBAPIError

from src.app import RAPID_API_KEY, create_app
from src.common_constants import BLACKLISTED_SERVICES
from src.exceptions.base_exceptions import FreeStreamMoviesServerError
from src.exceptions.DatabaseError import DatabaseError
from src.exceptions.UpsertError import UpsertError
from src.models.common import connect_db, db
from src.models.country_service import CountryService
from src.models.movie import Movie
from src.models.movie_poster import MoviePoster
from src.models.service import Service
from src.models.streaming_option import StreamingOption
from src.seed.seed_updater_constants import \
    STREAMING_AVAILABILITY_API_REQUEST_RATE_LIMIT_PER_SECOND
from src.seed.seeder_updater_helpers import (
    delete_country_movie_streaming_options, make_unique_transformed_show_data)
from src.util.file_handling import (read_json_file_helper,
                                    write_json_file_helper)
from src.util.logger import create_logger

# ==================================================

cursor_file_location = 'src/seed/streaming_availability_cursors.json'

logger = create_logger(__name__, 'src/logs/seed.log')

# --------------------------------------------------


def seed_services() -> None:
    """
    Adds records to the services and countries_services tables.

    See https://docs.movieofthenight.com/resource/countries#get-all-countries
    """

    # set up variables
    url = "https://streaming-availability.p.rapidapi.com/countries"
    headers = {'X-RapidAPI-Key': RAPID_API_KEY}

    # call API
    resp = requests.get(url, headers=headers)

    if resp.status_code == 200:
        added_services = set()

        # storing data for each service
        for country_code, country_data in resp.json().items():
            for service in country_data['services']:
                service_id = service['id']

                # only services that have free movies and not those that are incorrectly labeled as free
                if service['streamingOptionTypes']['free'] and service_id.lower() not in BLACKLISTED_SERVICES:
                    # creating Service Object
                    s = Service(
                        id=service_id,
                        name=service['name'],
                        home_page=service['homePage'],
                        theme_color_code=service['themeColorCode'],
                        light_theme_image=service['imageSet']['lightThemeImage'],
                        dark_theme_image=service['imageSet']['darkThemeImage'],
                        white_image=service['imageSet']['whiteImage']
                    )
                    logger.debug(f'Service = {s}.')

                    # creating CountryService Object
                    cs = CountryService(
                        country_code=country_code,
                        service_id=service_id
                    )
                    logger.debug(f'CountryService = {cs}.')

                    # adding Service to session while prevent duplicate service data,
                    # which will happen because countries will have the same services
                    if service_id not in added_services:
                        logger.info(f'Adding {service_id} to session.')
                        db.session.add(s)
                        added_services.add(service_id)

                    # adding CountryService to session
                    logger.info(
                        f'Adding {country_code}-{service['id']} to session.')
                    db.session.add(cs)

        # finally committing the data, all at once, to avoid multiple writes to database
        logger.debug('Committing services and countries-services.')
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            message = 'Exception encountered when committing new services to database.'
            logger.error(f'{message}\n'
                         f'Error is {type(e)}:\n'
                         f'{str(e)}')
            raise DatabaseError(message)

    else:
        logger.error(f'Unsuccessful response from API: '
                     f'status code {resp.status_code}: {resp.text}.')


def get_movies_and_streams_from_one_request(country_code: str, service_ids: list[str], cursor: str = None) -> dict:
    """
    Gets data for movies, movie_posters, and streaming_options tables from one API request, and returns it.
    Returns the next cursor if there are more records to get, or returns 'end' if there aren't.
    Deletes existing movies' streaming options, since it is not possible to find the outdated option belonging
    to an updated option.
    If the HTTP response status code from the API is not 200, then None is returned.

    See https://docs.movieofthenight.com/resource/shows#search-shows-by-filters

    :param country_code: The country code of the country to get data for.
    :param service_ids: A list of streaming service IDs to get data for.  This can not be empty.
    :param cursor: The next cursor (movie) to use for getting the next page of results.
        This has the form "ID:NAME" or "ID:RATING".
        This would be None if getting the first page of results.
    :return: A dict {'movies', 'movie_posters', 'streaming_options', 'next_cursor'}.
        movies, movie_posters, and streaming_options contain all the necessary model data,
        transformed from the Show JSON.
        next_cursor contains the next cursor (movie) to start at, if there are more results, or
        "end" if there is no more results to get.
        Returns None if response is not 200.
    """

    # set up variables
    url = "https://streaming-availability.p.rapidapi.com/shows/search/filters"
    headers = {'X-RapidAPI-Key': RAPID_API_KEY}

    catalogs = ', '.join([service_id + '.free' for service_id in service_ids])
    querystring = {"country": country_code,
                   "order_by": "original_title",
                   "catalogs": catalogs,
                   "show_type": "movie"}
    if cursor:
        querystring['cursor'] = cursor

    # call API
    try:
        resp = requests.get(url, headers=headers, params=querystring)
    except RequestException as e:
        message = 'Exception occurred when attempting to make one HTTP request to ' + \
            'Streaming Availability API to search shows by filters.'
        logger.error(f'{message}\n'
                     f'Error is {type(e)}:\n'
                     f'{str(e)}')
        raise FreeStreamMoviesServerError(message)

    if resp.status_code == 200:
        body = resp.json()

        output = {
            'movies': {},
            'movie_posters': {},
            'streaming_options': {},
            'next_cursor': None
        }

        # store data
        for show in body['shows']:
            delete_country_movie_streaming_options(show['id'], country_code)
            unique_transformed_show_data = make_unique_transformed_show_data(show)
            for k in unique_transformed_show_data:
                output[k].update(unique_transformed_show_data[k])

        # if there's another page of data, return next starting point, else return 'end'
        if body['hasMore']:
            logger.info(f'Response has more results.  '
                        f'Next cursor is "{body['nextCursor']}".')
            output['next_cursor'] = body['nextCursor']
        else:
            output['next_cursor'] = 'end'

        return output

    else:
        logger.error(f'Unsuccessful response from API: '
                     f'status code {resp.status_code}: {resp.json()['message']}.')


def seed_movies_and_streams() -> None:
    """
    Adds records to the movies, movie_posters, and streaming_options tables for all countries
    and free streaming services.

    This will save the next cursor (movie), which will be used to get the next page of
    movie data for a specified country.  In other words, there is bookmarking.

    Cursors will be in a dictionary containing country codes, where each country code
    contains the next cursor to use.  When reading the cursors file, it is possible that
    cursors will be an empty dict.
    ({country: cursor, country: cursor, ...})

    Cursors will be saved into a JSON file.
    """

    try:
        countries_services = db.session.query(CountryService).all()
    except DBAPIError as e:
        db.session.rollback()
        message = 'Exception encountered when getting countries-services during seeding.'
        logger.error(f'{message}\n'
                     f'Error is {type(e)}:\n'
                     f'{str(e)}')
        raise DatabaseError(message)

    countries_services = CountryService.convert_list_to_dict(countries_services)

    cursors = read_json_file_helper(cursor_file_location)

    data_for_all_shows = {'movies': {}, 'movie_posters': {}, 'streaming_options': {}}

    for country_code, service_ids in countries_services.items():
        logger.info(f'Seeding movies and streaming options for '
                    f'country "{country_code}" and services "{service_ids}".')

        cursor = cursors.get(country_code)
        logger.debug(f'Saved next cursor is: "{cursor}".')

        # repeat requests due to Streaming Availability API rate limit
        while cursor != 'end':
            for i in range(STREAMING_AVAILABILITY_API_REQUEST_RATE_LIMIT_PER_SECOND):
                cursor_and_data = get_movies_and_streams_from_one_request(country_code, service_ids, cursor)

                if cursor_and_data:
                    for k in data_for_all_shows:
                        data_for_all_shows[k].update(cursor_and_data[k])

                    cursor = cursor_and_data['next_cursor']
                    cursors[country_code] = cursor
                    write_json_file_helper(cursor_file_location, cursors)

                if not cursor_and_data or cursor == 'end':
                    break

            if not cursor_and_data or cursor == 'end':
                break

            # sleep needed due to Streaming Availability API request rate limit per second
            time.sleep(1)

    Movie.upsert_database(list(data_for_all_shows['movies'].values()))
    MoviePoster.upsert_database(list(data_for_all_shows['movie_posters'].values()))
    StreamingOption.insert_database(list(data_for_all_shows['streaming_options'].values()))

    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        message = 'Exception encountered when committing new movie data.'
        logger.error(f'{message}\n'
                     f'Error is {type(e)}:\n'
                     f'{str(e)}')
        raise UpsertError(message)

# ==================================================


if __name__ == "__main__":
    app = create_app("freestreammovies")
    connect_db(app)
    with app.app_context():
        db.create_all()
        # seed_services()
        seed_movies_and_streams()
