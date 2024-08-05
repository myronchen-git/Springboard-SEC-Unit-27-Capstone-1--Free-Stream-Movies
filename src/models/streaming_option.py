from models.common import db

# ==================================================


class StreamingOption(db.Model):
    """Represents a streaming option."""

    __tablename__ = 'streaming_options'

    movie_id = db.Column(
        db.Text,
        db.ForeignKey('movies.id', ondelete='CASCADE'),
        primary_key=True
    )

    country_code = db.Column(
        db.String(2),
        primary_key=True
    )

    service_id = db.Column(
        db.Text,
        db.ForeignKey('services.id', ondelete='CASCADE'),
        primary_key=True
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
