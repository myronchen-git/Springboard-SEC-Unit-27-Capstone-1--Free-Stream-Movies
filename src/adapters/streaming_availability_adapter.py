from pathlib import Path

from src.models.common import db
from src.models.movie import Movie
from src.models.movie_poster import MoviePoster
from src.models.streaming_option import StreamingOption
from src.util.case_transform import CamelToSnake
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

    existing_movie = db.session.query(Movie).get(show['id'])
    movie = convert_show_json_into_movie_object(show, existing_movie)

    existing_movie_posters = db.session.query(MoviePoster).filter_by(movie_id=show['id']).all()
    movie_posters = convert_image_set_json_into_movie_poster_objects(
        show['imageSet'], show['id'], existing_movie_posters)

    logger.info(f'Adding/updating Movie {movie.id} ({movie.title}) to session and database.')
    logger.info(f'Adding {len(movie_posters)} posters from Movie {show['id']} '
                f'({show['title']}) to session and database.')

    db.session.add_all([movie, *movie_posters])
    db.session.commit()

    store_streaming_options(show['streamingOptions'], show['id'])


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

    streaming_options = []
    for country_code, streaming_options_data in country_streaming_options_data.items():

        for streaming_option_data in streaming_options_data:
            if streaming_option_data['type'] == 'free' \
                    and streaming_option_data['service']['id'].lower() not in BLACKLISTED_SERVICES:

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
