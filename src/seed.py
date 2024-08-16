import sys
from os.path import abspath, dirname, join

# Adds root folder as a working directory.
# This is needed so that imports can be found.
root_dir = abspath(join(dirname(__file__), '../'))  # nopep8
sys.path.append(root_dir)  # nopep8

# --------------------------------------------------

import time

import requests

from src.adapters.streaming_availability_adapter import \
    convert_image_set_json_into_movie_poster_objects
from src.app import RAPID_API_KEY, create_app
from src.models.common import connect_db, db
from src.models.country_service import CountryService
from src.models.movie import Movie
from src.models.service import Service
from src.models.streaming_option import StreamingOption
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

    url = "https://streaming-availability.p.rapidapi.com/countries"
    headers = {'X-RapidAPI-Key': RAPID_API_KEY}

    resp = requests.get(url, headers=headers)

    if resp.status_code == 200:
        added_services = set()

        for country_code, country_data in resp.json().items():
            for service in country_data['services']:
                service_id = service['id']

                if service['streamingOptionTypes']['free'] and service_id.lower() not in BLACKLISTED_SERVICES:
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

                    cs = CountryService(
                        country_code=country_code,
                        service_id=service_id
                    )
                    logger.debug(f'CountryService = {cs}.')

                    if service_id not in added_services:
                        logger.info(f'Adding {service_id} to session.')
                        db.session.add(s)
                        added_services.add(service_id)

                    logger.info(
                        f'Adding {country_code}-{service['id']} to session.')
                    db.session.add(cs)

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

    url = "https://streaming-availability.p.rapidapi.com/shows/search/filters"
    headers = {'X-RapidAPI-Key': RAPID_API_KEY}
    querystring = {"country": country,
                   "order_by": "original_title",
                   "catalogs": f"{service_id}.free",
                   "show_type": "movie"}
    if cursor:
        querystring['cursor'] = cursor

    resp = requests.get(url, headers=headers, params=querystring)

    if resp.status_code == 200:
        body = resp.json()

        for show in body['shows']:
            m = Movie(
                id=show['id'],
                imdb_id=show['imdbId'],
                tmdb_id=show['tmdbId'],
                title=show['title'],
                overview=show['overview'],
                release_year=show.get('releaseYear'),
                original_title=show['originalTitle'],
                directors=show.get('directors'),
                cast=show['cast'],
                rating=show['rating'],
                runtime=show.get('runtime')
            )
            logger.debug(f'Movie = {m}.')

            logger.info(f'Adding Movie {show['id']} ({show['title']}) '
                        f'to session.')
            db.session.add(m)

            # adding movie posters
            movie_posters = convert_image_set_json_into_movie_poster_objects(show['imageSet'], show['id'])
            logger.info(f'Adding {len(movie_posters)} posters from Movie {show['id']} ({show['title']}) to session.')
            db.session.add_all(movie_posters)

            for country_code, streaming_options in show['streamingOptions'].items():
                for streaming_option in streaming_options:
                    if streaming_option['type'] == 'free' \
                            and streaming_option['service']['id'].lower() not in BLACKLISTED_SERVICES:

                        so = StreamingOption(
                            movie_id=show['id'],
                            country_code=country_code,
                            service_id=streaming_option['service']['id'],
                            link=streaming_option['link'],
                            expires_soon=streaming_option['expiresSoon'],
                            expires_on=streaming_option.get('expiresOn')
                        )
                        logger.debug(f'StreamingOption = {so}.')

                        logger.info(f'Adding {show['id']}-'
                                    f'{country_code}-'
                                    f'{streaming_option['service']['id']} '
                                    f'({show['title']}) '
                                    f'streaming option to session.')
                        db.session.add(so)

        logger.debug('Committing movies and streaming options.')
        db.session.commit()

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

    # countries_services = db.session.query(CountryService).all()
    # temp
    countries_services = db.session.query(
        CountryService).filter_by(country_code='us', service_id='tubi').all()

    for country_service in countries_services:
        logger.info(f'Seeding movies and streaming options for '
                    f'{country_service.country_code} and {country_service.service_id}.')
        cursor = None

        while True:
            # iterations needed due to Streaming Availability API request rate limit per second
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
