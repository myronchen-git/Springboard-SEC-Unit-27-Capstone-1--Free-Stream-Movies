import sys
from os.path import abspath, dirname, join

# Adds root folder as a working directory.
# This is needed so that imports can be found.
root_dir = abspath(join(dirname(__file__), '../../'))  # nopep8
sys.path.append(root_dir)  # nopep8

# --------------------------------------------------

from unittest import TestCase

from flask import url_for

from src.app import create_app
from src.models.common import connect_db, db
from src.models.country_service import CountryService
from src.models.movie import Movie
from src.models.service import Service
from tests.util import service_generator

# ==================================================

app = create_app("freestreammovies_test", testing=True)
app.config.update(
    WTF_CSRF_ENABLED=False,
    SERVER_NAME="localhost:5000"
)

connect_db(app)
app.app_context().push()

db.drop_all()
db.create_all()

# --------------------------------------------------


class HomepageViewTestCase(TestCase):
    """Tests the view for the homepage."""

    def setUp(self):
        db.session.query(CountryService).delete()
        db.session.query(Service).delete()
        db.session.query(Movie).delete()
        db.session.commit()

    def tearDown(self):
        db.session.rollback()

    def test_display_homepage_with_services(self):
        """Tests that the homepage renders with a country's streaming services."""

        # Arrange
        url = url_for("home")

        # setting up countries
        country_codes = ['us']

        # adding streaming services
        services = service_generator(1)
        db.session.add_all(services)

        # adding relationships between services and countries
        country_service = CountryService(
            country_code=country_codes[0],
            service_id=services[0].id)
        db.session.add(country_service)

        db.session.commit()

        # Act
        with app.test_client() as client:
            client.set_cookie("country_code", country_codes[0])
            resp = client.get(url, follow_redirects=True)
            html = resp.get_data(as_text=True)

        # Assert
        self.assertEqual(resp.status_code, 200)

        self.assertIn(f'<section id="section-{services[0].id}" class="section-service">', html)
        self.assertIn(f'<img src="{services[0].light_theme_image}" alt="service.name"', html)
        self.assertIn(f'data-service="{services[0].id}"', html)
        self.assertIn("Loading Movies...", html)

    def test_display_homepage_without_unavailable_services(self):
        """Tests that the homepage renders only the streaming services available in a provided country."""

        # Arrange
        url = url_for("home")

        # setting up countries
        country_codes = ['us', 'ca']

        # adding streaming services
        services = service_generator(2)
        db.session.add_all(services)

        # adding relationships between services and countries
        country_service = CountryService(
            country_code=country_codes[0],
            service_id=services[0].id)
        db.session.add(country_service)

        country_service = CountryService(
            country_code=country_codes[1],
            service_id=services[1].id)
        db.session.add(country_service)

        db.session.commit()

        # Act
        with app.test_client() as client:
            response_status_codes = []
            htmls = []

            for i in range(len(country_codes)):
                client.set_cookie("country_code", country_codes[i])
                resp = client.get(url, follow_redirects=True)
                html = resp.get_data(as_text=True)

                response_status_codes.append(resp.status_code)
                htmls.append(html)

        # Assert
            for response_status_code in response_status_codes:
                self.assertEqual(response_status_code, 200)

            self.assertIn(f'<section id="section-{services[0].id}" class="section-service">', htmls[0])
            self.assertNotIn(f'<section id="section-{services[1].id}" class="section-service">', htmls[0])
            self.assertNotIn(f'<section id="section-{services[0].id}" class="section-service">', htmls[1])
            self.assertIn(f'<section id="section-{services[1].id}" class="section-service">', htmls[1])
