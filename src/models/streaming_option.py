import json

from flask_sqlalchemy.pagination import Pagination

from src.models.common import db
from src.models.movie import Movie

# ==================================================


class StreamingOption(db.Model):
    """Represents a streaming option."""

    __tablename__ = 'streaming_options'

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    movie_id = db.Column(
        db.Text,
        db.ForeignKey('movies.id', ondelete='CASCADE'),
    )

    country_code = db.Column(
        db.String(2),
    )

    service_id = db.Column(
        db.Text,
        db.ForeignKey('services.id', ondelete='CASCADE'),
    )

    link = db.Column(
        db.Text,
        nullable=False
    )

    expires_soon = db.Column(
        db.Boolean,
        nullable=False
    )

    expires_on = db.Column(
        db.BigInteger
    )

    movie = db.relationship('Movie', back_populates='streaming_options')

    service = db.relationship('Service', back_populates='streaming_options')

    def __repr__(self) -> str:
        """Show info about streaming option."""

        return "{}({!r})".format(self.__class__.__name__, self.__dict__)

    def toJson(self) -> str:
        """Converts StreamingOption instance into JSON string."""

        return json.dumps(
            self,
            default=lambda o: {
                "id": o.id,
                "movie_id": o.movie_id,
                "country_code": o.country_code,
                "service_id": o.service_id,
                "link": o.link,
                "expires_soon": o.expires_soon,
                "expires_on": o.expires_on
            }
        )

    @classmethod
    def get_streaming_options(cls, country_code: str, service_id: str, page: int = None) -> Pagination:
        """
        Retrieves one page of streaming options for a country and streaming service.

        Returns a Flask-SQLAlchemy Pagination object.
        """

        return db.session\
            .query(StreamingOption)\
            .join(Movie, StreamingOption.movie_id == Movie.id)\
            .filter(
                StreamingOption.country_code == country_code,
                StreamingOption.service_id == service_id
            )\
            .order_by(Movie.rating.desc())\
            .paginate(page=page)
