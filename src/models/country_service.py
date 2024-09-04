from typing import Self

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

    @classmethod
    def convert_list_to_dict(cls, countries_services: list[Self]) -> dict:
        """
        Converts a list of CountryServices to a dict {country: [services]}.

        :param countries_services: A list of CountryServices.
        :return: {country: [services]}.
        """

        output = {}

        for country_service in countries_services:
            services = output.get(country_service.country_code, [])
            services.append(country_service.service_id)
            output[country_service.country_code] = services

        return output
