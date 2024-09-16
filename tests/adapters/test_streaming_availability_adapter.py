import sys
from os.path import abspath, dirname, join

# Adds root folder as a working directory.
# This is needed so that imports can be found.
root_dir = abspath(join(dirname(__file__), '../../'))  # nopep8
sys.path.append(root_dir)  # nopep8

# --------------------------------------------------

from copy import deepcopy
from unittest import TestCase
from unittest.mock import call, patch

from src.adapters.streaming_availability_adapter import (
    convert_image_set_json_into_movie_poster_objects, gather_streaming_options,
    store_movie_and_streaming_options,
    transform_image_set_json_into_movie_poster_list, transform_show,
    transform_show_json_into_movie_dict,
    transform_streaming_option_json_into_dict)
from src.app import create_app
from src.models.common import connect_db, db
from src.models.movie import Movie
from src.models.movie_poster import MoviePoster
from src.models.service import Service
from src.models.streaming_option import StreamingOption
from tests.data import show_stargate
from tests.utilities import service_generator

# ==================================================

app = create_app("freestreammovies_test", testing=True)
connect_db(app)
app.app_context().push()

db.drop_all()
db.create_all()

# --------------------------------------------------


class StreamingAvailabilityAdapterUnitTests(TestCase):
    """Unit tests for Streaming Availability Adapter functions."""

    def test_transform_show_json_into_movie_dict(self):
        """A show JSON should successfully be transformed into a dict that Movie can use."""

        # Arrange
        show = deepcopy(show_stargate)

        expected_result = {
            'id': show_stargate['id'],
            'imdb_id': show_stargate['imdbId'],
            'tmdb_id': show_stargate['tmdbId'],
            'title': show_stargate['title'],
            'overview': show_stargate['overview'],
            'release_year': show_stargate['releaseYear'],
            'original_title': show_stargate['originalTitle'],
            'directors': show_stargate['directors'],
            'cast': show_stargate['cast'],
            'rating': show_stargate['rating'],
            'runtime': show_stargate['runtime']
        }

        # Act
        result = transform_show_json_into_movie_dict(show)

        # Assert
        self.assertEqual(result, expected_result)

    def test_transform_streaming_option_json_into_dict(self):
        """A streaming option JSON should successfully be transformed into a dict that StreamingOption can use."""

        # Arrange
        streaming_option_json = deepcopy(show_stargate['streamingOptions']['us'][2])
        movie_id = show_stargate['id']
        country_code = 'us'

        expected_result = {
            'movie_id': movie_id,
            'country_code': country_code,
            'service_id': show_stargate['streamingOptions']['us'][2]['service']['id'],
            'link': show_stargate['streamingOptions']['us'][2]['link'],
            'expires_soon': show_stargate['streamingOptions']['us'][2]['expiresSoon'],
            'expires_on': show_stargate['streamingOptions']['us'][2].get('expiresOn')
        }

        # Act
        result = transform_streaming_option_json_into_dict(streaming_option_json, movie_id, country_code)

        # Assert
        self.assertEqual(result, expected_result)

    def test_transform_image_set_json_into_movie_poster_list(self):
        """An image set JSON should successfully be transformed into a dict that MoviePoster can use."""

        # Arrange
        image_set = deepcopy(show_stargate['imageSet'])
        movie_id = show_stargate['id']

        expected_result = []
        for poster_size, link in show_stargate['imageSet']['verticalPoster'].items():
            expected_result.append({
                'movie_id': movie_id,
                'type': 'verticalPoster',
                'size': poster_size,
                'link': link
            })

        # Act
        result = transform_image_set_json_into_movie_poster_list(image_set, movie_id)

        # Assert
        self.assertEqual(result, expected_result)

    @patch('src.adapters.streaming_availability_adapter.transform_streaming_option_json_into_dict', autospec=True)
    @patch('src.adapters.streaming_availability_adapter.read_services_blacklist', autospec=True)
    def test_gather_streaming_options(
            self,
            mock_read_services_blacklist,
            mock_transform_streaming_option_json_into_dict):
        """
        When gathering streaming options, only free streaming options should be returned and
        non-free or blacklisted streaming options should not be returned.
        """

        # Arrange
        # 1st set contains only one free option
        # 2nd set contains one free option and one not free option
        # 3rd set contains one free option and one blacklisted option
        subtest_inputs = [
            [
                {
                    'service': {
                        'id': 'tubi'
                    },
                    'type': 'free'
                }
            ],
            [
                {
                    'service': {
                        'id': 'tubi'
                    },
                    'type': 'free'
                },
                {
                    'service': {
                        'id': 'Amazon'
                    },
                    'type': 'buy'
                }
            ],
            [
                {
                    'service': {
                        'id': 'tubi'
                    },
                    'type': 'free'
                },
                {
                    'service': {
                        'id': 'peacock'
                    },
                    'type': 'free'
                }
            ]
        ]

        for streaming_options_test_data in subtest_inputs:
            with self.subTest(streaming_options_test_data=streaming_options_test_data):

                # Arrange
                country_streaming_options_data = {
                    'ca': [deepcopy(test_data) for test_data in streaming_options_test_data],
                    'us': [deepcopy(test_data) for test_data in streaming_options_test_data]
                }

                movie_id = show_stargate['id']

                # Arrange mocks
                mock_read_services_blacklist.return_value = {'peacock'}

                def expected_streaming_option(country):
                    return {
                        'movie_id': movie_id,
                        'country_code': country,
                        'service_id': 'tubi'
                    }

                def side_effect_func(streaming_option_data, movie_id, country_code):
                    if country_code == 'ca' and streaming_option_data == streaming_options_test_data[0]:
                        return expected_streaming_option('ca')
                    elif country_code == 'us' and streaming_option_data == streaming_options_test_data[0]:
                        return expected_streaming_option('us')

                mock_transform_streaming_option_json_into_dict.side_effect = side_effect_func

                # Arrange expected
                expected_result = [expected_streaming_option('ca'), expected_streaming_option('us')]

                # Act
                result = gather_streaming_options(country_streaming_options_data, movie_id)

                # Assert
                self.assertEqual(result, expected_result)

                self.assertEqual(
                    mock_transform_streaming_option_json_into_dict.call_args_list,
                    [call(streaming_options_test_data[0], movie_id, 'ca'),
                     call(streaming_options_test_data[0], movie_id, 'us')]
                )

                # clean up
                mock_transform_streaming_option_json_into_dict.reset_mock()

    @patch('src.adapters.streaming_availability_adapter.transform_streaming_option_json_into_dict', autospec=True)
    @patch('src.adapters.streaming_availability_adapter.read_services_blacklist', autospec=True)
    def test_gather_streaming_options_with_no_free_options(
            self,
            mock_read_services_blacklist,
            mock_transform_streaming_option_json_into_dict):
        """When there aren't any free options, an empty list should be returned."""

        # Arrange
        streaming_option_test_data = {
            'service': {
                'id': 'Amazon'
            },
            'type': 'subscription'
        }

        country_streaming_options_data = {
            'us': [deepcopy(streaming_option_test_data)]
        }

        movie_id = show_stargate['id']

        # Arrange mocks
        mock_read_services_blacklist.return_value = {'peacock'}

        # Arrange expected
        expected_result = []

        # Act
        result = gather_streaming_options(country_streaming_options_data, movie_id)

        # Assert
        self.assertEqual(result, expected_result)

        mock_transform_streaming_option_json_into_dict.assert_not_called()

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
        db.session.query(MoviePoster).delete()
        db.session.query(StreamingOption).delete()
        db.session.query(Movie).delete()
        db.session.query(Service).delete()

        db.session.commit()

    def tearDown(self):
        db.session.rollback()

    def test_store_movie_and_streaming_options_for_new_data(self):
        """
        Tests for successfully adding a movie and its streaming options to the database
        when they don't already exist in the database.
        """

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

    def test_store_movie_and_streaming_options_for_updating_data(self):
        """Tests for successfully updating old data in the database."""

        # Arrange
        services = service_generator(1)
        service00_id = services[0].id
        db.session.add_all(services)
        db.session.commit()

        movie_id = "movie1"

        def create_show_json(service_id: str, movie_id: str, subscript: str) -> dict:
            link00 = f"www.youtube.com/{movie_id}-{subscript}"
            streaming_options_json = {
                "us": [
                    {
                        "service": {"id": service_id},
                        "type": "free",
                        "link": link00,
                        "expiresSoon": False
                    }]
            }

            image_set_json = {
                "verticalPoster": {
                    "w240": f"example.com/w240-{subscript}",
                    "w360": f"example.com/w360-{subscript}"
                }
            }

            show_json = {
                "id": movie_id,
                "imdbId": "tt0468569",
                "tmdbId": "movie/155",
                "title": f"{subscript} title",
                "overview": f"{subscript} description",
                "releaseYear": 2008,
                "originalTitle": f"{subscript} title",
                "cast": ["person1", "person2"],
                "rating": 87,
                "runtime": 152,
                "imageSet": image_set_json,
                "streamingOptions": streaming_options_json
            }

            return show_json

        subscript = 'old'
        show_json_old = create_show_json(service00_id, movie_id, subscript)
        store_movie_and_streaming_options(deepcopy(show_json_old))

        subscript = 'new'
        show_json_new = create_show_json(service00_id, movie_id, subscript)
        streaming_option_link_new = f"www.youtube.com/{movie_id}-{subscript}"

        # Act
        store_movie_and_streaming_options(deepcopy(show_json_new))

        # Assert
        movies = db.session.query(Movie).all()
        self.assertEqual(len(movies), 1)
        self.assertEqual(movies[0].id, movie_id)
        self.assertEqual(movies[0].title, show_json_new['title'])
        self.assertEqual(movies[0].overview, show_json_new['overview'])

        movie_posters = db.session.query(MoviePoster).all()
        self.assertEqual(len(movie_posters), 2)
        for movie_poster in movie_posters:
            self.assertEqual(movie_poster.movie_id, movie_id)
            self.assertEqual(movie_poster.type, "verticalPoster")
        self.assertEqual(movie_posters[0].size, "w240")
        self.assertEqual(movie_posters[0].link, "example.com/w240-new")
        self.assertEqual(movie_posters[1].size, "w360")
        self.assertEqual(movie_posters[1].link, "example.com/w360-new")

        streaming_options = db.session.query(StreamingOption).all()
        self.assertEqual(len(streaming_options), 1)
        self.assertEqual(streaming_options[0].link, streaming_option_link_new)


class StreamingAvailabilityAdapterIntegrationTestsTransformShow(TestCase):
    """Integration tests for transform_show()."""

    def test_show_transforms_into_dict(self):
        """Tests that a Streaming Availability Show JSON is transformed, and a dict is returned."""

        # Arrange
        show = deepcopy(show_stargate)

        movie_posters = []
        for poster_size, link in show_stargate['imageSet']['verticalPoster'].items():
            movie_posters.append({
                'movie_id': show_stargate['id'],
                'type': 'verticalPoster',
                'size': poster_size,
                'link': link
            })

        streaming_options = []
        for country, options in show_stargate['streamingOptions'].items():
            for i in range(1, 3):
                streaming_option = {
                    'movie_id': show_stargate['id'],
                    'country_code': country,
                    'service_id': options[i]['service']['id'],
                    'link': options[i]['link'],
                    'expires_soon': options[i]['expiresSoon']
                }
                if 'expiresOn' in options[i]:
                    streaming_option['expires_on'] = options[i]['expiresOn']
                streaming_options.append(streaming_option)

        expected_result = {
            'movies': [{
                'id': show_stargate['id'],
                'imdb_id': show_stargate['imdbId'],
                'tmdb_id': show_stargate['tmdbId'],
                'title': show_stargate['title'],
                'overview': show_stargate['overview'],
                'release_year': show_stargate['releaseYear'],
                'original_title': show_stargate['originalTitle'],
                'directors': deepcopy(show_stargate['directors']),
                'cast': deepcopy(show_stargate['cast']),
                'rating': show_stargate['rating'],
                'runtime': show_stargate['runtime']
            }],
            'movie_posters': movie_posters,
            'streaming_options': streaming_options
        }

        # Act
        result = transform_show(show)

        # Assert
        self.assertEqual(result, expected_result)
