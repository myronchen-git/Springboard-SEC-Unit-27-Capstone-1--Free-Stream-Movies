from pathlib import Path

from src.models.common import db
from src.models.movie import Movie
from src.models.movie_poster import MoviePoster
from src.models.streaming_option import StreamingOption
from src.util.file_handling import read_services_blacklist
from src.util.logger import create_logger

# ==================================================

BLACKLISTED_SERVICES = read_services_blacklist()

log_file_name = Path(__file__).stem
logger = create_logger(__name__, f'src/logs/{log_file_name}.log')

# --------------------------------------------------


def convert_show_json_into_movie_object(show: dict) -> Movie:
    """
    Converts Streaming Availability's Show object into a Movie object.

    :param show: The JSON Show object retrieved from a response from Streaming Availability.
    :return: Movie object.
    """

    movie = Movie(
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

    logger.debug(f'Movie = {movie}.')
    return movie


def convert_streaming_option_json_into_object(
        streaming_option: dict, movie_id: str, country_code: str
) -> StreamingOption | None:
    """
    Converts Streaming Availability's Show object's streaming option into a StreamingOption object.

    :param streaming_option: The JSON streamingOption object retrieved within a Show object from Streaming
        Availability.
    :param movie_id: The movie ID that this streaming_option belongs to.
    :param country_code: The country that this streaming_option belongs to.
    :return: A StreamingOption if successful.  If the streaming option is not free or is blacklisted,
        then return None.
    """

    if streaming_option['type'] == 'free' \
            and streaming_option['service']['id'].lower() not in BLACKLISTED_SERVICES:

        streaming_option = StreamingOption(
            movie_id=movie_id,
            country_code=country_code,
            service_id=streaming_option['service']['id'],
            link=streaming_option['link'],
            expires_soon=streaming_option['expiresSoon'],
            expires_on=streaming_option.get('expiresOn')
        )

        logger.debug(f'StreamingOption = {streaming_option}.')
        return streaming_option


def store_streaming_options(streaming_options: dict, movie_id: str) -> None:
    """
    Goes through lists of streaming options from within a Show object from Streaming Availability
    and adds them to the database.

    :param streaming_options: The JSON streamingOptions object retrieved within a Show object from Streaming
        Availability.  This is the plural form, which contains a dictionary of countries, where each country
        contains lists of streaming options.
    :param movie_id: The movie ID that this streaming_options belongs to.
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

    :param show: The JSON Show object retrieved from a response from Streaming Availability.
    """

    movie = convert_show_json_into_movie_object(show)
    logger.info(f'Adding Movie {movie.id} ({movie.title}) to session.')

    movie_posters = convert_image_set_json_into_movie_poster_objects(show['imageSet'], show['id'])
    logger.info(f'Adding {len(movie_posters)} posters from Movie {show['id']} ({show['title']}) to session.')

    db.session.add_all([movie, *movie_posters])
    db.session.commit()

    store_streaming_options(show['streamingOptions'], show['id'])


def convert_image_set_json_into_movie_poster_objects(image_set: dict, movie_id: str) -> list[MoviePoster]:
    """
    Converts Streaming Availability's Show object's image set of movie posters into MoviePoster objects.
    Currently, this just takes the vertical posters.

    :param image_set: The JSON imageSet object within a Show object from Streaming Availability.
    :return: A list of MoviePosters.
    """

    poster_type = 'verticalPoster'
    movie_posters = []

    for poster_size, link in image_set[poster_type].items():
        movie_posters.append(
            MoviePoster(
                movie_id=movie_id,
                type=poster_type,
                size=poster_size,
                link=link
            ))

    return movie_posters
