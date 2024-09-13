from sqlalchemy.dialects import postgresql

from src.models.common import db

# ==================================================


class Movie(db.Model):
    """Represents a movie."""

    __tablename__ = 'movies'

    id = db.Column(
        db.Text,
        primary_key=True
    )

    imdb_id = db.Column(
        db.Text,
        nullable=False
    )

    tmdb_id = db.Column(
        db.Text,
        nullable=False
    )

    title = db.Column(
        db.Text,
        nullable=False
    )

    overview = db.Column(
        db.Text,
        nullable=False
    )

    release_year = db.Column(
        db.Integer
    )

    original_title = db.Column(
        db.Text,
        nullable=False
    )

    directors = db.Column(
        postgresql.ARRAY(db.Text)
    )

    cast = db.Column(
        postgresql.ARRAY(db.Text),
        nullable=False
    )

    rating = db.Column(
        db.Integer,
        nullable=False
    )

    runtime = db.Column(
        db.Integer
    )

    streaming_options = db.relationship(
        'StreamingOption', back_populates='movie', cascade='all, delete-orphan'
    )

    movie_posters = db.relationship(
        'MoviePoster', back_populates='movie', cascade='all, delete-orphan'
    )

    def __repr__(self) -> str:
        """Show info about movie."""

        return "{}({!r})".format(self.__class__.__name__, self.__dict__)

    @classmethod
    def upsert_database(cls, attributes: list[dict]) -> None:
        """
        Use a list of dictionaries, where each dictionary contains all the attributes for one movie (including id),
        and inserts new movies into the PostgreSQL database.  If a movie already exists, it will be overwritten
        with the new data.

        This performs an session.execute(), which will later need to be committed.

        :param attributes: A list of dicts.  A dict contains id, imdb_id, tmdb_id, ... for keys.  Values are movie
            data to put into database.
        """

        if len(attributes) > 0:
            stmt = postgresql.insert(cls).values(attributes)

            # all columns except id
            columns_to_replace = {name: column for name, column in stmt.excluded.items() if name != 'id'}

            stmt = stmt.on_conflict_do_update(
                constraint=f'{cls.__tablename__}_pkey',
                set_=columns_to_replace
            )

            db.session.execute(stmt)
