import sys
from os.path import abspath, dirname, join

# Adds src folder as a working directory.
# This is needed so that imports can be found.
src_dir = abspath(join(dirname(__file__), '../../src'))  # nopep8
sys.path.append(src_dir)  # nopep8

# --------------------------------------------------

from unittest import TestCase

from flask import url_for

from app import create_app
from models.common import connect_db, db
from models.movie import Movie
from models.service import Service
from models.streaming_option import StreamingOption

from ..util import (movie_generator, service_generator,
                    streaming_option_generator)

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


class MovieSearchViewTestCase(TestCase):
    """Tests for views involving movie searches.  This currently involves real network calls to API."""

    def test_search_title(self):
        """Tests for successfully searching for a movie title and displaying results."""

        # Arrange
        url = url_for("search_titles")
        title = "Batman"
        query_string = {"country": "us", "title": title}

        # Act
        with app.test_client() as client:
            resp = client.get(url, query_string=query_string)
            html = resp.get_data(as_text=True)

        # Assert
            self.assertIn("Search Results", html)
            self.assertIn(title, html)

    def test_search_title_with_no_results(self):
        """Tests for successfully searching for a movie title that doesn't exist."""

        # Arrange
        url = url_for("search_titles")
        query_string = {"country": "us", "title": "plpmnb"}

        # Act
        with app.test_client() as client:
            resp = client.get(url, query_string=query_string)
            html = resp.get_data(as_text=True)

        # Assert
            self.assertIn("Search Results", html)
            self.assertIn("No results found.", html)

    def test_search_title_with_missing_required_parameters(self):
        """Doing a title search without country or movie title should redirect to the homepage."""

        # Arrange
        url = url_for("search_titles")
        query_strings = [{"country": "us"}, {"title": "Batman"}]

        # Act
        for query_string in query_strings:
            with self.subTest(query_string=query_string):
                with app.test_client() as client:
                    resp = client.get(url, query_string=query_string)

        # Assert
                    self.assertEqual(resp.status_code, 302)
                    self.assertEqual(resp.location, url_for("home"))


class MovieDetailsViewTestCase(TestCase):
    """Tests for the view of a movie's details page.  This currently involves real network calls to API."""

    def setUp(self):
        db.session.query(StreamingOption).delete()
        db.session.query(Service).delete()
        db.session.query(Movie).delete()
        db.session.commit()

    def tearDown(self):
        db.session.rollback()

    def test_movie_details_page_with_data_in_local_database(self):
        """Tests that a movie's details page is loaded with existing data from the local database."""

        # Arrange
        country_code = 'us'

        service = service_generator(1)[0]
        service_light_theme_image = service.light_theme_image
        movie = movie_generator(1)[0]
        movie_id = movie.id
        movie_title = movie.title
        streaming_option = streaming_option_generator(1, movie_id, country_code, service.id)[0]
        streaming_option_link = streaming_option.link

        db.session.add_all([service, movie, streaming_option])
        db.session.commit()

        url = f'/movie/{movie_id}'

        # Act
        with app.test_client() as client:
            client.set_cookie("country_code", country_code)
            resp = client.get(url, follow_redirects=True)
            html = resp.get_data(as_text=True)

        # Assert
            self.assertEqual(resp.status_code, 200)
            self.assertIn(movie_title, html)
            self.assertIn(streaming_option_link, html)
            self.assertIn(service_light_theme_image, html)

    def test_movie_details_page_with_only_movie_data_in_local_database(self):
        """Tests that a movie's details page is loaded from the local database, but there are no streaming options."""

        # Arrange
        country_code = 'us'

        movie = movie_generator(1)[0]
        movie_id = movie.id
        movie_title = movie.title

        db.session.add(movie)
        db.session.commit()

        url = f'/movie/{movie_id}'

        # Act
        with app.test_client() as client:
            client.set_cookie("country_code", country_code)
            resp = client.get(url, follow_redirects=True)
            html = resp.get_data(as_text=True)

        # Assert
            self.assertEqual(resp.status_code, 200)
            self.assertIn(movie_title, html)
            self.assertIn('Not free', html)

    def test_movie_details_page_without_movie_data_in_local_database(self):
        """
        Tests that a movie's details page is loaded from the external API if it doesn't exist in the local database.

        !WARNING!
        Values used in here are contemporary.  They are retrieved from an external source and may change in the future.
        """

        # Arrange
        country_code = 'us'
        movie_id = '2332'  # Stargate
        url = f'/movie/{movie_id}'

        pluto = Service(
            id='plutotv',
            name='Pluto TV',
            home_page='https://pluto.tv/',
            theme_color_code='#fff200',
            light_theme_image='https://media.movieofthenight.com/services/plutotv/logo-light-theme.svg',
            dark_theme_image='https://media.movieofthenight.com/services/plutotv/logo-dark-theme.svg',
            white_image='https://media.movieofthenight.com/services/plutotv/logo-white.svg'
        )

        tubi = Service(
            id='tubi',
            name='Tubi',
            home_page='https://tubitv.com/',
            theme_color_code='#ffff13',
            light_theme_image='https://media.movieofthenight.com/services/tubi/logo-light-theme.svg',
            dark_theme_image='https://media.movieofthenight.com/services/tubi/logo-dark-theme.svg',
            white_image='https://media.movieofthenight.com/services/tubi/logo-white.svg'
        )

        db.session.add_all([pluto, tubi])
        db.session.commit()

        # Act
        with app.test_client() as client:
            client.set_cookie("country_code", country_code)
            resp = client.get(url, follow_redirects=True)
            html = resp.get_data(as_text=True)

        # Arrange
        self.assertEqual(resp.status_code, 200)
        self.assertIn('Stargate', html)
        self.assertIn("https://pluto.tv/gsa/on-demand/movies/5ca2afdf2ecfdaae49357414/details", html)
        self.assertIn("https://tubitv.com/movies/475643/stargate", html)
