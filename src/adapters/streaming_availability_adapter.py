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


def convert_streaming_option_json_into_object(
        streaming_option_data: dict, movie_id: str, country_code: str
) -> StreamingOption | None:
    """
    Converts Streaming Availability's Show object's streaming option into a StreamingOption object.

    :param streaming_option_data: The JSON streamingOption object retrieved within a Show object from Streaming
        Availability.
    :param movie_id: The movie ID that this streaming_option_data belongs to.
    :param country_code: The country that this streaming_option_data belongs to.
    :return: A StreamingOption if successful.  If the streaming option is not free or is blacklisted,
        then return None.
    """

    if streaming_option_data['type'] == 'free' \
            and streaming_option_data['service']['id'].lower() not in BLACKLISTED_SERVICES:

        streaming_option = StreamingOption(
            movie_id=movie_id,
            country_code=country_code,
            service_id=streaming_option_data['service']['id'],
            link=streaming_option_data['link'],
            expires_soon=streaming_option_data['expiresSoon'],
            expires_on=streaming_option_data.get('expiresOn')
        )

        logger.debug(f'StreamingOption = {streaming_option}.')
        return streaming_option


def store_streaming_options(country_streaming_options_data: dict, movie_id: str) -> None:
    """
    Goes through lists of streaming options from within a Show object from Streaming Availability
    and adds them to the database.

    :param country_streaming_options_data: The JSON streamingOptions object retrieved within a Show object from
        Streaming Availability.  This is the plural form, which contains a dictionary of countries, where each country
        contains lists of streaming options.
    :param movie_id: The movie ID that this country_streaming_options_data belongs to.
    """

    for country_code, streaming_options_data in country_streaming_options_data.items():

        # Deleting old streaming options, since "updated" changes from Streaming Availability API can contain
        # additions, removals, and modifications.
        # It is also not easy to find an old StreamingOption, since there can be multiple streaming options
        # for a movie, country, and streaming service, such as when there are different languages for a movie.
        # Once there is a change, for example if the link changes, it might not be possible to find the old one.
        db.session.query(StreamingOption).filter_by(
            movie_id=movie_id,
            country_code=country_code
        ).delete()
        db.session.commit()

        for streaming_option_data in streaming_options_data:
            streaming_option_object = convert_streaming_option_json_into_object(
                streaming_option_data, movie_id, country_code)

            if streaming_option_object:
                logger.info(f'Adding/updating {streaming_option_object.movie_id}-'
                            f'{streaming_option_object.country_code}-'
                            f'{streaming_option_object.service_id} '
                            f'streaming option to session and database.')
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


def convert_image_set_json_into_movie_poster_objects(
        image_set: dict, movie_id: str, existing_objs: list[MoviePoster] = None
) -> list[MoviePoster]:
    """
    Converts Streaming Availability's Show object's image set of movie posters into MoviePoster objects.
    Currently, this just takes the vertical posters.
    A list of existing MoviePosters can be passed in to update them, instead of creating new MoviePoster objects.

    :param image_set: The JSON imageSet object within a Show object from Streaming Availability.
    :param movie_id: The movie ID that the posters belong to.
    :param existing_objs: List of MoviePosters, retrieved from the database, to be updated.
    :return: A list of MoviePosters.
    """

    poster_type = 'verticalPoster'
    movie_posters = []

    for poster_size, link in image_set[poster_type].items():
        existing_obj = None

        # find MoviePoster in list and pop it
        # iterating thru list is fine, since there will only be at most 4 types of posters, with 5 sizes for each
        if existing_objs:
            for i in range(len(existing_objs)):
                if existing_objs[i].type == poster_type and existing_objs[i].size == poster_size:
                    existing_obj = existing_objs.pop(i)
                    break

        movie_poster = existing_obj or MoviePoster()
        movie_poster.movie_id = movie_id
        movie_poster.type = poster_type
        movie_poster.size = poster_size
        movie_poster.link = link

        movie_posters.append(movie_poster)

    return movie_posters
