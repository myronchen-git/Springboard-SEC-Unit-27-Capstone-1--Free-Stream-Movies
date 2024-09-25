from src.adapters.streaming_availability_adapter import transform_show
from src.exceptions.DatabaseError import DatabaseError
from src.models.common import db
from src.models.streaming_option import StreamingOption
from src.util.logger import create_logger

# ==================================================

logger = create_logger(__name__, 'src/logs/seeder_updater_helpers.log')

# --------------------------------------------------


def delete_country_movie_streaming_options(movie_id, country_code) -> None:
    """
    Deletes old streaming options belonging to both provided movie ID and country code,
    since "updated" changes from Streaming Availability API can contain additions, removals,
    and modifications.

    It is not easy to find an old StreamingOption, since there can be multiple streaming options
    for a movie, country, and streaming service, such as when there are different languages for a movie.
    Once there is a change, for example if the link changes, it might not be possible to find the old one.

    :param movie_id: The movie ID to delete streaming options for.
    :param country_code: The country to delete streaming options for.
    """

    try:
        db.session.query(StreamingOption).filter_by(
            movie_id=movie_id,
            country_code=country_code
        ).delete()
        db.session.commit()

    except Exception as e:
        db.session.rollback()
        logger.error('Exception encountered when deleting StreamingOptions.'
                     f'Error is {type(e)}:\n'
                     f'{e}')
        raise DatabaseError('Server exception encountered when deleting streaming options.')


def make_unique_transformed_show_data(show) -> dict:
    """
    Transforms the show JSON and puts results into dictionaries to remove duplicates.

    :param show: The JSON Show object retrieved from a response from Streaming Availability.
    :return: {
        'movies': {
            'movie identifier': {movie attributes}
        },
        'movie_posters': {
            'poster identifier': {movie poster attributes},
            ...
        },
        'streaming_options': {
            'streaming options identifier': {streaming option attributes},
            ...
        }
    }
    """

    output = {
        'movies': {},
        'movie_posters': {},
        'streaming_options': {},
    }

    transformed_show = transform_show(show)
    output['movies'].update({movie['id']: movie for movie in transformed_show['movies']})
    output['movie_posters'].update({
        f'{poster['movie_id']}-{poster['type']}-{poster['size']}': poster
        for poster in transformed_show['movie_posters']
    })
    output['streaming_options'].update({
        f'{option['movie_id']}-{option['country_code']}-{option['service_id']}-{option['link']}': option
        for option in transformed_show['streaming_options']
    })

    return output
