import time
from pathlib import Path

from src.common_constants import BLACKLISTED_SERVICES
from src.models.movie import Movie
from src.models.movie_poster import MoviePoster
from src.models.streaming_option import StreamingOption
from src.util.case_transform import CamelToSnake
from src.util.logger import create_logger

# ==================================================

log_file_name = Path(__file__).stem
logger = create_logger(__name__, f'src/logs/{log_file_name}.log')

# --------------------------------------------------


def convert_show_json_into_movie_object(show: dict, existing_obj: Movie = None) -> Movie:
    """
    Converts Streaming Availability's Show object into a Movie object.
    An existing Movie can be passed in to update it, instead of creating a new Movie object.

    :param show: The JSON Show object retrieved from a response from Streaming Availability.
    :param existing_obj: A Movie, that was already retrieved from the database, to be updated.
    :return: Movie object.
    """

    movie = existing_obj or Movie()

    movie.id = show['id']
    movie.imdb_id = show['imdbId']
    movie.tmdb_id = show['tmdbId']
    movie.title = show['title']
    movie.overview = show['overview']
    movie.release_year = show.get('releaseYear')
    movie.original_title = show['originalTitle']
    movie.directors = show.get('directors')
    movie.cast = show['cast']
    movie.rating = show['rating']
    movie.runtime = show.get('runtime')

    logger.debug(f'Movie = {movie}.')
    return movie


def transform_show_json_into_movie_dict(show: dict) -> dict:
    """
    Transforms Streaming Availability API's show JSON into a dictionary containing the attributes of Movie.
    This does not take the data about movie posters or streaming options, just info about a movie.

    :param show: A Show JSON from Streaming Availability API.
    :return: A dict containing Movie attributes.
    """

    movie = {}

    for attr, val in show.items():
        attr = CamelToSnake.transform(attr)

        if attr in Movie.__table__.columns.keys():
            movie[attr] = val

    logger.debug(f'Transformed movie = {movie}.')
    return movie


def transform_streaming_option_json_into_dict(
        streaming_option_data: dict, movie_id: str, country_code: str
) -> dict:
    """
    Transforms Streaming Availability API's show's streaming option JSON into a dictionary
    containing the attributes of StreamingOption.

    :param streaming_option_data: JSON data for one streaming option.
    :param movie_id: The movie ID that the streaming option data belongs to.
    :param country_code: The country code that the streaming option data belongs to.
    :return: A dict containing StreamingOption attributes.
    """

    streaming_option = {}

    for attr, val in streaming_option_data.items():
        attr = CamelToSnake.transform(attr)

        if attr in StreamingOption.__table__.columns.keys():
            streaming_option[attr] = val

    streaming_option['movie_id'] = movie_id
    streaming_option['country_code'] = country_code
    streaming_option['service_id'] = streaming_option_data['service']['id']

    logger.debug(f'Transformed streaming option = {streaming_option}.')
    return streaming_option


def transform_image_set_json_into_movie_poster_list(image_set: dict, movie_id: str) -> list[dict]:
    """
    Transforms Streaming Availability API's show's image set JSON into a dictionary
    containing the attributes of MoviePoster.

    :param image_set: A movie's image set JSON, which contains the poster types, sizes, and links.
    :param movie_id: The movie ID that the image set belongs to.
    :return: A list of dicts containing MoviePoster attributes.
    """

    movie_posters = []

    for poster_type in MoviePoster.Types:
        for poster_size, link in image_set[poster_type].items():
            # if there are horizontal types, put them in this if statement
            if 'vertical' in poster_type.lower() and poster_size.lower() in MoviePoster.VerticalSizes:

                movie_posters.append({
                    'movie_id': movie_id,
                    'type': poster_type,
                    'size': poster_size,
                    'link': link
                })

    logger.debug(f'Transformed movie posters = {movie_posters}')
    return movie_posters


def gather_streaming_options(country_streaming_options_data: dict, movie_id: str) -> list[dict]:
    """
    Goes through lists of streaming options from within a Show object from Streaming Availability
    and transforms free options into something usable by StreamingOption.

    :param country_streaming_options_data: The JSON streamingOptions object retrieved within a Show object from
        Streaming Availability.  This is the plural form, which contains a dictionary of countries, where each country
        contains lists of streaming options.
    :param movie_id: The movie ID that this country_streaming_options_data belongs to.
    :return: A list of dicts containing StreamingOption attributes.
    """

    current_timestamp = time.time()

    streaming_options = []
    for country_code, streaming_options_data in country_streaming_options_data.items():

        for streaming_option_data in streaming_options_data:
            if streaming_option_data['type'] == 'free' \
                    and streaming_option_data['service']['id'].lower() not in BLACKLISTED_SERVICES \
                    and (streaming_option_data['expiresOn'] > current_timestamp
                         if 'expiresOn' in streaming_option_data else True):

                streaming_option = transform_streaming_option_json_into_dict(
                    streaming_option_data, movie_id, country_code)
                streaming_options.append(streaming_option)

    for streaming_option in streaming_options:
        logger.info(f'Transformed {streaming_option['movie_id']}-'
                    f'{streaming_option['country_code']}-'
                    f'{streaming_option['service_id']}.')
    return streaming_options


def transform_show(show: dict) -> dict:
    """
    Transforms a show JSON dict from Streaming Availability API into a dictionary containing lists of Movie,
    MoviePoster, and StreamingOption attributes in dictionary form.

    :param show: The JSON Show object retrieved from a response from Streaming Availability.
    :return: {
        'movies': [{movie attributes}],
        'movie_posters': [{movie poster attributes}, {...}, ...],
        'streaming_options': [{streaming option attributes}, {...}, ...]
    }
    """

    output = {}

    movie = transform_show_json_into_movie_dict(show)
    logger.info(f'Transformed Movie {movie['id']} ({movie['title']}).')
    output['movies'] = [movie]

    movie_posters = transform_image_set_json_into_movie_poster_list(
        show['imageSet'], show['id'])
    logger.info(f'Transformed {len(movie_posters)} posters from Movie {show['id']} '
                f'({show['title']}).')
    output['movie_posters'] = movie_posters

    streaming_options = gather_streaming_options(show['streamingOptions'], show['id'])
    logger.info(f'Transformed {len(streaming_options)} streaming options for Movie {show['id']} '
                f'({show['title']}).')
    output['streaming_options'] = streaming_options

    return output
