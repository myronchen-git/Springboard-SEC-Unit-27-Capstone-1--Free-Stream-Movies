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
from src.models.streaming_option import StreamingOption
from tests.util import (movie_generator, service_generator,
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


class StreamingOptionApiTestCase(TestCase):
    """Tests for streaming option API."""

    COUNTRY_CODE = "us"
    SERVICE_ID = "service00"  # see util.py -> service_generator() for name format

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

    def test_get_streaming_options_at_first_page(self):
        """
        Calling the base get_streaming_options endpoint should return the first page of
        streaming options, page number, and whether there is a next page.
        """

        # Arrange
        url = url_for(
            "get_streaming_options",
            country_code=StreamingOptionApiTestCase.COUNTRY_CODE,
            service_id=StreamingOptionApiTestCase.SERVICE_ID
        )

        streaming_options = streaming_option_generator(
            21,
            StreamingOptionApiTestCase.movie_id,
            StreamingOptionApiTestCase.COUNTRY_CODE,
            StreamingOptionApiTestCase.SERVICE_ID
        )

        db.session.add_all(streaming_options)
        db.session.commit()

        # Act
        with app.test_client() as client:
            resp = client.get(url)
            json = resp.get_json()

        # Assert
            self.assertEqual(json['page'], 1)
            self.assertEqual(json['has_prev'], False)
            self.assertEqual(json['has_next'], True)

            first_page_of_items = [option.toJson()
                                   for ind, option in enumerate(streaming_options)
                                   if ind < 20]
            self.assertEqual(json['items'], first_page_of_items)

    def test_get_streaming_options_at_second_page(self):
        """
        Calling get_streaming_options endpoint with a page query argument should return that page's
        set of streaming options, page number, and whether there is a prev/next page.
        """

        # Arrange
        url = url_for(
            "get_streaming_options",
            country_code=StreamingOptionApiTestCase.COUNTRY_CODE,
            service_id=StreamingOptionApiTestCase.SERVICE_ID
        )

        streaming_options = streaming_option_generator(
            21,
            StreamingOptionApiTestCase.movie_id,
            StreamingOptionApiTestCase.COUNTRY_CODE,
            StreamingOptionApiTestCase.SERVICE_ID
        )

        db.session.add_all(streaming_options)
        db.session.commit()

        # Act
        with app.test_client() as client:
            resp = client.get(url, query_string={"page": 2})
            json = resp.get_json()

        # Assert
            self.assertEqual(json['page'], 2)
            self.assertEqual(json['has_prev'], True)
            self.assertEqual(json['has_next'], False)

            second_page_of_items = [option.toJson()
                                    for ind, option in enumerate(streaming_options)
                                    if ind >= 20]
            self.assertEqual(json['items'], second_page_of_items)
