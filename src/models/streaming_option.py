import json

from flask_sqlalchemy.pagination import Pagination
from sqlalchemy import insert

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
        nullable=False
    )

    country_code = db.Column(
        db.String(2),
        nullable=False
    )

    service_id = db.Column(
        db.Text,
        db.ForeignKey('services.id', ondelete='CASCADE'),
        nullable=False
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

        :param country_code: A country's 2-char code.  For example, Canada is 'ca'.
        :param service_id: A streaming service's ID.
        :param page: The page to fetch.
        :return: a Flask-SQLAlchemy Pagination object.
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

    @classmethod
    def insert_database(cls, attributes: list[dict]) -> None:
        """
        Use a list of dictionaries, where each dictionary contains all the attributes for one streaming option,
        and inserts new streaming options into the PostgreSQL database.

        This performs an session.execute(), which will later need to be committed.

        :param attributes: A list of dicts.  A dict contains movie_id, country_code, service_id, ... for keys.
            Values are streaming option data to put into database.
        """

        if len(attributes) > 0:
            db.session.execute(
                insert(cls),
                attributes
            )
