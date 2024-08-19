from enum import StrEnum
from typing import Self

from src.exceptions.UnrecognizedValueError import UnrecognizedValueError
from src.models.common import db

# ==================================================


class MoviePoster(db.Model):
    """Represents a movie's posters."""

    __tablename__ = 'movie_posters'

    movie_id = db.Column(
        db.Text,
        db.ForeignKey('movies.id', ondelete='CASCADE'),
        primary_key=True
    )

    type = db.Column(
        db.Text,
        primary_key=True
    )

    size = db.Column(
        db.String(4),
        primary_key=True
    )

    link = db.Column(
        db.Text,
        nullable=False
    )

    movie = db.relationship('Movie', back_populates='movie_posters')

    # currently only storing vertical posters
    Types = StrEnum('Types', {'VERTICAL_POSTER': 'verticalPoster'})
    VerticalSizes = StrEnum('VerticalSizes', ['W240', 'W360', 'W480', 'W600', 'W720'])

    def __repr__(self) -> str:
        """Show info about movie poster."""

        return "{}({!r})".format(self.__class__.__name__, self.__dict__)

    @classmethod
    def get_movie_posters(cls, movie_ids: list[str], types: list[str], sizes: list[str]) -> list[Self]:
        """
        Retrieves a dictionary of movie posters for specified movies, types, and sizes.
        Queries the database.

        @param {list[str]} movie_ids - Movie IDs of the posters to retrieve.
        @param {list[str]} types - Movie poster types, such as verticalPoster.
        @param {list[str]} sizes - Movie poster sizes, such as w240.
        @returns {movie_id: {type: {size: link}}}.
        """

        for type in types:
            if type not in cls.Types:
                supported_types = tuple(type.value for type in cls.Types)
                raise UnrecognizedValueError(
                    f'Movie poster type(s) is unrecognized.  Supported types are {supported_types}.')

        for size in sizes:
            if size not in cls.VerticalSizes:
                supported_sizes = tuple(size.value for size in cls.VerticalSizes)
                raise UnrecognizedValueError(
                    f'Movie poster size(s) is unrecognized.  Supported sizes are {supported_sizes}.')

        return db.session\
            .query(MoviePoster)\
            .filter(
                MoviePoster.movie_id.in_(movie_ids),
                MoviePoster.type.in_(types),
                MoviePoster.size.in_(sizes)
            )\
            .all()

    @classmethod
    def convert_list_to_dict(cls, movie_posters: list[Self]) -> dict:
        """
        Converts a list of MoviePosters to a dict {movie_id: {type: {size: link}}}.

        @param {list[MoviePoster]} movie_posters - A list of MoviePoster objects.
        @returns {movie_id: {type: {size: link}}}.
        """

        output = {}
        for movie_poster in movie_posters:
            movie_posters_of_movie_id = output.get(movie_poster.movie_id, {})
            movie_posters_of_movie_id_and_type = movie_posters_of_movie_id.get(movie_poster.type, {})

            movie_posters_of_movie_id_and_type.update({movie_poster.size: movie_poster.link})
            movie_posters_of_movie_id.update({movie_poster.type: movie_posters_of_movie_id_and_type})
            output.update({movie_poster.movie_id: movie_posters_of_movie_id})

        return output
