import sys
from os.path import abspath, dirname, join

# Adds root folder as a working directory.
# This is needed so that imports can be found.
root_dir = abspath(join(dirname(__file__), '../../'))  # nopep8
sys.path.append(root_dir)  # nopep8

# --------------------------------------------------

from copy import deepcopy
from unittest import TestCase

from src.app import create_app
from src.models.common import connect_db, db
from src.models.movie import Movie
from tests.utilities import movie_generator

# ==================================================

app = create_app("freestreammovies_test", testing=True)
connect_db(app)
app.app_context().push()

db.drop_all()
db.create_all()

# --------------------------------------------------


class MovieIntegrationTestsUpsertDatabase(TestCase):
    """Integration tests for Movie.upsert_database()."""

    def setUp(self):
        db.session.query(Movie).delete()
        db.session.commit()

    def tearDown(self):
        db.session.rollback()

    def test_insert_new_movies(self):
        """For one and many movies, inserting new movies should store them in the database."""

        for num_movies in range(1, 3):
            with self.subTest(num_movies=num_movies):

                # Arrange
                movies_data = []

                for movie in movie_generator(num_movies):
                    data = {}
                    for attr in Movie.__table__.columns.keys():
                        data[attr] = getattr(movie, attr)
                    movies_data.append(data)

                # Act
                Movie.upsert_database(deepcopy(movies_data))
                db.session.commit()

                # Assert
                movies = db.session.query(Movie).all()

                self.assertEqual(len(movies), num_movies)

                for i in range(num_movies):
                    for attr in Movie.__table__.columns.keys():
                        self.assertEqual(getattr(movies[i], attr), movies_data[i][attr],
                                         msg=(f'Assertion failed for subtest(num_movies = {num_movies}) '
                                              f'-> movie id "{i}" -> attribute "{attr}".'))

                # clean up
                db.session.rollback()
                db.session.query(Movie).delete()
                db.session.commit()

    def test_update_existing_movies(self):
        """For one and many movies, inserting movies for existing movies should update them in the database."""

        for num_movies in range(1, 3):
            with self.subTest(num_movies=num_movies):

                # Arrange
                generated_movies = movie_generator(num_movies * 2)

                initial_movies = generated_movies[:num_movies]
                db.session.add_all(initial_movies)
                db.session.commit()

                updated_movies = generated_movies[num_movies:]
                updated_movies_data = []
                for i in range(len(updated_movies)):
                    data = {}
                    for attr in Movie.__table__.columns.keys():
                        data[attr] = getattr(updated_movies[i], attr)
                    data['id'] = initial_movies[i].id
                    updated_movies_data.append(data)

                # Act
                Movie.upsert_database(deepcopy(updated_movies_data))
                db.session.commit()

                # Assert
                movies = db.session.query(Movie).all()

                self.assertEqual(len(movies), num_movies)

                for i in range(num_movies):
                    for attr in Movie.__table__.columns.keys():
                        self.assertEqual(getattr(movies[i], attr), updated_movies_data[i][attr],
                                         msg=(f'Assertion failed for subtest(num_movies = {num_movies}) '
                                              f'-> movie id "{i}" -> attribute "{attr}".'))

                # clean up
                db.session.rollback()
                db.session.query(Movie).delete()
                db.session.commit()

    def test_upsert_no_movies(self):
        """When upserting no movies, the database should remain unchanged."""

        # Arrange
        movies_data = []

        initial_movies = movie_generator(2)
        db.session.add_all(initial_movies)
        db.session.commit()

        # Act
        Movie.upsert_database(movies_data)
        db.session.commit()

        # Assert
        movies = db.session.query(Movie).all()

        self.assertEqual(len(movies), len(initial_movies))

        self.assertEqual(movies, initial_movies)
