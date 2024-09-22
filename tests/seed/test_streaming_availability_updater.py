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
from src.seed.seed_updater_constants import \
    SA_API_PREFERRED_REQUEST_RATE_LIMIT_PER_DAY
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


@patch('src.seed.streaming_availability_updater.StreamingOption', autospec=True)
@patch('src.seed.streaming_availability_updater.MoviePoster', autospec=True)
@patch('src.seed.streaming_availability_updater.Movie', autospec=True)
@patch('src.seed.streaming_availability_updater.write_json_file_helper', new_callable=CopyingMock())
@patch('src.seed.streaming_availability_updater.get_updated_movies_and_streams_from_one_request', autospec=True)
@patch('src.seed.streaming_availability_updater.read_json_file_helper', autospec=True)
@patch('src.seed.streaming_availability_updater.CountryService', autospec=True)
@patch('src.seed.streaming_availability_updater.db', autospec=True)
class GetUpdatedMoviesAndStreamingOptionsUnitTests(TestCase):
    """
    Unit tests for get_updated_movies_and_streaming_options().
    Note that all patched imports using CopyingMock need to be reset after each test, since only one instance is used.
    """

    def setUp(self):
        self.mock_countries_services = MagicMock(name='mock_countries_services')

    def test_get_updates_with_and_without_from_timestamps(
            self,
            mock_db,
            mock_CountryService,
            mock_read_json_file_helper,
            mock_get_updated_movies_and_streams_from_one_request,
            mock_write_json_file_helper,
            mock_Movie,
            mock_MoviePoster,
            mock_StreamingOption
    ):
        """Tests that requests to retrieve updates are done with and without the "from" timestamps."""

        # Arrange subtest parameters
        # [{condition: ..., expectation: ...}, {condition: ..., expectation: ...}]
        test_parameters = [{'from_timestamps': {},
                            'expected_from_timestamp': {'ca': None, 'us': None}},
                           {'from_timestamps': {'ca': 1000, 'us': 2000},
                            'expected_from_timestamp': {'ca': 1000, 'us': 2000}}]

        for test_parameter in test_parameters:
            with self.subTest(from_timestamps=test_parameter['from_timestamps']):

                # Arrange
                countries_services = {'ca': ['service00', 'service01'],
                                      'us': ['service01', 'service02']}

                expected_next_from_timestamp = 9999

                # using strings in place of dictionaries in the lists should still work, since only the object matters
                def side_effect_func(country_code, service_ids, from_timestamp):
                    return {
                        'movies': {f'movie_{country_code}': 'movie'},
                        'movie_posters': {f'movie_poster_{country_code}': 'movie_poster'},
                        'streaming_options': {f'streaming_option_{country_code}': 'streaming_option'},
                        'has_more': False,
                        'next_from_timestamp': expected_next_from_timestamp
                    }

                # Arrange mocks
                mock_db.session.query.return_value.all.return_value = self.mock_countries_services
                mock_CountryService.convert_list_to_dict.return_value = deepcopy(countries_services)
                mock_read_json_file_helper.return_value = test_parameter['from_timestamps']
                mock_get_updated_movies_and_streams_from_one_request.side_effect = side_effect_func

                # Arrange expected
                expected_db_calls = call.session.query(mock_CountryService).all().call_list()
                expected_db_calls.append(call.session.commit())

                expected_get_updated_movies_and_streams_from_one_request_calls = [
                    call(
                        country_code,
                        countries_services[country_code],
                        test_parameter['expected_from_timestamp'][country_code]
                    )
                    for country_code in countries_services
                ]

                # get base from_timestamps then deepcopy and add to new calls
                expected_write_json_calls = []
                temp_from_timestamps = deepcopy(test_parameter['from_timestamps'])
                for country_code in countries_services:
                    temp_from_timestamps |= {country_code: expected_next_from_timestamp}
                    expected_write_json_calls.append(call(
                        ANY,
                        deepcopy(temp_from_timestamps)
                    ))

                # Act
                get_updated_movies_and_streaming_options()

                # Assert
                self.assertEqual(mock_db.mock_calls, expected_db_calls)
                mock_CountryService.convert_list_to_dict.assert_called_once_with(self.mock_countries_services)
                mock_read_json_file_helper.assert_called_once()
                mock_get_updated_movies_and_streams_from_one_request.assert_has_calls(
                    expected_get_updated_movies_and_streams_from_one_request_calls
                )
                mock_write_json_file_helper.assert_has_calls(expected_write_json_calls)

                num_countries = len(countries_services)
                mock_Movie.upsert_database.assert_called_once_with(
                    ['movie' for i in range(num_countries)])
                mock_MoviePoster.upsert_database.assert_called_once_with(
                    ['movie_poster' for i in range(num_countries)])
                mock_StreamingOption.insert_database.assert_called_once_with(
                    ['streaming_option' for i in range(num_countries)])

                # clean up
                mock_db.reset_mock()
                mock_CountryService.reset_mock()
                mock_read_json_file_helper.reset_mock()
                mock_get_updated_movies_and_streams_from_one_request.reset_mock()
                mock_write_json_file_helper.reset_mock()
                mock_Movie.reset_mock()
                mock_MoviePoster.reset_mock()
                mock_StreamingOption.reset_mock()

    def test_get_updates_when_there_are_no_updates(
            self,
            mock_db,
            mock_CountryService,
            mock_read_json_file_helper,
            mock_get_updated_movies_and_streams_from_one_request,
            mock_write_json_file_helper,
            mock_Movie,
            mock_MoviePoster,
            mock_StreamingOption
    ):
        """
        Tests for the condition of when there are no updates, the next "from" timestamp is not saved and no more
        requests are made.

        Essentially tests that get_updated_movies_and_streams_from_one_request() returns
        'movies': {}, 'movie_posters': {}, 'streaming_options': {}, has_more = false, and
        next_from_timestamp = None.
        """

        # Arrange
        countries_services = {'us': ['service00']}

        # Arrange mocks
        mock_db.session.query.return_value.all.return_value = self.mock_countries_services
        mock_CountryService.convert_list_to_dict.return_value = deepcopy(countries_services)
        mock_read_json_file_helper.return_value = {}
        mock_get_updated_movies_and_streams_from_one_request.return_value = {
            'movies': {},
            'movie_posters': {},
            'streaming_options': {},
            'has_more': False,
            'next_from_timestamp': None
        }

        # Arrange expected
        expected_db_calls = call.session.query(mock_CountryService).all().call_list()
        expected_db_calls.append(call.session.commit())

        # Act
        get_updated_movies_and_streaming_options()

        # Assert
        self.assertEqual(mock_db.mock_calls, expected_db_calls)
        mock_CountryService.convert_list_to_dict.assert_called_once_with(self.mock_countries_services)
        mock_read_json_file_helper.assert_called_once()
        mock_get_updated_movies_and_streams_from_one_request.assert_called_once_with(
            'us', countries_services['us'], None)
        mock_write_json_file_helper.assert_not_called()

        mock_Movie.upsert_database.assert_called_once_with([])
        mock_MoviePoster.upsert_database.assert_called_once_with([])
        mock_StreamingOption.insert_database.assert_called_once_with([])

    def test_get_updates_when_there_is_only_one_page_of_updates(
            self,
            mock_db,
            mock_CountryService,
            mock_read_json_file_helper,
            mock_get_updated_movies_and_streams_from_one_request,
            mock_write_json_file_helper,
            mock_Movie,
            mock_MoviePoster,
            mock_StreamingOption
    ):
        """
        Tests that when getting updates and receiving only one page of updates, the next "from" timestamp is saved and
        there are no additional requests.

        Essentially tests that get_updated_movies_and_streams_from_one_request() returns
        data for movies, movie_posters, streaming_options, has_more = false, and next_from_timestamp = int.
        """

        # Arrange
        countries_services = {'us': ['service00']}
        expected_next_from_timestamp = 12345

        # Arrange mocks
        mock_db.session.query.return_value.all.return_value = self.mock_countries_services
        mock_CountryService.convert_list_to_dict.return_value = deepcopy(countries_services)
        mock_read_json_file_helper.return_value = {}
        mock_get_updated_movies_and_streams_from_one_request.return_value = {
            'movies': {'movie1': 'movie'},
            'movie_posters': {'poster1': 'movie_poster'},
            'streaming_options': {'option1': 'streaming_option'},
            'has_more': False,
            'next_from_timestamp': expected_next_from_timestamp
        }

        # Arrange expected
        expected_db_calls = call.session.query(mock_CountryService).all().call_list()
        expected_db_calls.append(call.session.commit())

        # Act
        get_updated_movies_and_streaming_options()

        # Assert
        self.assertEqual(mock_db.mock_calls, expected_db_calls)
        mock_CountryService.convert_list_to_dict.assert_called_once_with(self.mock_countries_services)
        mock_read_json_file_helper.assert_called_once()
        mock_get_updated_movies_and_streams_from_one_request.assert_called_once_with(
            'us', countries_services['us'], None)
        mock_write_json_file_helper.assert_called_once_with(ANY, {'us': expected_next_from_timestamp})

        num_countries = len(countries_services)
        mock_Movie.upsert_database.assert_called_once_with(
            ['movie' for i in range(num_countries)])
        mock_MoviePoster.upsert_database.assert_called_once_with(
            ['movie_poster' for i in range(num_countries)])
        mock_StreamingOption.insert_database.assert_called_once_with(
            ['streaming_option' for i in range(num_countries)])

        # clean up
        mock_write_json_file_helper.reset_mock()

    def test_get_updates_when_there_is_more_to_get(
            self,
            mock_db,
            mock_CountryService,
            mock_read_json_file_helper,
            mock_get_updated_movies_and_streams_from_one_request,
            mock_write_json_file_helper,
            mock_Movie,
            mock_MoviePoster,
            mock_StreamingOption
    ):
        """
        Tests that when getting updates and receiving only one page of updates, the next "from" timestamp is saved and
        there are additional requests.

        Essentially tests that get_updated_movies_and_streams_from_one_request() returns
        data for movies, movie_posters, streaming_options, has_more = true, and next_from_timestamp = int.
        """

        # Arrange
        countries_services = {'us': ['service00']}
        expected_next_from_timestamps = [1000, 2000]

        # using strings in place of dictionaries in the lists should still work, since only the object matters
        def side_effect_func(country_code, service_ids, from_timestamp):
            if not from_timestamp:
                return {
                    'movies': {'movie1': 'movie'},
                    'movie_posters': {'poster1': 'movie_poster'},
                    'streaming_options': {'option1': 'streaming_option'},
                    'has_more': True,
                    'next_from_timestamp': expected_next_from_timestamps[0]
                }
            else:
                return {
                    'movies': {'movie2': 'movie'},
                    'movie_posters': {'poster2': 'movie_poster'},
                    'streaming_options': {'option2': 'streaming_option'},
                    'has_more': False,
                    'next_from_timestamp': expected_next_from_timestamps[1]
                }

        # Arrange mocks
        mock_db.session.query.return_value.all.return_value = self.mock_countries_services
        mock_CountryService.convert_list_to_dict.return_value = deepcopy(countries_services)
        mock_read_json_file_helper.return_value = {}
        mock_get_updated_movies_and_streams_from_one_request.side_effect = side_effect_func

        # Arrange expected
        expected_db_calls = call.session.query(mock_CountryService).all().call_list()
        expected_db_calls.append(call.session.commit())

        # Act
        get_updated_movies_and_streaming_options()

        # Assert
        self.assertEqual(mock_db.mock_calls, expected_db_calls)
        mock_CountryService.convert_list_to_dict.assert_called_once_with(self.mock_countries_services)
        mock_read_json_file_helper.assert_called_once()
        mock_get_updated_movies_and_streams_from_one_request.assert_has_calls([
            call('us', countries_services['us'], None),
            call('us', countries_services['us'], 1000)
        ])
        mock_write_json_file_helper.assert_has_calls([
            call(ANY, {'us': expected_next_from_timestamp})
            for expected_next_from_timestamp in expected_next_from_timestamps
        ])

        mock_Movie.upsert_database.assert_called_once_with(
            ['movie' for i in range(2)])
        mock_MoviePoster.upsert_database.assert_called_once_with(
            ['movie_poster' for i in range(2)])
        mock_StreamingOption.insert_database.assert_called_once_with(
            ['streaming_option' for i in range(2)])

        # clean up
        mock_write_json_file_helper.reset_mock()

    def test_get_updates_is_within_rate_limits(
            self,
            mock_db,
            mock_CountryService,
            mock_read_json_file_helper,
            mock_get_updated_movies_and_streams_from_one_request,
            mock_write_json_file_helper,
            mock_Movie,
            mock_MoviePoster,
            mock_StreamingOption
    ):
        """
        Tests that the number of requests does not go near the rate limit.  This only considers multiple countries,
        since total requests for one country will always be less than for multiple countries.
        Note that movie data is empty, because those are unimportant for this test.
        """

        # Arrange
        countries_services = {'ca': ['service00', 'service01'],
                              'us': ['service01', 'service02']}
        expected_next_from_timestamp = 12345

        def side_effect(country_code, service_ids, from_timestamp):
            # empty because unimportant
            transformed_request_data = {
                'movies': {},
                'movie_posters': {},
                'streaming_options': {}
            }

            # Since there are >1 countries, stop requests for first country at 50% call count.
            # Continue requesting for second country indefinitely.
            if mock_get_updated_movies_and_streams_from_one_request.call_count < expected_max_request_count / 2:
                transformed_request_data.update({'has_more': True, 'next_from_timestamp': 12345})
                return transformed_request_data
            elif mock_get_updated_movies_and_streams_from_one_request.call_count == \
                    ceil(expected_max_request_count / 2):
                transformed_request_data.update({'has_more': False, 'next_from_timestamp': 12345})
                return transformed_request_data
            else:
                transformed_request_data.update({'has_more': True, 'next_from_timestamp': 12345})
                return transformed_request_data

        # Arrange mocks
        mock_db.session.query.return_value.all.return_value = self.mock_countries_services
        mock_CountryService.convert_list_to_dict.return_value = deepcopy(countries_services)
        mock_read_json_file_helper.return_value = {}
        mock_get_updated_movies_and_streams_from_one_request.side_effect = side_effect

        # Arrange expected
        expected_db_calls = call.session.query(mock_CountryService).all().call_list()
        expected_db_calls.append(call.session.commit())
        expected_max_request_count = ceil(SA_API_PREFERRED_REQUEST_RATE_LIMIT_PER_DAY)

        # Act
        get_updated_movies_and_streaming_options()

        # Assert
        self.assertEqual(mock_db.mock_calls, expected_db_calls)
        mock_CountryService.convert_list_to_dict.assert_called_once_with(self.mock_countries_services)
        mock_read_json_file_helper.assert_called_once()
        self.assertEqual(mock_get_updated_movies_and_streams_from_one_request.call_count,
                         expected_max_request_count)
        for country_code in countries_services:
            mock_get_updated_movies_and_streams_from_one_request.assert_any_call(
                country_code, countries_services[country_code], expected_next_from_timestamp)
        self.assertEqual(mock_write_json_file_helper.call_count,
                         expected_max_request_count)
        mock_write_json_file_helper.assert_called_with(
            ANY,
            {'ca': expected_next_from_timestamp, 'us': expected_next_from_timestamp}
        )

        mock_Movie.upsert_database.assert_called_once()
        mock_MoviePoster.upsert_database.assert_called_once()
        mock_StreamingOption.insert_database.assert_called_once()

        # clean up
        mock_write_json_file_helper.reset_mock()

    def test_get_updates_returns_error(
            self,
            mock_db,
            mock_CountryService,
            mock_read_json_file_helper,
            mock_get_updated_movies_and_streams_from_one_request,
            mock_write_json_file_helper,
            mock_Movie,
            mock_MoviePoster,
            mock_StreamingOption
    ):
        """
        If a Streaming Availability API call results in an error, then exit without saving the next "from" timestamp,
        do not make additional calls, and save all movie data, retrieved so far, into the database.
        Note that the database upserts are checked to see if they have been run once.  In production, there may be
        data obtained from other countries before an exception is thrown.
        """

        # Arrange
        countries_services = {'us': ['service00']}

        # Arrange mocks
        mock_db.session.query.return_value.all.return_value = self.mock_countries_services
        mock_CountryService.convert_list_to_dict.return_value = deepcopy(countries_services)
        mock_read_json_file_helper.return_value = {}
        mock_get_updated_movies_and_streams_from_one_request.side_effect = StreamingAvailabilityApiError("")

        # Arrange expected
        expected_db_calls = call.session.query(mock_CountryService).all().call_list()
        expected_db_calls.append(call.session.commit())

        # Act
        get_updated_movies_and_streaming_options()

        # Assert
        self.assertEqual(mock_db.mock_calls, expected_db_calls)
        mock_CountryService.convert_list_to_dict.assert_called_once_with(self.mock_countries_services)
        mock_read_json_file_helper.assert_called_once()
        mock_get_updated_movies_and_streams_from_one_request.assert_called_once_with(
            'us', countries_services['us'], None)
        mock_write_json_file_helper.assert_not_called()

        mock_Movie.upsert_database.assert_called_once()
        mock_MoviePoster.upsert_database.assert_called_once()
        mock_StreamingOption.insert_database.assert_called_once()


@patch('src.seed.streaming_availability_updater.make_unique_transformed_show_data', autospec=True)
@patch('src.seed.streaming_availability_updater.delete_country_movie_streaming_options', autospec=True)
@patch('src.seed.streaming_availability_updater.requests', autospec=True)
@patch('src.seed.streaming_availability_updater.RAPID_API_KEY')
class GetUpdatedMoviesAndStreamsFromOneRequestUnitTests(TestCase):
    """Unit tests for get_updated_movies_and_streams_from_one_request()."""

    def setUp(self):
        self.country_code = 'us'
        self.service_ids = ['service00', 'service01']
        self.expected_catalogs = 'service00.free, service01.free'

        # using strings in place of dictionaries in the dict values should still work, since only the object matters
        self.unique_transformed_show_data = {
            'movies': {'movie1': 'movie1'},
            'movie_posters': {'poster1': 'poster1'},
            'streaming_options': {'option1': 'option1'}
        }

    def test_get_updates_from_one_request_when_there_is_more_data_to_retrieve(
            self,
            mock_RAPID_API_KEY,
            mock_requests,
            mock_delete_country_movie_streaming_options,
            mock_make_unique_transformed_show_data
    ):
        """
        Tests retrieving updated changes, with and without providing a "from" timestamp, and when there are changes
        returned and there is more data to retrieve.  It should return a dict {'movies', 'movie_posters',
        'streaming_options', 'has_more', 'next_from_timestamp'}.
        """

        # Arrange subtest parameters
        from_timestamps = (None, 4444)
        for from_timestamp in from_timestamps:
            with self.subTest(from_timestamp=from_timestamp):

                # Arrange
                show_id = '123'
                show = {'id': show_id}
                expected_next_from_timestamp = 5555
                has_more = True

                # Arrange mocks
                mock_response = MagicMock(name='mock_response')
                mock_response.status_code = 200
                mock_response.json.return_value = {
                    'changes': [],
                    'shows': {
                        show_id: deepcopy(show)
                    },
                    'hasMore': has_more,
                    'nextCursor': f'{expected_next_from_timestamp}:6666'
                }
                mock_requests.get.return_value = mock_response

                mock_make_unique_transformed_show_data.return_value = deepcopy(self.unique_transformed_show_data)

                # Arrange expected
                expected_query_string = {'change_type': 'updated', 'country': self.country_code, 'item_type': 'show',
                                         'show_type': 'movie', 'catalogs': self.expected_catalogs}
                if from_timestamp:
                    expected_query_string['from'] = from_timestamp

                expected_result = deepcopy(self.unique_transformed_show_data)
                expected_result |= {'has_more': has_more, 'next_from_timestamp': expected_next_from_timestamp}

                # Act
                result = get_updated_movies_and_streams_from_one_request(
                    self.country_code, self.service_ids, from_timestamp)

                # Assert
                mock_requests.get.assert_called_once_with(
                    STREAMING_AVAILABILITY_CHANGES_URL,
                    headers={'X-RapidAPI-Key': mock_RAPID_API_KEY},
                    params=expected_query_string)

                mock_delete_country_movie_streaming_options.assert_called_once_with(show_id, self.country_code)
                mock_make_unique_transformed_show_data.assert_called_once_with(show)

                self.assertEqual(result, expected_result)

                # clean up
                mock_requests.reset_mock()
                mock_delete_country_movie_streaming_options.reset_mock()
                mock_make_unique_transformed_show_data.reset_mock()

    def test_get_updates_from_one_request_and_receive_no_updates(
            self,
            mock_RAPID_API_KEY,
            mock_requests,
            mock_delete_country_movie_streaming_options,
            mock_make_unique_transformed_show_data
    ):
        """Tests retrieving updated changes, but there aren't any changes in the response."""

        # Arrange
        from_timestamp = 4444
        has_more = False

        # Arrange mocks
        mock_response = MagicMock(name='mock_response')
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'changes': [],
            'shows': {},
            'hasMore': has_more
        }
        mock_requests.get.return_value = mock_response

        # Arrange expected
        expected_query_string = {'change_type': 'updated', 'country': self.country_code, 'item_type': 'show',
                                 'show_type': 'movie', 'catalogs': self.expected_catalogs, 'from': from_timestamp}

        expected_result = {'has_more': has_more, 'next_from_timestamp': None}

        # Act
        result = get_updated_movies_and_streams_from_one_request(
            self.country_code, self.service_ids, from_timestamp)

        # Assert
        mock_requests.get.assert_called_once_with(
            STREAMING_AVAILABILITY_CHANGES_URL,
            headers={'X-RapidAPI-Key': mock_RAPID_API_KEY},
            params=expected_query_string)

        mock_delete_country_movie_streaming_options.assert_not_called()
        mock_make_unique_transformed_show_data.assert_not_called()

        self.assertEqual(result, expected_result)

    def test_get_updates_from_one_request_and_body_has_no_more(
            self,
            mock_RAPID_API_KEY,
            mock_requests,
            mock_delete_country_movie_streaming_options,
            mock_make_unique_transformed_show_data
    ):
        """
        Tests retrieving updated changes and there are changes returned, but there are no more changes after those.
        """

        # Arrange
        from_timestamp = 4444
        shows = [{'id': '1'}, {'id': '2'}]
        has_more = False
        last_changes_timestamp = 99

        # Arrange mocks
        mock_response = MagicMock(name='mock_response')
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'changes': [{'timestamp': last_changes_timestamp - 1}, {'timestamp': last_changes_timestamp}],
            'shows': {
                shows[0]['id']: deepcopy(shows[0]),
                shows[1]['id']: deepcopy(shows[1])
            },
            'hasMore': has_more
        }
        mock_requests.get.return_value = mock_response

        mock_make_unique_transformed_show_data.return_value = deepcopy(self.unique_transformed_show_data)

        # Arrange expected
        expected_query_string = {'change_type': 'updated', 'country': self.country_code, 'item_type': 'show',
                                 'show_type': 'movie', 'catalogs': self.expected_catalogs, 'from': from_timestamp}

        expected_result = deepcopy(self.unique_transformed_show_data)
        expected_result['has_more'] = has_more
        expected_result['next_from_timestamp'] = last_changes_timestamp + 1

        # Act
        result = get_updated_movies_and_streams_from_one_request(
            self.country_code, self.service_ids, from_timestamp)

        # Assert
        mock_requests.get.assert_called_once_with(
            STREAMING_AVAILABILITY_CHANGES_URL,
            headers={'X-RapidAPI-Key': mock_RAPID_API_KEY},
            params=expected_query_string)

        mock_delete_country_movie_streaming_options.assert_has_calls([
            call('1', self.country_code),
            call('2', self.country_code)
        ])
        mock_make_unique_transformed_show_data.assert_has_calls([
            call(shows[0]),
            call(shows[1])
        ])

        self.assertEqual(result, expected_result)

    def test_get_updates_from_one_request_with_too_old_timestamp(
            self,
            mock_RAPID_API_KEY,
            mock_requests,
            mock_delete_country_movie_streaming_options,
            mock_make_unique_transformed_show_data
    ):
        """
        Tests that passing a "from" timestamp that is too old will cause a retry without a "from" timestamp.
        Note that the expected result doesn't have movie data, because it is unimportant for this test.
        """

        # Arrange
        show = {'id': '123'}
        from_timestamp = 1
        expected_next_from_timestamp = 5555
        has_more = True

        # Arrange mocks
        mock_failed_response = MagicMock(name='mock_failed_response')
        mock_failed_response.status_code = 400
        mock_failed_response.json.return_value = {
            'message': 'parameter "from" cannot be more than 31 days in the past'}

        mock_successful_response = MagicMock(name='mock_response')
        mock_successful_response.status_code = 200
        mock_successful_response.json.return_value = {
            'changes': [],
            'shows': {
                show['id']: deepcopy(show)
            },
            'hasMore': has_more,
            'nextCursor': f'{expected_next_from_timestamp}:6666'
        }

        mock_requests.get.side_effect = lambda url, headers, params: \
            mock_failed_response if 'from' in params else mock_successful_response

        # Arrange expected
        expected_failed_query_string = {'change_type': 'updated',
                                        'country': self.country_code,
                                        'item_type': 'show',
                                        'show_type': 'movie',
                                        'catalogs': self.expected_catalogs,
                                        'from': from_timestamp}
        expected_successful_query_string = deepcopy(expected_failed_query_string)
        del expected_successful_query_string['from']

        expected_result = {
            'movies': {},
            'movie_posters': {},
            'streaming_options': {},
            'has_more': has_more,
            'next_from_timestamp': expected_next_from_timestamp
        }

        # Act
        result = get_updated_movies_and_streams_from_one_request(
            self.country_code, self.service_ids, from_timestamp)

        # Assert
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

        mock_delete_country_movie_streaming_options.assert_called_once_with(show['id'], self.country_code)
        mock_make_unique_transformed_show_data.assert_called_once_with(show)

        self.assertEqual(result, expected_result)

    def test_get_updates_from_one_request_and_not_get_status_code_200(
            self,
            mock_RAPID_API_KEY,
            mock_requests,
            mock_delete_country_movie_streaming_options,
            mock_make_unique_transformed_show_data
    ):
        """Tests that getting a response with an unexpected status code should raise an error."""

        # Arrange
        from_timestamp = 4444

        # Arrange mocks
        mock_response = MagicMock(name='mock_response')
        mock_response.status_code = 500
        mock_requests.get.return_value = mock_response

        # Arrange expected
        expected_query_string = {'change_type': 'updated', 'country': self.country_code, 'item_type': 'show',
                                 'show_type': 'movie', 'catalogs': self.expected_catalogs, 'from': from_timestamp}

        # Act/Assert
        self.assertRaises(
            StreamingAvailabilityApiError,
            get_updated_movies_and_streams_from_one_request,
            self.country_code,
            self.service_ids,
            from_timestamp)

        mock_requests.get.assert_called_once_with(
            STREAMING_AVAILABILITY_CHANGES_URL,
            headers={'X-RapidAPI-Key': mock_RAPID_API_KEY},
            params=expected_query_string)

        mock_delete_country_movie_streaming_options.assert_not_called()
        mock_make_unique_transformed_show_data.assert_not_called()
