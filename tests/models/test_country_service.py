import sys
from os.path import abspath, dirname, join

# Adds root folder as a working directory.
# This is needed so that imports can be found.
root_dir = abspath(join(dirname(__file__), '../../'))  # nopep8
sys.path.append(root_dir)  # nopep8

# --------------------------------------------------

from unittest import TestCase

from src.app import create_app
from src.models.common import connect_db, db
from src.models.country_service import CountryService

# ==================================================

app = create_app("freestreammovies_test", testing=True)
connect_db(app)
app.app_context().push()

db.drop_all()
db.create_all()

# --------------------------------------------------


class CountryServiceConvertListToDictUnitTestCase(TestCase):
    """Unit tests for CountryService.convert_list_to_dict()."""

    def test_convert_for_zero_countries_and_services(self):
        """Tests that an empty list returns an empty dict."""

        # Act
        result = CountryService.convert_list_to_dict([])

        # Assert
        self.assertEqual(result, {})

    def test_convert_for_one_country_service(self):
        # Arrange
        country_service_1 = CountryService(country_code='us', service_id='service1')

        # Act
        result = CountryService.convert_list_to_dict([country_service_1])

        # Assert
        self.assertEqual(result, {'us': ['service1']})

    def test_convert_for_multiple_countries_and_services(self):
        """
        Tests that a list of CountryServices having different countries
        and services should successfully convert to a dict.
        """

        # Arrange
        country_service_1 = CountryService(country_code='us', service_id='service1')
        country_service_2 = CountryService(country_code='us', service_id='service2')
        country_service_3 = CountryService(country_code='ca', service_id='service1')

        # Act
        result = CountryService.convert_list_to_dict([country_service_1, country_service_2, country_service_3])

        # Assert
        self.assertEqual(result, {'us': ['service1', 'service2'], 'ca': ['service1']})
