from src.models.common import db

# ==================================================


class Service(db.Model):
    """Represents a streaming service."""

    __tablename__ = 'services'

    id = db.Column(
        db.Text,
        primary_key=True
    )

    name = db.Column(
        db.Text,
        nullable=False
    )

    home_page = db.Column(
        db.Text,
        nullable=False
    )

    theme_color_code = db.Column(
        db.Text,
        nullable=False
    )

    light_theme_image = db.Column(
        db.Text,
        nullable=False
    )

    dark_theme_image = db.Column(
        db.Text,
        nullable=False
    )

    white_image = db.Column(
        db.Text,
        nullable=False
    )

    streaming_options = db.relationship(
        'StreamingOption', back_populates='service', cascade='all, delete-orphan')

    def __repr__(self) -> str:
        """Show info about movie."""

        return "{}({!r})".format(self.__class__.__name__, self.__dict__)
