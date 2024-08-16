import sys
from os.path import abspath, dirname, join

# Adds root folder as a working directory.
# This is needed so that imports can be found.
root_dir = abspath(join(dirname(__file__), '../../'))  # nopep8
sys.path.append(root_dir)  # nopep8

# --------------------------------------------------

from unittest import TestCase

from src.adapters.streaming_availability_adapter import \
    store_movie_and_streaming_options
from src.app import create_app
from src.models.common import connect_db, db
from src.models.movie import Movie
from src.models.movie_posters import MoviePoster
from src.models.streaming_option import StreamingOption
from tests.util import service_generator

# ==================================================

app = create_app("freestreammovies_test", testing=True)
connect_db(app)
app.app_context().push()

db.drop_all()
db.create_all()

# --------------------------------------------------


class StreamingAvailabilityTestCase(TestCase):
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
