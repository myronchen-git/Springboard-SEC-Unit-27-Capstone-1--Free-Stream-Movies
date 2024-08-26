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
from src.models.movie import Movie
from src.models.movie_poster import MoviePoster
from tests.utility_functions import movie_generator, movie_poster_generator

# ==================================================

app = create_app("freestreammovies_test", testing=True)
app.config.update(
    SERVER_NAME="localhost:5000"
)

connect_db(app)
app.app_context().push()

db.drop_all()
db.create_all()

# --------------------------------------------------


class MoviePosterApiTestCase(TestCase):
    """Tests for movie poster API."""

    def setUp(self):
        db.session.query(MoviePoster).delete()
        db.session.query(Movie).delete()
        db.session.commit()

        movies = movie_generator(2)
        db.session.add_all(movies)

        self.movie_posters = tuple(movie_poster_generator(('0',)))
        db.session.add_all(self.movie_posters)
        db.session.commit()

    def tearDown(self):
        db.session.rollback()

    def test_get_json_of_movie_posters(self):
        """Calling the get_movie_posters API route with valid query parameters should return a JSON."""

        # Arrange
        url = url_for('get_movie_posters')
        queries = {'movieId': '0', 'type': 'verticalPoster', 'size': 'w240'}
        expected_movie_poster_link = self.movie_posters[0].link

        # Act
        with app.test_client() as client:
            resp = client.get(url, query_string=queries)
            json = resp.get_json()

        # Assert
            self.assertEqual(resp.status_code, 200)
            self.assertEqual(json, {'0': {'verticalPoster': {'w240': expected_movie_poster_link}}})

    def test_get_movie_posters_with_missing_required_query_parameters(self):
        """
        Calling the get_movie_posters API route with missing required parameters
        should result in a client error.
        """

        # Arrange
        url = url_for('get_movie_posters')
        queries = [{'type': 'verticalPoster', 'size': 'w240'},
                   {'movieId': '0', 'size': 'w240'},
                   {'movieId': '0', 'type': 'verticalPoster'}]

        # Act
        for query_string in queries:
            with self.subTest(query_string=query_string):
                with app.test_client() as client:
                    resp = client.get(url, query_string=query_string)

        # Assert
                    self.assertEqual(resp.status_code, 400)

    def test_get_movie_posters_with_query_parameters_containing_comma(self):
        """
        Calling the get_movie_posters API route with query parameters
        containing commas should result in a client error.
        """

        # Arrange
        url = url_for('get_movie_posters')
        queries = {'movieId': '0', 'type': 'verticalPoster', 'size': 'w240, w360'}

        # Act
        with app.test_client() as client:
            resp = client.get(url, query_string=queries)

        # Assert
            self.assertEqual(resp.status_code, 400)

    def test_get_movie_posters_with_unrecognized_query_parameter(self):
        """
        Calling the get_movie_posters API route with an unrecognized value
        for a query parameter should result in an error.
        """

        # Arrange
        url = url_for('get_movie_posters')
        queries = {'movieId': '0', 'type': 'diagonalPoster', 'size': 'w240'}

        # Act
        with app.test_client() as client:
            resp = client.get(url, query_string=queries)

        # Assert
            self.assertEqual(resp.status_code, 400)
