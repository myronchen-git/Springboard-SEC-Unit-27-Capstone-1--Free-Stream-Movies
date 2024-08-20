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
from src.models.streaming_option import StreamingOption
from tests.utility_functions import (movie_generator, service_generator,
                                     streaming_option_generator)

# ==================================================

app = create_app("freestreammovies_test", testing=True)
connect_db(app)
app.app_context().push()

db.drop_all()
db.create_all()

# --------------------------------------------------


class StreamingOptionTestCase(TestCase):
    """Tests for StreamingOption model."""

    COUNTRY_CODE = "us"
    SERVICE_01_ID = "service00"  # see util.py -> service_generator() for name format

    @classmethod
    def setUpClass(cls):
        service = service_generator(1)[0]
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
            StreamingOptionTestCase.COUNTRY_CODE, StreamingOptionTestCase.SERVICE_01_ID)

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
            StreamingOptionTestCase.movie_id,
            StreamingOptionTestCase.COUNTRY_CODE,
            StreamingOptionTestCase.SERVICE_01_ID
        )
        db.session.add_all(streaming_options)
        db.session.commit()

        # Act
        page = StreamingOption.get_streaming_options(
            StreamingOptionTestCase.COUNTRY_CODE, StreamingOptionTestCase.SERVICE_01_ID)

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
            StreamingOptionTestCase.movie_id,
            StreamingOptionTestCase.COUNTRY_CODE,
            StreamingOptionTestCase.SERVICE_01_ID
        )
        db.session.add_all(streaming_options)
        db.session.commit()

        # Act
        page1 = StreamingOption.get_streaming_options(
            StreamingOptionTestCase.COUNTRY_CODE, StreamingOptionTestCase.SERVICE_01_ID)
        page2 = StreamingOption.get_streaming_options(
            StreamingOptionTestCase.COUNTRY_CODE, StreamingOptionTestCase.SERVICE_01_ID, 2)

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

    # More tests are needed for cases where there are other movies, services, or streaming options.
