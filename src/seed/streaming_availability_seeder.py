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
from src.models.common import connect_db, db
from src.models.country_service import CountryService
from src.models.service import Service
from src.util.file_handling import read_services_blacklist
from src.util.logger import create_logger

# ==================================================

BLACKLISTED_SERVICES = read_services_blacklist()

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
        db.session.commit()

    else:
        logger.error(f'Unsuccessful response from API: '
                     f'status code {resp.status_code}: {resp.text}.')


def seed_movies_and_streams_from_one_request(country: str, service_id: str, cursor: str = None) -> str | None:
    """
    Adds records to the movies and streaming_options tables with data from one API request.
    Parameter country is country code.

    Returns the next cursor (movie) to start at, if there are more results.

    See https://docs.movieofthenight.com/resource/shows#search-shows-by-filters
    """

    # set up variables
    url = "https://streaming-availability.p.rapidapi.com/shows/search/filters"
    headers = {'X-RapidAPI-Key': RAPID_API_KEY}
    querystring = {"country": country,
                   "order_by": "original_title",
                   "catalogs": f"{service_id}.free",
                   "show_type": "movie"}
    if cursor:
        querystring['cursor'] = cursor

    # call API
    resp = requests.get(url, headers=headers, params=querystring)

    if resp.status_code == 200:
        body = resp.json()

        # store data
        for show in body['shows']:
            store_movie_and_streaming_options(show)

        # if there's another page of data, return next starting point
        if body['hasMore']:
            logger.info(f'Response has more results.  '
                        f'Next cursor is "{body['nextCursor']}".')
            return body['nextCursor']

    else:
        logger.error(f'Unsuccessful response from API: '
                     f'status code {resp.status_code}: {resp.json()['message']}.')


def seed_movies_and_streams() -> None:
    """
    Adds records to the movies and streaming_options tables
    for all countries and free streaming services.
    """

    # retrieve all countries and services
    # countries_services = db.session.query(CountryService).all()

    # during development, temporarily get data for US and Tubi instead of all
    countries_services = db.session.query(
        CountryService).filter_by(country_code='us', service_id='tubi').all()

    for country_service in countries_services:
        logger.info(f'Seeding movies and streaming options for '
                    f'{country_service.country_code} and {country_service.service_id}.')
        cursor = None

        # repeat requests due to Streaming Availability API rate limit
        while True:
            for i in range(10):
                cursor = seed_movies_and_streams_from_one_request(
                    country_service.country_code, country_service.service_id, cursor)

                if not cursor:
                    break

            if not cursor:
                break

            # sleep needed due to Streaming Availability API request rate limit per second
            time.sleep(1)

# ==================================================


app = create_app("freestreammovies")
connect_db(app)
with app.app_context():
    db.create_all()
    # seed_services()
    seed_movies_and_streams()
