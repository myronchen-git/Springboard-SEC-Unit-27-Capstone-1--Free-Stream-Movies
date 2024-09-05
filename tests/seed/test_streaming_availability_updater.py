import sys
from os.path import abspath, dirname, join

# Adds root folder as a working directory.
# This is needed so that imports can be found.
root_dir = abspath(join(dirname(__file__), '../../'))  # nopep8
sys.path.append(root_dir)  # nopep8

# --------------------------------------------------

from copy import deepcopy
from unittest import TestCase
from unittest.mock import ANY, MagicMock, call, patch

from src.app import create_app
from src.exceptions.StreamingAvailabilityApiError import \
    StreamingAvailabilityApiError
from src.models.common import connect_db, db
from src.seed.streaming_availability_updater import \
    get_updated_movies_and_streams_from_one_request

# ==================================================

app = create_app("freestreammovies_test", testing=True)
connect_db(app)
app.app_context().push()

db.drop_all()
db.create_all()

STREAMING_AVAILABILITY_CHANGES_URL = 'https://streaming-availability.p.rapidapi.com/changes'

# --------------------------------------------------


@patch('src.seed.streaming_availability_updater.store_movie_and_streaming_options', autospec=True)
@patch('src.seed.streaming_availability_updater.requests', autospec=True)
@patch('src.seed.streaming_availability_updater.RAPID_API_KEY')
class StreamingAvailabilityUpdaterGetUpdatedMoviesAndStreamsFromOneRequestUnitTests(TestCase):
    """Unit tests for get_updated_movies_and_streams_from_one_request()."""

    def setUp(self):
        self.country_code = 'us'
        self.service_ids = ['service00', 'service01']
        self.expected_catalogs = 'service00.free, service01.free'

    def test_get_updates_from_one_request_when_there_is_more_data_to_retrieve(
            self,
            mock_RAPID_API_KEY,
            mock_requests,
            mock_store_movie_and_streaming_options
    ):
        """
        Tests retrieving updated changes, with and without providing a "from" timestamp, and when there are changes
        returned and there is more data to retrieve.  It should return a tuple (True, timestamp) and store the Show
        JSON object from the response.
        """

        # Arrange
        expected_next_from_timestamp = 5555

        mock_response = MagicMock(name='mock_response')
        mock_response.status_code = 200
        mock_show_dict = MagicMock(name='mock_show_dict')
        mock_response.json.return_value = {
            'changes': [],
            'shows': {
                '123': mock_show_dict
            },
            'hasMore': True,
            'nextCursor': f'{expected_next_from_timestamp}:6666'
        }
        mock_requests.get.return_value = mock_response

        from_timestamps = (None, 4444)
        for from_timestamp in from_timestamps:
            with self.subTest(from_timestamp=from_timestamp):
                # Act
                result = get_updated_movies_and_streams_from_one_request(
                    self.country_code, self.service_ids, from_timestamp)

                # Assert
                expected_query_string = {'change_type': 'updated', 'country': self.country_code, 'item_type': 'show',
                                         'show_type': 'movie', 'catalogs': self.expected_catalogs}
                if from_timestamp:
                    expected_query_string['from'] = from_timestamp

                mock_requests.get.assert_called_once_with(
                    STREAMING_AVAILABILITY_CHANGES_URL,
                    headers={'X-RapidAPI-Key': mock_RAPID_API_KEY},
                    params=expected_query_string)

                mock_store_movie_and_streaming_options.assert_called_with(mock_show_dict)

                self.assertEqual(result, (True, expected_next_from_timestamp))

                # clean up
                mock_requests.reset_mock()
                mock_store_movie_and_streaming_options.reset_mock()

    def test_get_updates_from_one_request_and_receive_no_updates(
            self,
            mock_RAPID_API_KEY,
            mock_requests,
            mock_store_movie_and_streaming_options
    ):
        """Tests retrieving updated changes, but there aren't any changes in the response."""

        # Arrange
        from_timestamp = 4444

        mock_response = MagicMock(name='mock_response')
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'changes': [],
            'shows': {},
            'hasMore': False
        }
        mock_requests.get.return_value = mock_response

        # Act
        result = get_updated_movies_and_streams_from_one_request(
            self.country_code, self.service_ids, from_timestamp)

        # Assert
        expected_query_string = {'change_type': 'updated', 'country': self.country_code, 'item_type': 'show',
                                 'show_type': 'movie', 'catalogs': self.expected_catalogs, 'from': from_timestamp}

        mock_requests.get.assert_called_once_with(
            STREAMING_AVAILABILITY_CHANGES_URL,
            headers={'X-RapidAPI-Key': mock_RAPID_API_KEY},
            params=expected_query_string)

        mock_store_movie_and_streaming_options.assert_not_called()

        self.assertEqual(result, (False, None))

    def test_get_updates_from_one_request_and_body_has_no_more(
            self,
            mock_RAPID_API_KEY,
            mock_requests,
            mock_store_movie_and_streaming_options
    ):
        """
        Tests retrieving updated changes and there are changes returned, but there are no more changes after those.
        """

        # Arrange
        from_timestamp = 4444

        mock_response = MagicMock(name='mock_response')
        mock_response.status_code = 200

        mock_show_dict_1 = MagicMock(name='mock_show_dict_1')
        mock_show_dict_2 = MagicMock(name='mock_show_dict_2')
        last_changes_timestamp = 99
        mock_response.json.return_value = {
            'changes': [{'timestamp': last_changes_timestamp - 1}, {'timestamp': last_changes_timestamp}],
            'shows': {
                '1': mock_show_dict_1,
                '2': mock_show_dict_2
            },
            'hasMore': False
        }
        mock_requests.get.return_value = mock_response

        # Act
        result = get_updated_movies_and_streams_from_one_request(
            self.country_code, self.service_ids, from_timestamp)

        # Assert
        expected_query_string = {'change_type': 'updated', 'country': self.country_code, 'item_type': 'show',
                                 'show_type': 'movie', 'catalogs': self.expected_catalogs, 'from': from_timestamp}

        mock_requests.get.assert_called_once_with(
            STREAMING_AVAILABILITY_CHANGES_URL,
            headers={'X-RapidAPI-Key': mock_RAPID_API_KEY},
            params=expected_query_string)

        mock_store_movie_and_streaming_options.assert_has_calls([call(mock_show_dict_1), call(mock_show_dict_2)])

        self.assertEqual(result, (False, last_changes_timestamp + 1))

    def test_get_updates_from_one_request_with_too_old_timestamp(
            self,
            mock_RAPID_API_KEY,
            mock_requests,
            mock_store_movie_and_streaming_options
    ):
        """Tests that passing a "from" timestamp that is too old will cause a retry without a "from" timestamp."""

        # Arrange
        from_timestamp = 1
        expected_next_from_timestamp = 5555

        mock_failed_response = MagicMock(name='mock_failed_response')
        mock_failed_response.status_code = 400
        mock_failed_response.json.return_value = {
            'message': 'parameter "from" cannot be more than 31 days in the past'}

        mock_successful_response = MagicMock(name='mock_response')
        mock_successful_response.status_code = 200
        mock_show_dict = MagicMock(name='mock_show_dict')
        mock_successful_response.json.return_value = {
            'changes': [],
            'shows': {
                '123': mock_show_dict
            },
            'hasMore': True,
            'nextCursor': f'{expected_next_from_timestamp}:6666'
        }

        mock_requests.get.side_effect = lambda url, headers, params: \
            mock_failed_response if 'from' in params else mock_successful_response

        # Act
        result = get_updated_movies_and_streams_from_one_request(
            self.country_code, self.service_ids, from_timestamp)

        # Assert
        expected_failed_query_string = {'change_type': 'updated',
                                        'country': self.country_code,
                                        'item_type': 'show',
                                        'show_type': 'movie',
                                        'catalogs': self.expected_catalogs,
                                        'from': from_timestamp}
        expected_successful_query_string = deepcopy(expected_failed_query_string)
        del expected_successful_query_string['from']

        mock_requests.get.assert_has_calls([
            call(
                STREAMING_AVAILABILITY_CHANGES_URL,
                headers={'X-RapidAPI-Key': mock_RAPID_API_KEY},
                params=expected_failed_query_string
            ),
            call(
                STREAMING_AVAILABILITY_CHANGES_URL,
                headers={'X-RapidAPI-Key': mock_RAPID_API_KEY},
                params=expected_successful_query_string
            )
        ])

        mock_store_movie_and_streaming_options.assert_called_once_with(mock_show_dict)

        self.assertEqual(result, (True, expected_next_from_timestamp))

    def test_get_updates_from_one_request_and_not_get_status_code_200(
            self,
            mock_RAPID_API_KEY,
            mock_requests,
            mock_store_movie_and_streaming_options
    ):
        """Tests that getting a response with an unexpected status code should raise an error."""

        # Arrange
        from_timestamp = 4444

        mock_response = MagicMock(name='mock_response')
        mock_response.status_code = 500

        mock_requests.get.return_value = mock_response

        # Act/Assert
        self.assertRaises(
            StreamingAvailabilityApiError,
            get_updated_movies_and_streams_from_one_request,
            self.country_code,
            self.service_ids,
            from_timestamp)

        expected_query_string = {'change_type': 'updated', 'country': self.country_code, 'item_type': 'show',
                                 'show_type': 'movie', 'catalogs': self.expected_catalogs, 'from': from_timestamp}

        mock_requests.get.assert_called_once_with(
            STREAMING_AVAILABILITY_CHANGES_URL,
            headers={'X-RapidAPI-Key': mock_RAPID_API_KEY},
            params=expected_query_string)

        mock_store_movie_and_streaming_options.assert_not_called()
