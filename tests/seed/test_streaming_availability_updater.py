import sys
from os.path import abspath, dirname, join

# Adds root folder as a working directory.
# This is needed so that imports can be found.
root_dir = abspath(join(dirname(__file__), '../../'))  # nopep8
sys.path.append(root_dir)  # nopep8

# --------------------------------------------------

from copy import deepcopy
from math import ceil
from unittest import TestCase
from unittest.mock import ANY, MagicMock, call, patch

from src.app import create_app
from src.exceptions.StreamingAvailabilityApiError import \
    StreamingAvailabilityApiError
from src.models.common import connect_db, db
from src.seed.common_constants import \
    STREAMING_AVAILABILITY_API_REQUEST_RATE_LIMIT_PER_DAY
from src.seed.streaming_availability_updater import (
    get_updated_movies_and_streaming_options,
    get_updated_movies_and_streams_from_one_request)
from tests.utilities import CopyingMock

# ==================================================

app = create_app("freestreammovies_test", testing=True)
connect_db(app)
app.app_context().push()

db.drop_all()
db.create_all()

STREAMING_AVAILABILITY_CHANGES_URL = 'https://streaming-availability.p.rapidapi.com/changes'

# --------------------------------------------------


@patch('src.seed.streaming_availability_updater.write_json_file_helper', new_callable=CopyingMock())
@patch('src.seed.streaming_availability_updater.get_updated_movies_and_streams_from_one_request', autospec=True)
@patch('src.seed.streaming_availability_updater.read_json_file_helper', autospec=True)
@patch('src.seed.streaming_availability_updater.CountryService', autospec=True)
@patch('src.seed.streaming_availability_updater.db', autospec=True)
class GetUpdatedMoviesAndStreamingOptionsUnitTests(TestCase):
    """Unit tests for get_updated_movies_and_streaming_options()."""

    def setUp(self):
        self.mock_countries_services = MagicMock(name='mock_countries_services')

    def test_get_updates_with_and_without_from_timestamps(
            self,
            mock_db,
            mock_CountryService,
            mock_read_json_file_helper,
            mock_get_updated_movies_and_streams_from_one_request,
            mock_write_json_file_helper
    ):
        """Tests that requests to retrieve updates are done with and without the "from" timestamps."""

        # Arrange
        mock_db.session.query.return_value.all.return_value = self.mock_countries_services

        expected_db_call = call.session.query(mock_CountryService).all().call_list()

        countries_services = {'ca': ['service00', 'service01'],
                              'us': ['service01', 'service02']}
        mock_CountryService.convert_list_to_dict.return_value = deepcopy(countries_services)

        mock_get_updated_movies_and_streams_from_one_request.return_value = (False, None)

        # [{condition: ..., expectation: ...}, {condition: ..., expectation: ...}]
        test_parameters = [{'from_timestamps': {},
                            'expected_from_timestamp': {'ca': None, 'us': None}},
                           {'from_timestamps': {'ca': 1000, 'us': 2000},
                               'expected_from_timestamp': {'ca': 1000, 'us': 2000}}]

        for test_parameter in test_parameters:
            with self.subTest(from_timestamps=test_parameter['from_timestamps']):
                # Arrange
                mock_read_json_file_helper.return_value = test_parameter['from_timestamps']

                # Act
                get_updated_movies_and_streaming_options()

                # Assert
                self.assertEqual(mock_db.mock_calls, expected_db_call)
                mock_CountryService.convert_list_to_dict.assert_called_once_with(self.mock_countries_services)
                mock_read_json_file_helper.assert_called_once()
                mock_get_updated_movies_and_streams_from_one_request.assert_has_calls(
                    [call('ca', countries_services['ca'], test_parameter['expected_from_timestamp']['ca']),
                     call('us', countries_services['us'], test_parameter['expected_from_timestamp']['us'])]
                )

                # clean up
                mock_db.reset_mock()
                mock_CountryService.reset_mock()
                mock_read_json_file_helper.reset_mock()
                mock_get_updated_movies_and_streams_from_one_request.reset_mock()

    def test_get_updates_when_there_are_no_updates(
            self,
            mock_db,
            mock_CountryService,
            mock_read_json_file_helper,
            mock_get_updated_movies_and_streams_from_one_request,
            mock_write_json_file_helper
    ):
        """
        Tests for the condition of when there are no updates, the next "from" timestamp is not saved and no more
        requests are made.

        Essentially tests that get_updated_movies_and_streams_from_one_request() returns has_more = false and
        next_from_timestamp = None.
        """

        # Arrange
        mock_db.session.query.return_value.all.return_value = self.mock_countries_services

        expected_db_call = call.session.query(mock_CountryService).all().call_list()

        countries_services = {'us': ['service00']}
        mock_CountryService.convert_list_to_dict.return_value = deepcopy(countries_services)

        mock_read_json_file_helper.return_value = {}

        mock_get_updated_movies_and_streams_from_one_request.return_value = (False, None)

        # Act
        get_updated_movies_and_streaming_options()

        # Assert
        self.assertEqual(mock_db.mock_calls, expected_db_call)
        mock_CountryService.convert_list_to_dict.assert_called_once_with(self.mock_countries_services)
        mock_read_json_file_helper.assert_called_once()
        mock_get_updated_movies_and_streams_from_one_request.assert_called_once_with(
            'us', countries_services['us'], None)
        mock_write_json_file_helper.assert_not_called()

    def test_get_updates_when_there_is_only_one_page_of_updates(
            self,
            mock_db,
            mock_CountryService,
            mock_read_json_file_helper,
            mock_get_updated_movies_and_streams_from_one_request,
            mock_write_json_file_helper
    ):
        """
        Tests that when getting updates and receiving only one page of updates, the next "from" timestamp is saved and
        there are no additional requests.

        Essentially tests that get_updated_movies_and_streams_from_one_request() returns has_more = false and
        next_from_timestamp = int.
        """

        # Arrange
        mock_db.session.query.return_value.all.return_value = self.mock_countries_services

        expected_db_call = call.session.query(mock_CountryService).all().call_list()

        countries_services = {'us': ['service00']}
        mock_CountryService.convert_list_to_dict.return_value = deepcopy(countries_services)

        mock_read_json_file_helper.return_value = {}

        next_from_timestamp = 12345
        mock_get_updated_movies_and_streams_from_one_request.return_value = (False, next_from_timestamp)

        # Act
        get_updated_movies_and_streaming_options()

        # Assert
        self.assertEqual(mock_db.mock_calls, expected_db_call)
        mock_CountryService.convert_list_to_dict.assert_called_once_with(self.mock_countries_services)
        mock_read_json_file_helper.assert_called_once()
        mock_get_updated_movies_and_streams_from_one_request.assert_called_once_with(
            'us', countries_services['us'], None)
        mock_write_json_file_helper.assert_called_once_with(ANY, {'us': next_from_timestamp})

        # clean up
        mock_write_json_file_helper.reset_mock()

    def test_get_updates_when_there_is_more_to_get(
            self,
            mock_db,
            mock_CountryService,
            mock_read_json_file_helper,
            mock_get_updated_movies_and_streams_from_one_request,
            mock_write_json_file_helper
    ):
        """
        Tests that when getting updates and receiving only one page of updates, the next "from" timestamp is saved and
        there are additional requests.

        Essentially tests that get_updated_movies_and_streams_from_one_request() returns has_more = true and
        next_from_timestamp = int.
        """

        # Arrange
        mock_db.session.query.return_value.all.return_value = self.mock_countries_services

        expected_db_call = call.session.query(mock_CountryService).all().call_list()

        countries_services = {'us': ['service00']}
        mock_CountryService.convert_list_to_dict.return_value = deepcopy(countries_services)

        mock_read_json_file_helper.return_value = {}

        # return (True, 1000) first, then (False, 2000)
        mock_get_updated_movies_and_streams_from_one_request.side_effect = \
            lambda country_code, service_ids, from_timestamp: \
            (True, 1000) if from_timestamp == None else (False, 2000)

        # Act
        get_updated_movies_and_streaming_options()

        # Assert
        self.assertEqual(mock_db.mock_calls, expected_db_call)
        mock_CountryService.convert_list_to_dict.assert_called_once_with(self.mock_countries_services)
        mock_read_json_file_helper.assert_called_once()
        mock_get_updated_movies_and_streams_from_one_request.assert_has_calls([
            call('us', countries_services['us'], None),
            call('us', countries_services['us'], 1000)
        ])
        mock_write_json_file_helper.assert_has_calls([
            call(ANY, {'us': 1000}),
            call(ANY, {'us': 2000})
        ])

        # clean up
        mock_write_json_file_helper.reset_mock()

    def test_get_updates_is_within_rate_limits(
            self,
            mock_db,
            mock_CountryService,
            mock_read_json_file_helper,
            mock_get_updated_movies_and_streams_from_one_request,
            mock_write_json_file_helper
    ):
        """
        Tests that the number of requests does not go near the rate limit.  This only considers multiple countries,
        since total requests for one country will always be less than for multiple countries.
        """

        # Arrange
        mock_db.session.query.return_value.all.return_value = self.mock_countries_services

        expected_db_call = call.session.query(mock_CountryService).all().call_list()

        countries_services = {'ca': ['service00', 'service01'],
                              'us': ['service01', 'service02']}
        mock_CountryService.convert_list_to_dict.return_value = deepcopy(countries_services)

        mock_read_json_file_helper.return_value = {}

        expected_max_request_count = ceil(STREAMING_AVAILABILITY_API_REQUEST_RATE_LIMIT_PER_DAY * 0.8)

        def side_effect(country_code, service_ids, from_timestamp):
            if mock_get_updated_movies_and_streams_from_one_request.call_count < expected_max_request_count / 2:
                return (True, 12345)
            elif mock_get_updated_movies_and_streams_from_one_request.call_count == \
                    ceil(expected_max_request_count / 2):
                return (False, 12345)
            else:
                return (True, 12345)

        mock_get_updated_movies_and_streams_from_one_request.side_effect = side_effect

        # Act
        get_updated_movies_and_streaming_options()

        # Assert
        self.assertEqual(mock_db.mock_calls, expected_db_call)
        mock_CountryService.convert_list_to_dict.assert_called_once_with(self.mock_countries_services)
        mock_read_json_file_helper.assert_called_once()
        self.assertEqual(mock_get_updated_movies_and_streams_from_one_request.call_count,
                         expected_max_request_count)
        mock_get_updated_movies_and_streams_from_one_request.assert_any_call('ca', countries_services['ca'], 12345)
        mock_get_updated_movies_and_streams_from_one_request.assert_any_call('us', countries_services['us'], 12345)
        self.assertEqual(mock_write_json_file_helper.call_count,
                         expected_max_request_count)
        mock_write_json_file_helper.assert_called_with(ANY, {'ca': 12345, 'us': 12345})

        # clean up
        mock_write_json_file_helper.reset_mock()

    def test_get_updates_returns_error(
            self,
            mock_db,
            mock_CountryService,
            mock_read_json_file_helper,
            mock_get_updated_movies_and_streams_from_one_request,
            mock_write_json_file_helper
    ):
        """
        If a Streaming Availability API call results in an error, then exit without saving the next
        "from" timestamp and do not make additional calls.
        """

        # Arrange
        mock_db.session.query.return_value.all.return_value = self.mock_countries_services

        expected_db_call = call.session.query(mock_CountryService).all().call_list()

        countries_services = {'us': ['service00']}
        mock_CountryService.convert_list_to_dict.return_value = deepcopy(countries_services)

        mock_read_json_file_helper.return_value = {}

        mock_get_updated_movies_and_streams_from_one_request.side_effect = StreamingAvailabilityApiError("")

        # Act
        get_updated_movies_and_streaming_options()

        # Assert
        self.assertEqual(mock_db.mock_calls, expected_db_call)
        mock_CountryService.convert_list_to_dict.assert_called_once_with(self.mock_countries_services)
        mock_read_json_file_helper.assert_called_once()
        mock_get_updated_movies_and_streams_from_one_request.assert_called_once_with(
            'us', countries_services['us'], None)
        mock_write_json_file_helper.assert_not_called()


@patch('src.seed.streaming_availability_updater.store_movie_and_streaming_options', autospec=True)
@patch('src.seed.streaming_availability_updater.requests', autospec=True)
@patch('src.seed.streaming_availability_updater.RAPID_API_KEY')
class GetUpdatedMoviesAndStreamsFromOneRequestUnitTests(TestCase):
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
