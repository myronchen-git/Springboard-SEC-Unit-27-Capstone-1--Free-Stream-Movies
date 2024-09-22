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
from src.models.common import connect_db, db
from src.seed.streaming_availability_seeder import (
    get_movies_and_streams_from_one_request, seed_movies_and_streams)

# ==================================================

app = create_app("freestreammovies_test", testing=True)
connect_db(app)
app.app_context().push()

db.drop_all()
db.create_all()

# --------------------------------------------------


@patch('src.seed.streaming_availability_seeder.make_unique_transformed_show_data', autospec=True)
@patch('src.seed.streaming_availability_seeder.delete_country_movie_streaming_options', autospec=True)
@patch('src.seed.streaming_availability_seeder.requests', autospec=True)
@patch('src.seed.streaming_availability_seeder.RAPID_API_KEY')
class GetMoviesAndStreamsFromOneRequestUnitTests(TestCase):
    """Unit tests for get_movies_and_streams_from_one_request()."""

    def test_api_request_build(
            self,
            mock_RAPID_API_KEY,
            mock_requests,
            mock_delete_country_movie_streaming_options,
            mock_make_unique_transformed_show_data
    ):
        """Tests that the API request is correct when requesting data for one and many services."""

        service_ids_list = [
            ['service00'],
            ['service00', 'service01']
        ]

        for service_ids in service_ids_list:
            with self.subTest(service_ids=service_ids):

                # Arrange
                country = 'us'

                # Arrange expected
                expected_url = "https://streaming-availability.p.rapidapi.com/shows/search/filters"
                expected_headers = {'X-RapidAPI-Key': mock_RAPID_API_KEY}
                expected_params = {"country": country,
                                   "order_by": "original_title",
                                   "catalogs": ', '.join([service_id + '.free' for service_id in service_ids]),
                                   "show_type": "movie"}

                # Act
                get_movies_and_streams_from_one_request(country, service_ids)

                # Assert
                mock_requests.get.assert_called_once_with(
                    expected_url, headers=expected_headers, params=expected_params)

                # clean up
                mock_requests.reset_mock()

    def test_api_request_build_with_cursor(
            self,
            mock_RAPID_API_KEY,
            mock_requests,
            mock_delete_country_movie_streaming_options,
            mock_make_unique_transformed_show_data
    ):
        """Tests that the API request is correct when a cursor is present."""

        # Arrange
        country = 'us'
        service_ids = ['service00']
        cursor = "5692:76"

        # Arrange expected
        expected_url = "https://streaming-availability.p.rapidapi.com/shows/search/filters"
        expected_headers = {'X-RapidAPI-Key': mock_RAPID_API_KEY}
        expected_params = {"country": country,
                           "order_by": "original_title",
                           "catalogs": 'service00.free',
                           "show_type": "movie",
                           "cursor": cursor}

        # Act
        get_movies_and_streams_from_one_request(country, service_ids, cursor)

        # Assert
        mock_requests.get.assert_called_once_with(
            expected_url, headers=expected_headers, params=expected_params)

    def test_receiving_shows_and_there_is_more(
            self,
            mock_RAPID_API_KEY,
            mock_requests,
            mock_delete_country_movie_streaming_options,
            mock_make_unique_transformed_show_data
    ):
        """
        If the API response indicates there is more data to be requested, then put the next cursor in the return.
        Also, the return should include the shows' data.
        """

        # Arrange
        country = 'us'
        service_ids = ['service00']
        shows_input = [{'id': '1'}, {'id': '2'}]

        # Arrange mocks
        mock_response = MagicMock(name='mock_response')
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'shows': deepcopy(shows_input),
            'nextCursor': '1234:56',
            'hasMore': True
        }
        mock_requests.get.return_value = mock_response

        def side_effect_func(show):
            return mock_make_unique_transformed_show_data_side_effect(country, service_ids, show)

        mock_make_unique_transformed_show_data.side_effect = side_effect_func

        # Arrange expected
        expected_delete_calls = [call(show['id'], country) for show in shows_input]

        expected_result = {
            'movies': {movie['id']: movie for movie in shows_input},
            'movie_posters': {
                f'{movie['id']}-verticalPoster-w240': {
                    'movie_id': movie['id'],
                    'type': 'verticalPoster',
                    'size': 'w240',
                    'link': 'link' + movie['id']
                } for movie in shows_input
            },
            'streaming_options': {
                f'{movie['id']}-{country}-{service_ids[0]}-link{movie['id']}': {
                    'movie_id': movie['id'],
                    'country_code': country,
                    'service_id': service_ids[0],
                    'link': f'link{movie['id']}'
                } for movie in shows_input
            },
            'next_cursor': '1234:56'
        }

        # Act
        result = get_movies_and_streams_from_one_request(country, service_ids)

        # Assert
        self.assertEqual(result, expected_result)
        self.assertEqual(mock_delete_country_movie_streaming_options.mock_calls, expected_delete_calls)

    def test_receiving_any_number_of_shows_and_there_is_no_more(
            self,
            mock_RAPID_API_KEY,
            mock_requests,
            mock_delete_country_movie_streaming_options,
            mock_make_unique_transformed_show_data
    ):
        """Tests that the return includes the correct data when there are any number of shows in the API response."""

        shows_inputs = [
            [],
            [{'id': '1'}],
            [{'id': '1'}, {'id': '2'}]
        ]

        for shows_input in shows_inputs:
            with self.subTest(shows_input=shows_input):

                # Arrange
                country = 'us'
                service_ids = ['service00']

                # Arrange mocks
                mock_response = MagicMock(name='mock_response')
                mock_response.status_code = 200
                mock_response.json.return_value = {
                    'shows': deepcopy(shows_input),
                    'hasMore': False
                }
                mock_requests.get.return_value = mock_response

                def side_effect_func(show):
                    return mock_make_unique_transformed_show_data_side_effect(country, service_ids, show)

                mock_make_unique_transformed_show_data.side_effect = side_effect_func

                # Arrange expected
                expected_delete_calls = [call(show['id'], country) for show in shows_input]

                expected_result = {
                    'movies': {movie['id']: movie for movie in shows_input},
                    'movie_posters': {
                        f'{movie['id']}-verticalPoster-w240': {
                            'movie_id': movie['id'],
                            'type': 'verticalPoster',
                            'size': 'w240',
                            'link': 'link' + movie['id']
                        } for movie in shows_input
                    },
                    'streaming_options': {
                        f'{movie['id']}-{country}-{service_ids[0]}-link{movie['id']}': {
                            'movie_id': movie['id'],
                            'country_code': country,
                            'service_id': service_ids[0],
                            'link': f'link{movie['id']}'
                        } for movie in shows_input
                    },
                    'next_cursor': 'end'
                }

                # Act
                result = get_movies_and_streams_from_one_request(country, service_ids)

                # Assert
                self.assertEqual(result, expected_result)
                self.assertEqual(mock_delete_country_movie_streaming_options.mock_calls, expected_delete_calls)

                # clean up
                mock_delete_country_movie_streaming_options.reset_mock()

    def test_when_api_response_is_not_200(
            self,
            mock_RAPID_API_KEY,
            mock_requests,
            mock_delete_country_movie_streaming_options,
            mock_make_unique_transformed_show_data
    ):
        """When the API response is not 200, return None."""

        # Arrange
        country = 'us'
        service_ids = ['service00']

        # Arrange mocks
        mock_response = MagicMock(name='mock_response')
        mock_response.status_code = 400
        mock_requests.get.return_value = mock_response

        # Act
        result = get_movies_and_streams_from_one_request(country, service_ids)

        # Assert
        self.assertIsNone(result)
        mock_delete_country_movie_streaming_options.assert_not_called()
        mock_make_unique_transformed_show_data.assert_not_called()


@patch('src.seed.streaming_availability_seeder.StreamingOption', autospec=True)
@patch('src.seed.streaming_availability_seeder.MoviePoster', autospec=True)
@patch('src.seed.streaming_availability_seeder.Movie', autospec=True)
@patch('src.seed.streaming_availability_seeder.write_json_file_helper', autospec=True)
@patch('src.seed.streaming_availability_seeder.get_movies_and_streams_from_one_request', autospec=True)
@patch('src.seed.streaming_availability_seeder.read_json_file_helper', autospec=True)
@patch('src.seed.streaming_availability_seeder.CountryService', autospec=True)
@patch('src.seed.streaming_availability_seeder.db', autospec=True)
class SeedMoviesAndStreamsUnitTests(TestCase):
    """Unit tests for seed_movies_and_streams()."""

    def setUp(self):
        self.mock_countries_services_objs = MagicMock(name='mock_countries_services_objs')
        self.countries_services_dict = {'ca': ['service00', 'service01'],
                                        'us': ['service01', 'service02']}

    def test_seeding_when_cursors_file_does_not_exist(
            self,
            mock_db,
            mock_CountryService,
            mock_read_json_file_helper,
            mock_get_movies_and_streams_from_one_request,
            mock_write_json_file_helper,
            mock_Movie,
            mock_MoviePoster,
            mock_StreamingOption):
        """Tests seeding when there has not been seeding before."""

        # Arrange mocks
        mock_db.session.query.return_value.all.return_value = self.mock_countries_services_objs

        mock_CountryService.convert_list_to_dict.return_value = deepcopy(self.countries_services_dict)

        mock_read_json_file_helper.return_value = {}

        # using strings in place of dictionaries in the lists should still work, since only the object matters
        def side_effect_func(country_code, service_ids, cursor):
            return {
                'movies': {f'movie_{country_code}': 'movie'},
                'movie_posters': {f'movie_poster_{country_code}': 'movie_poster'},
                'streaming_options': {f'streaming_option_{country_code}': 'streaming_option'},
                'next_cursor': 'end'
            }
        mock_get_movies_and_streams_from_one_request.side_effect = side_effect_func

        # Arrange expected
        expected_db_call = call.session.query(mock_CountryService).all().call_list()
        expected_db_call.append(call.session.commit())

        expected_cursors = {'ca': 'end', 'us': 'end'}

        # Act
        seed_movies_and_streams()

        # Assert
        self.assertEqual(mock_db.mock_calls, expected_db_call)
        mock_CountryService.convert_list_to_dict.assert_called_once_with(self.mock_countries_services_objs)
        mock_read_json_file_helper.assert_called_once()
        mock_get_movies_and_streams_from_one_request.assert_has_calls(
            [call('ca', self.countries_services_dict['ca'], None),
             call('us', self.countries_services_dict['us'], None)]
        )
        mock_write_json_file_helper.assert_called_with(ANY, expected_cursors)

        num_countries = len(self.countries_services_dict)
        mock_Movie.upsert_database.assert_called_once_with(['movie' for i in range(num_countries)])
        mock_MoviePoster.upsert_database.assert_called_once_with(['movie_poster' for i in range(num_countries)])
        mock_StreamingOption.insert_database.assert_called_once_with(['streaming_option' for i in range(num_countries)])

    def test_seeding_when_cursors_has_saved_cursor(
            self,
            mock_db,
            mock_CountryService,
            mock_read_json_file_helper,
            mock_get_movies_and_streams_from_one_request,
            mock_write_json_file_helper,
            mock_Movie,
            mock_MoviePoster,
            mock_StreamingOption):
        """Tests seeding when a cursor exists from a previous seeding."""

        # Arrange mocks
        mock_db.session.query.return_value.all.return_value = self.mock_countries_services_objs

        mock_CountryService.convert_list_to_dict.return_value = deepcopy(self.countries_services_dict)

        mock_read_json_file_helper.return_value = {
            'ca': 'next ca movie', 'us': 'next us movie'}

        # using strings in place of dictionaries in the lists should still work, since only the object matters
        def side_effect_func(country_code, service_ids, cursor):
            return {
                'movies': {f'movie_{country_code}': 'movie'},
                'movie_posters': {f'movie_poster_{country_code}': 'movie_poster'},
                'streaming_options': {f'streaming_option_{country_code}': 'streaming_option'},
                'next_cursor': 'end'
            }
        mock_get_movies_and_streams_from_one_request.side_effect = side_effect_func

        # Arrange expected
        expected_db_call = call.session.query(mock_CountryService).all().call_list()
        expected_db_call.append(call.session.commit())

        expected_cursors = {'ca': 'end', 'us': 'end'}

        # Act
        seed_movies_and_streams()

        # Assert
        self.assertEqual(mock_db.mock_calls, expected_db_call)
        mock_CountryService.convert_list_to_dict.assert_called_once_with(self.mock_countries_services_objs)
        mock_read_json_file_helper.assert_called_once()
        mock_get_movies_and_streams_from_one_request.assert_has_calls(
            [call('ca', self.countries_services_dict['ca'], 'next ca movie'),
             call('us', self.countries_services_dict['us'], 'next us movie')]
        )
        mock_write_json_file_helper.assert_called_with(ANY, expected_cursors)

        num_countries = len(self.countries_services_dict)
        mock_Movie.upsert_database.assert_called_once_with(['movie' for i in range(num_countries)])
        mock_MoviePoster.upsert_database.assert_called_once_with(['movie_poster' for i in range(num_countries)])
        mock_StreamingOption.insert_database.assert_called_once_with(['streaming_option' for i in range(num_countries)])

    def test_seeding_when_cursors_has_end_cursor(
            self,
            mock_db,
            mock_CountryService,
            mock_read_json_file_helper,
            mock_get_movies_and_streams_from_one_request,
            mock_write_json_file_helper,
            mock_Movie,
            mock_MoviePoster,
            mock_StreamingOption):
        """Tests seeding when it has already been finished completing before."""

        # Arrange mocks
        mock_db.session.query.return_value.all.return_value = self.mock_countries_services_objs

        mock_CountryService.convert_list_to_dict.return_value = deepcopy(self.countries_services_dict)

        mock_read_json_file_helper.return_value = {'ca': 'end', 'us': 'end'}

        # Arrange expected
        expected_db_call = call.session.query(mock_CountryService).all().call_list()
        expected_db_call.append(call.session.commit())

        # Act
        seed_movies_and_streams()

        # Assert
        self.assertEqual(mock_db.mock_calls, expected_db_call)
        mock_CountryService.convert_list_to_dict.assert_called_once_with(self.mock_countries_services_objs)
        mock_read_json_file_helper.assert_called_once()
        mock_get_movies_and_streams_from_one_request.assert_not_called()
        mock_write_json_file_helper.assert_not_called()

        mock_Movie.upsert_database.assert_called_once_with([])
        mock_MoviePoster.upsert_database.assert_called_once_with([])
        mock_StreamingOption.insert_database.assert_called_once_with([])

    def test_seeding_when_response_gives_next_cursor(
            self,
            mock_db,
            mock_CountryService,
            mock_read_json_file_helper,
            mock_get_movies_and_streams_from_one_request,
            mock_write_json_file_helper,
            mock_Movie,
            mock_MoviePoster,
            mock_StreamingOption):
        """
        Tests seeding when the API response indicates that there is more data to retrieve.  This also shows that
        there are no more calls to Streaming Availability API when the end of a page of movies is reached.
        """

        # Arrange mocks
        mock_db.session.query.return_value.all.return_value = self.mock_countries_services_objs

        mock_CountryService.convert_list_to_dict.return_value = deepcopy(self.countries_services_dict)

        mock_read_json_file_helper.return_value = {}

        # using strings in place of dictionaries in the lists should still work, since only the object matters
        def side_effect_func(country_code, service_ids, cursor):
            if country_code == 'ca':
                if cursor is None:
                    return {
                        'movies': {f'movie_{country_code}_1': 'movie'},
                        'movie_posters': {f'movie_poster_{country_code}_1': 'movie_poster'},
                        'streaming_options': {f'streaming_option_{country_code}_1': 'streaming_option'},
                        'next_cursor': '29583:A Dark Truth'
                    }
                elif cursor == '29583:A Dark Truth':
                    return {
                        'movies': {f'movie_{country_code}_2': 'movie'},
                        'movie_posters': {f'movie_poster_{country_code}_2': 'movie_poster'},
                        'streaming_options': {f'streaming_option_{country_code}_2': 'streaming_option'},
                        'next_cursor': 'end'
                    }
            if country_code == 'us':
                if cursor is None:
                    return {
                        'movies': {f'movie_{country_code}_3': 'movie'},
                        'movie_posters': {f'movie_poster_{country_code}_3': 'movie_poster'},
                        'streaming_options': {f'streaming_option_{country_code}_3': 'streaming_option'},
                        'next_cursor': '210942:A Deeper Shade of Blue'
                    }
                elif cursor == '210942:A Deeper Shade of Blue':
                    return {
                        'movies': {f'movie_{country_code}_4': 'movie'},
                        'movie_posters': {f'movie_poster_{country_code}_4': 'movie_poster'},
                        'streaming_options': {f'streaming_option_{country_code}_4': 'streaming_option'},
                        'next_cursor': 'end'
                    }
        mock_get_movies_and_streams_from_one_request.side_effect = side_effect_func

        # Arrange expected
        expected_db_call = call.session.query(mock_CountryService).all().call_list()
        expected_db_call.append(call.session.commit())

        expected_cursors = {'ca': 'end', 'us': 'end'}

        # Act
        seed_movies_and_streams()

        # Assert
        self.assertEqual(mock_db.mock_calls, expected_db_call)
        mock_CountryService.convert_list_to_dict.assert_called_once_with(self.mock_countries_services_objs)
        mock_read_json_file_helper.assert_called_once()
        mock_get_movies_and_streams_from_one_request.assert_has_calls(
            [call('ca', self.countries_services_dict['ca'], None),
             call('ca', self.countries_services_dict['ca'], '29583:A Dark Truth'),
             call('us', self.countries_services_dict['us'], None),
             call('us', self.countries_services_dict['us'], '210942:A Deeper Shade of Blue')]
        )
        mock_write_json_file_helper.assert_called_with(ANY, expected_cursors)

        mock_Movie.upsert_database.assert_called_once_with(['movie' for i in range(4)])
        mock_MoviePoster.upsert_database.assert_called_once_with(['movie_poster' for i in range(4)])
        mock_StreamingOption.insert_database.assert_called_once_with(['streaming_option' for i in range(4)])

    def test_seeding_when_response_has_an_error(
            self,
            mock_db,
            mock_CountryService,
            mock_read_json_file_helper,
            mock_get_movies_and_streams_from_one_request,
            mock_write_json_file_helper,
            mock_Movie,
            mock_MoviePoster,
            mock_StreamingOption):
        """Tests seeding when the API response does not return a status code of 200."""

        # Arrange mocks
        mock_db.session.query.return_value.all.return_value = self.mock_countries_services_objs

        mock_CountryService.convert_list_to_dict.return_value = deepcopy(self.countries_services_dict)

        mock_read_json_file_helper.return_value = {}

        mock_get_movies_and_streams_from_one_request.return_value = None

        # Arrange expected
        expected_db_call = call.session.query(mock_CountryService).all().call_list()
        expected_db_call.append(call.session.commit())

        # Act
        seed_movies_and_streams()

        # Assert
        self.assertEqual(mock_db.mock_calls, expected_db_call)
        mock_CountryService.convert_list_to_dict.assert_called_once_with(self.mock_countries_services_objs)
        mock_read_json_file_helper.assert_called_once()
        mock_get_movies_and_streams_from_one_request.assert_has_calls(
            [call('ca', self.countries_services_dict['ca'], None),
             call('us', self.countries_services_dict['us'], None)]
        )
        mock_write_json_file_helper.assert_not_called()

        mock_Movie.upsert_database.assert_called_once_with([])
        mock_MoviePoster.upsert_database.assert_called_once_with([])
        mock_StreamingOption.insert_database.assert_called_once_with([])

    def test_seeding_when_there_are_no_countryservices(
            self,
            mock_db,
            mock_CountryService,
            mock_read_json_file_helper,
            mock_get_movies_and_streams_from_one_request,
            mock_write_json_file_helper,
            mock_Movie,
            mock_MoviePoster,
            mock_StreamingOption):
        """Tests seeding when there are no streaming services stored in the database."""

        # Arrange mocks
        mock_db.session.query.return_value.all.return_value = self.mock_countries_services_objs

        mock_CountryService.convert_list_to_dict.return_value = {}

        mock_read_json_file_helper.return_value = {}

        # Arrange expected
        expected_db_call = call.session.query(mock_CountryService).all().call_list()
        expected_db_call.append(call.session.commit())

        # Act
        seed_movies_and_streams()

        # Assert
        self.assertEqual(mock_db.mock_calls, expected_db_call)
        mock_CountryService.convert_list_to_dict.assert_called_once_with(self.mock_countries_services_objs)
        mock_get_movies_and_streams_from_one_request.assert_not_called()
        mock_write_json_file_helper.assert_not_called()

        mock_Movie.upsert_database.assert_called_once_with([])
        mock_MoviePoster.upsert_database.assert_called_once_with([])
        mock_StreamingOption.insert_database.assert_called_once_with([])

    # Maybe add one more test for one country and service, for when there are 20+ pages or cursors.

# ==================================================


def mock_make_unique_transformed_show_data_side_effect(country: str, service_ids: list, show: dict) -> dict:
    return {
        'movies': {
            show['id']: {'id': show['id']}
        },
        'movie_posters': {
            f'{show['id']}-verticalPoster-w240': {'movie_id': show['id'],
                                                  'type': 'verticalPoster',
                                                  'size': 'w240',
                                                  'link': 'link' + show['id']}
        },
        'streaming_options': {
            f'{show['id']}-{country}-{service_ids[0]}-{'link' + show['id']}': {'movie_id': show['id'],
                                                                               'country_code': country,
                                                                               'service_id': service_ids[0],
                                                                               'link': 'link' + show['id']}
        }
    }
