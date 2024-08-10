from pathlib import Path

from models.common import db
from models.movie import Movie
from models.streaming_option import StreamingOption
from util.file_handling import read_services_blacklist
from util.logger import create_logger

# ==================================================

BLACKLISTED_SERVICES = read_services_blacklist()

log_file_name = Path(__file__).stem
logger = create_logger(__name__, f'src/logs/{log_file_name}.log')

# --------------------------------------------------


def convert_show_json_into_movie_object(show: dict) -> Movie:
    """
    Converts Streaming Availability's Show object into a Movie object.

    @param {dict} show - The JSON Show object retrieved from a response from Streaming Availability.
    @returns {Movie} Movie object.
    """

    return Movie(
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


def convert_streaming_option_json_into_object(
        streaming_option: dict, movie_id: str, country_code: str
) -> StreamingOption | None:
    """
    Converts Streaming Availability's Show object's streaming option into a StreamingOption object.

    @param {dict} streaming_option - The JSON streamingOption object retrieved within a Show object from Streaming
    Availability.
    @param {str} movie_id - The movie ID that this streaming_option belongs to.
    @param {str} country_code - The country that this streaming_option belongs to.
    @returns {StreamingOption or None} A StreamingOption if successful.  If the streaming option is not free or is
    blacklisted, then return None.
    """

    if streaming_option['type'] == 'free' \
            and streaming_option['service']['id'].lower() not in BLACKLISTED_SERVICES:

        return StreamingOption(
            movie_id=movie_id,
            country_code=country_code,
            service_id=streaming_option['service']['id'],
            link=streaming_option['link'],
            expires_soon=streaming_option['expiresSoon'],
            expires_on=streaming_option.get('expiresOn')
        )


def store_streaming_options(streaming_options: dict, movie_id: str) -> None:
    """
    Goes through lists of streaming options from within a Show object from Streaming Availability
    and adds them to the database.

    @param {dict} streaming_options - The JSON streamingOptions object retrieved within a Show object from Streaming
    Availability.  This is the plural form, which contains a dictionary of countries, where each country contains
    lists of streaming options.
    @param {str} movie_id - The movie ID that this streaming_options belongs to.
    """

    for country_code, streaming_options in streaming_options.items():
        for streaming_option in streaming_options:
            streaming_option_object = convert_streaming_option_json_into_object(
                streaming_option, movie_id, country_code)

            if streaming_option_object:
                logger.info(f'Adding {streaming_option_object.movie_id}-'
                            f'{streaming_option_object.country_code}-'
                            f'{streaming_option_object.service_id} '
                            f'streaming option to session.')
                db.session.add(streaming_option_object)

    db.session.commit()


def store_movie_and_streaming_options(show: dict) -> None:
    """
    Stores the movie and its streaming options from a Show object from Streaming Availability.

    @param {dict} show - The JSON Show object retrieved from a response from Streaming Availability.
    """

    movie = convert_show_json_into_movie_object(show)
    logger.info(f'Adding Movie {movie.id} ({movie.title}) to session.')
    db.session.add(movie)
    db.session.commit()

    store_streaming_options(show['streamingOptions'], show['id'])
