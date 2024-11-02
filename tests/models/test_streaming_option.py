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
from src.models.service import Service
from src.models.streaming_option import StreamingOption
from tests.utilities import (movie_generator, service_generator,
                             streaming_option_generator)

# ==================================================

app = create_app("freestreammovies_test", testing=True)
connect_db(app)
app.app_context().push()

db.drop_all()
db.create_all()

# --------------------------------------------------


class StreamingOptionIntegrationTestsGetStreamingOptions(TestCase):
    """Tests for StreamingOption.get_streaming_options()."""

    @classmethod
    def setUpClass(cls):
        cls.country_code = 'us'

        db.session.query(Service).delete()
        db.session.query(Movie).delete()
        db.session.commit()

        service = service_generator(1)[0]
        cls.service_id = service.id
        movie = movie_generator(1)[0]
        cls.movie_id = movie.id

        db.session.add_all((service, movie))
        db.session.commit()

    def setUp(self):
        db.session.query(StreamingOption).delete()
        db.session.commit()

    def tearDown(self):
        db.session.rollback()

    def test_getting_streaming_options_of_zero_items(self):
        """
        Retrieving a page of streaming options, when there are no items,
        should return a Pagination containing no items.
        """

        # Act
        page = StreamingOption.get_streaming_options(
            self.country_code,
            self.service_id)

        # Assert
        self.assertEqual(len(page.items), 0)
        self.assertEqual(page.page, 1)
        self.assertFalse(page.has_prev)
        self.assertFalse(page.has_next)

    def test_getting_streaming_options_of_one_item(self):
        """
        Retrieving a page of streaming options, when there is only one item,
        should return a Pagination containing only that one item.
        """

        # Arrange
        streaming_options = streaming_option_generator(
            1,
            self.movie_id,
            self.country_code,
            self.service_id
        )
        db.session.add_all(streaming_options)
        db.session.commit()

        # Act
        page = StreamingOption.get_streaming_options(
            self.country_code,
            self.service_id)

        # Assert
        self.assertEqual(len(page.items), len(streaming_options))

        for streaming_option in streaming_options:
            self.assertIn(streaming_option, page.items)

        self.assertEqual(page.page, 1)
        self.assertFalse(page.has_prev)
        self.assertFalse(page.has_next)

    def test_getting_streaming_options_of_multiple_items(self):
        """
        Retrieving a page of streaming options, when there are multiple items,
        should return a Pagination containing multiple items
        and indications that there are more pages.
        """

        # Arrange
        streaming_options = streaming_option_generator(
            21,
            self.movie_id,
            self.country_code,
            self.service_id
        )
        db.session.add_all(streaming_options)
        db.session.commit()

        # Act
        page1 = StreamingOption.get_streaming_options(
            self.country_code,
            self.service_id)
        page2 = StreamingOption.get_streaming_options(
            self.country_code,
            self.service_id, 2)

        # Assert
        self.assertEqual(len(page1.items), 20)
        self.assertEqual(len(page2.items), 1)

        for item in page1.items:
            self.assertIn(item, streaming_options[0:20])
        for item in page2.items:
            self.assertIn(item, streaming_options[20:])

        self.assertEqual(page1.page, 1)
        self.assertEqual(page2.page, 2)

        self.assertFalse(page1.has_prev)
        self.assertTrue(page2.has_prev)

        self.assertTrue(page1.has_next)
        self.assertFalse(page2.has_next)

    def test_getting_streaming_options_without_duplicate_options_bug(self):
        """
        Retrieving pages of streaming options should not display the same movie multiple times.
        """

        # Arrange
        db.session.query(Movie).delete()
        movies = movie_generator(100, 1)
        db.session.add_all(movies)
        db.session.commit()

        streaming_options = [
            streaming_option_generator(1, movie.id, self.country_code, self.service_id)[0]
            for movie in movies
        ]
        db.session.add_all(streaming_options)
        db.session.commit()

        # Act
        pages = [
            StreamingOption.get_streaming_options(self.country_code, self.service_id, i)
            for i in range(1, 5)
        ]

        # Assert
        count_of_a_movie = 0

        for page in pages:
            for item in page.items:
                if item.movie_id == movies[0].id:
                    count_of_a_movie += 1

        self.assertEqual(count_of_a_movie, 1)

    # More tests are needed for cases where there are other movies, services, or streaming options.


class StreamingOptionIntegrationTestsInsertDatabase(TestCase):
    """Tests for StreamingOption.insert_database()."""

    @classmethod
    def setUpClass(cls):
        cls.country_code = 'us'

        db.session.query(Service).delete()
        db.session.query(Movie).delete()
        db.session.commit()

        service = service_generator(1)[0]
        cls.service_id = service.id
        movie = movie_generator(1)[0]
        cls.movie_id = movie.id

        db.session.add_all((service, movie))
        db.session.commit()

    def setUp(self):
        db.session.query(StreamingOption).delete()
        db.session.commit()

    def tearDown(self):
        db.session.rollback()

    def test_insert_new_streaming_options(self):
        """Inserting new streaming options should store them in the database."""

        # Arrange
        num_streaming_options = 2

        streaming_options_data = []
        for streaming_option in streaming_option_generator(
                num_streaming_options,
                self.movie_id,
                self.country_code,
                self.service_id):
            data = {}
            for attr in StreamingOption.__table__.columns.keys():
                data[attr] = getattr(streaming_option, attr)
            streaming_options_data.append(data)

        # Act
        StreamingOption.insert_database(deepcopy(streaming_options_data))
        db.session.commit()

        # Assert
        streaming_options = db.session.query(StreamingOption).all()

        self.assertEqual(len(streaming_options), num_streaming_options)

        for i in range(num_streaming_options):
            for attr in StreamingOption.__table__.columns.keys():
                if attr != 'id':
                    self.assertEqual(getattr(streaming_options[i], attr), streaming_options_data[i][attr],
                                     msg=(f'Assertion failed for '
                                          f'subtest(num_streaming_options = {num_streaming_options}) '
                                          f'-> streaming option item {i} -> attribute "{attr}".'))

    def test_insert_no_streaming_options(self):
        """When inserting no streaming options, the database should remain unchanged."""

        # Arrange
        streaming_options_data = []

        initial_streaming_options = streaming_option_generator(
            2,
            self.movie_id,
            self.country_code,
            self.service_id)
        db.session.add_all(initial_streaming_options)
        db.session.commit()

        # Act
        StreamingOption.insert_database(streaming_options_data)
        db.session.commit()

        # Assert
        streaming_options = db.session.query(StreamingOption).all()

        self.assertEqual(len(streaming_options), len(initial_streaming_options))

        self.assertEqual(streaming_options, initial_streaming_options)
