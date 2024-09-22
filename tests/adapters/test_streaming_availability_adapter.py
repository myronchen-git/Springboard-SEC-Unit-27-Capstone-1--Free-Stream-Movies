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
    gather_streaming_options, transform_image_set_json_into_movie_poster_list,
    transform_show, transform_show_json_into_movie_dict,
    transform_streaming_option_json_into_dict)
from src.app import create_app
from src.models.common import connect_db, db
from tests.data import show_stargate

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
    @patch('src.adapters.streaming_availability_adapter.BLACKLISTED_SERVICES', new={'peacock'})
    def test_gather_streaming_options(
            self,
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
    @patch('src.adapters.streaming_availability_adapter.BLACKLISTED_SERVICES', new={'peacock'})
    def test_gather_streaming_options_with_no_free_options(
            self,
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

        # Arrange expected
        expected_result = []

        # Act
        result = gather_streaming_options(country_streaming_options_data, movie_id)

        # Assert
        self.assertEqual(result, expected_result)

        mock_transform_streaming_option_json_into_dict.assert_not_called()


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
