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

    def __repr__(self) -> str:
        """Show info about movie poster."""

        return "{}({!r})".format(self.__class__.__name__, self.__dict__)
