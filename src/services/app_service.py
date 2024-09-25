import os

import requests

from src.adapters.streaming_availability_adapter import (
    convert_show_json_into_movie_object, transform_show)
from src.exceptions.StreamingAvailabilityApiError import \
    StreamingAvailabilityApiError
from src.exceptions.UpsertError import UpsertError
from src.models.common import db
from src.models.movie import Movie
from src.models.movie_poster import MoviePoster
from src.models.streaming_option import StreamingOption
from src.util.logger import create_logger

# ==================================================

RAPID_API_KEY = os.environ.get('RAPID_API_KEY')

logger = create_logger(__name__, 'src/logs/app.log')

# --------------------------------------------------


class AppService:
    """Service-level code for app."""

    def __init__(self):
        self.STREAMING_AVAILABILITY_BASE_URL = 'https://streaming-availability.p.rapidapi.com'

    def search_movies_by_title(self, country_code: str, title: str) -> list:
        """
        Calls Streaming Availability API to search for a movie by title and country.
        Response contains a list of movies.

        :param country_code: The country to find the streaming options for.
        :param title: The movie title to search for.
        :return: The JSON movies data retrieved from Streaming Availability API.
            See "https://docs.movieofthenight.com/resource/shows#search-shows-by-title".
        :raise StreamingAvailabilityApiError: If the API response status code is not 200.
        """

        logger.info(f'Searching for movie "{title}" in country "{country_code}".')

        url = f'{self.STREAMING_AVAILABILITY_BASE_URL}/shows/search/title'
        headers = {'X-RapidAPI-Key': RAPID_API_KEY}
        querystring = {'country': country_code,
                       'title': title,
                       'show_type': 'movie'}

        resp = requests.get(url, headers=headers, params=querystring)

        if resp.status_code == 200:
            movies = resp.json()

            logger.info(f'{len(movies)} movies found.')
            logger.debug([f'{movie['id']}: {movie['title']}' for movie in movies])

            return movies

        else:
            logger.error(f'Unsuccessful response from Streaming Availability API when searching for movie "{title}".\n'
                         f'Status code: {resp.status_code}.\n'
                         f'Message: {resp.json()['message']}.')
            raise StreamingAvailabilityApiError(f'Error when searching for movie "{title}".', resp.status_code)

    def get_movie_data(self, movie_id: str) -> Movie:
        """
        Calls Streaming Availability API to retrieve data for a movie by ID.  Stores movie, poster, and streaming
        option data into database.

        :param movie_id: The movie ID to get data for.
        :return: A Movie object belonging to the movie ID.
        :raise UpsertError: If committing data to database fails.
        :raise StreamingAvailabilityApiError: If Streaming Availability API returns a status code that is not 200.
        """

        logger.info(f'Retrieving details for movie ID {movie_id}.')

        url = f"{self.STREAMING_AVAILABILITY_BASE_URL}/shows/{movie_id}"
        headers = {'X-RapidAPI-Key': RAPID_API_KEY}

        resp = requests.get(url, headers=headers)
        show = resp.json()

        if resp.status_code == 200:
            logger.info(f'Successfully retrieved movie details for {show['id']}: {show['title']}.')

            data = transform_show(show)
            Movie.upsert_database(data['movies'])
            MoviePoster.upsert_database(data['movie_posters'])
            StreamingOption.insert_database(data['streaming_options'])

            try:
                db.session.commit()
                logger.info(f'Successfully committed movie details to database for {show['id']}: {show['title']}.')
            except Exception as e:
                db.session.rollback()
                logger.error('Exception encountered when visiting movie details webpage '
                             'and committing new movie data to database.\n'
                             f'Movie is {show['id']}: {show['title']}.\n'
                             f'Error is {type(e)}:\n'
                             f'{str(e)}')
                raise UpsertError('Server exception encountered when saving movie data.')

            # Temporary Movie object used to store data.
            # This is different than the same Movie retrieved from the database.
            # Do not add to database session.
            movie = convert_show_json_into_movie_object(show)

            logger.info(f'Returning Movie object for {show['id']}: {show['title']}.')
            logger.debug(f'Returning Movie object:\n{movie}')

            return movie

        else:
            logger.error('Unsuccessful response from Streaming Availability API ' +
                         f'when retrieving details for movie ID {movie_id}.\n'
                         f'Status code: {resp.status_code}.\n'
                         f'Message: {resp.json()['message']}.')
            raise StreamingAvailabilityApiError(
                f'Error when getting movie details for movie ID {movie_id}.',
                resp.status_code
            )
