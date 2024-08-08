import sys
from os.path import abspath, dirname, join

# Adds src folder as a working directory.
# This is needed so that imports can be found.
root_dir = abspath(join(dirname(__file__), '../../src'))  # nopep8
sys.path.append(root_dir)  # nopep8

# --------------------------------------------------

from unittest import TestCase

from flask import url_for

from app import create_app
from models.common import connect_db, db

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
