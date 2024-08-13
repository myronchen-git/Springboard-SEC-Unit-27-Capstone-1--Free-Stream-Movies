from src.models.common import db

# ==================================================


class CountryService(db.Model):
    """Mapping of country and streaming service."""

    __tablename__ = "countries_services"

    country_code = db.Column(
        db.String(2),
        primary_key=True
    )

    service_id = db.Column(
        db.Text,
        db.ForeignKey('services.id', ondelete='CASCADE'),
        primary_key=True
    )

    service = db.relationship('Service')

    def __repr__(self) -> str:
        """Show info about streaming option."""

        return "{}({!r})".format(self.__class__.__name__, self.__dict__)
