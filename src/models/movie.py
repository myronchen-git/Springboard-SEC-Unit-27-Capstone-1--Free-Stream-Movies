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
        'StreamingOption', back_populates='movie', cascade='all, delete-orphan')

    def __repr__(self) -> str:
        """Show info about movie."""

        return "{}({!r})".format(self.__class__.__name__, self.__dict__)
