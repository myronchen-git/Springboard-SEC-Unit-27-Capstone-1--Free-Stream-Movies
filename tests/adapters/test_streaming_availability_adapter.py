import sys
from os.path import abspath, dirname, join

# Adds root folder as a working directory.
# This is needed so that imports can be found.
root_dir = abspath(join(dirname(__file__), '../../'))  # nopep8
sys.path.append(root_dir)  # nopep8

# --------------------------------------------------

from copy import deepcopy
from unittest import TestCase

from src.adapters.streaming_availability_adapter import (
    convert_image_set_json_into_movie_poster_objects,
    store_movie_and_streaming_options)
from src.app import create_app
from src.models.common import connect_db, db
from src.models.movie import Movie
from src.models.movie_poster import MoviePoster
from src.models.streaming_option import StreamingOption
from tests.utility_functions import service_generator

# ==================================================

app = create_app("freestreammovies_test", testing=True)
connect_db(app)
app.app_context().push()

db.drop_all()
db.create_all()

# --------------------------------------------------


class StreamingAvailabilityAdapterUnitTests(TestCase):
    """Unit tests for Streaming Availability Adapter functions."""

    def test_convert_image_set_json_into_movie_poster_objects(self):
        """
        Tests that an image set dict created from the JSON imageSet from Streaming Availability API is able to be
        converted into a list of MoviePosters, and for existing MoviePosters to be updated with that JSON data.
        """

        poster_type = 'verticalPoster'
        image_set = {poster_type: {'w240': 'link1', 'w360': 'link2'}}
        movie_id = '1'

        with self.subTest('When no existing MoviePosters are passed in.'):
            # Act
            result = convert_image_set_json_into_movie_poster_objects(deepcopy(image_set), movie_id)

            # Assert
            self.assertEqual(len(result), len(image_set[poster_type]))

            for movie_poster in result:
                self.assertEqual(movie_poster.movie_id, movie_id)
                self.assertEqual(movie_poster.type, poster_type)
                self.assertIn(movie_poster.size, image_set[poster_type].keys())
                self.assertIn(movie_poster.link, image_set[poster_type][movie_poster.size])

        with self.subTest('When existing MoviePosters are passed in.'):
            # Arrange
            movie_poster_1 = MoviePoster(movie_id=movie_id, type='verticalPoster', size='w240', link='old link1')
            movie_poster_2 = MoviePoster(movie_id=movie_id, type='verticalPoster', size='w360', link='old link2')

            # Act
            result = convert_image_set_json_into_movie_poster_objects(
                deepcopy(image_set), movie_id, [movie_poster_1, movie_poster_2])

            # Assert
            self.assertEqual(len(result), len(image_set['verticalPoster']))

            for movie_poster in result:
                self.assertEqual(movie_poster.movie_id, movie_id)
                self.assertEqual(movie_poster.type, poster_type)
                self.assertIn(movie_poster.size, image_set[poster_type].keys())
                self.assertIn(movie_poster.link, image_set[poster_type][movie_poster.size])

            self.assertIs(result[0], movie_poster_1)
            self.assertIs(result[1], movie_poster_2)


class StreamingAvailabilityAdapterIntegTests(TestCase):
    """Tests for functions that interact with Streaming Availability."""

    def setUp(self):
        db.session.query(Movie).delete()
        db.session.query(StreamingOption).delete()

        db.session.commit()

    def tearDown(self):
        db.session.rollback()

    def test_store_movie_and_streaming_options(self):
        """Tests for successfully adding a movie and its streaming options to the database."""

        # Arrange
        services = service_generator(2)
        service00_id = services[0].id
        service01_id = services[1].id
        db.session.add_all(services)
        db.session.commit()

        movie_id = "movie1"
        link00 = f"www.youtube.com/{movie_id}"
        link01 = f"www.pluto.tv/{movie_id}"
        streaming_options_json = {
            "ca": [
                {
                    "service": {"id": service00_id},
                    "type": "free",
                    "link": link00,
                    "expiresSoon": False
                },
                {
                    "service": {"id": service01_id},
                    "type": "free",
                    "link": link01,
                    "expiresSoon": False,
                    "expiresOn": 1735621200
                }],
            "us": [
                {
                    "service": {"id": service00_id},
                    "type": "free",
                    "link": link00,
                    "expiresSoon": False
                },
                {
                    "service": {"id": service01_id},
                    "type": "free",
                    "link": link01,
                    "expiresSoon": True,
                    "expiresOn": 1735621200
                }]
        }

        image_set_json = {
            "verticalPoster": {
                "w240": "example.com/w240",
                "w360": "example.com/w360"
            }
        }

        show_json = {
            "id": movie_id,
            "imdbId": "tt0468569",
            "tmdbId": "movie/155",
            "title": "The Dark Knight",
            "overview": "description",
            "releaseYear": 2008,
            "originalTitle": "The Dark Knight",
            "cast": ["person1", "person2"],
            "rating": 87,
            "runtime": 152,
            "imageSet": image_set_json,
            "streamingOptions": streaming_options_json
        }

        # Act
        store_movie_and_streaming_options(show_json)

        # Assert
        movies = db.session.query(Movie).all()
        self.assertEqual(len(movies), 1)
        self.assertEqual(movies[0].id, movie_id)

        movie_posters = db.session.query(MoviePoster).all()
        self.assertEqual(len(movie_posters), 2)
        for movie_poster in movie_posters:
            self.assertEqual(movie_poster.movie_id, movie_id)
            self.assertEqual(movie_poster.type, "verticalPoster")
        self.assertEqual(movie_posters[0].size, "w240")
        self.assertEqual(movie_posters[0].link, "example.com/w240")
        self.assertEqual(movie_posters[1].size, "w360")
        self.assertEqual(movie_posters[1].link, "example.com/w360")

        streaming_options = db.session.query(StreamingOption).all()
        self.assertEqual(len(streaming_options), 4)

        us_streaming_option_links = [streaming_option.link
                                     for streaming_option in streaming_options
                                     if streaming_option.country_code == 'us']
        self.assertEqual(len(us_streaming_option_links), 2)
        self.assertIn(link00, us_streaming_option_links)
        self.assertIn(link01, us_streaming_option_links)
