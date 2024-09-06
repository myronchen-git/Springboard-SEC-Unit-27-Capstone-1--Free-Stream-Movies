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
from src.seed.streaming_availability_seeder import seed_movies_and_streams

# ==================================================

app = create_app("freestreammovies_test", testing=True)
connect_db(app)
app.app_context().push()

db.drop_all()
db.create_all()

# --------------------------------------------------


@patch('src.seed.streaming_availability_seeder.write_json_file_helper', autospec=True)
@patch('src.seed.streaming_availability_seeder.seed_movies_and_streams_from_one_request', autospec=True)
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
            mock_seed_movies_and_streams_from_one_request,
            mock_write_json_file_helper):
        """Tests seeding when there has not been seeding before."""

        # Arrange
        mock_db.session.query.return_value.all.return_value = self.mock_countries_services_objs
        expected_db_call = call.session.query(mock_CountryService).all().call_list()

        mock_CountryService.convert_list_to_dict.return_value = deepcopy(self.countries_services_dict)

        mock_read_json_file_helper.return_value = {}
        mock_seed_movies_and_streams_from_one_request.return_value = 'end'

        expected_cursors = {'ca': 'end', 'us': 'end'}

        # Act
        seed_movies_and_streams()

        # Assert
        self.assertEqual(mock_db.mock_calls, expected_db_call)
        mock_CountryService.convert_list_to_dict.assert_called_once_with(self.mock_countries_services_objs)
        mock_read_json_file_helper.assert_called_once()
        mock_seed_movies_and_streams_from_one_request.assert_has_calls(
            [call('ca', self.countries_services_dict['ca'], None),
             call('us', self.countries_services_dict['us'], None)]
        )
        mock_write_json_file_helper.assert_called_with(ANY, expected_cursors)

    def test_seeding_when_cursors_has_saved_cursor(
            self,
            mock_db,
            mock_CountryService,
            mock_read_json_file_helper,
            mock_seed_movies_and_streams_from_one_request,
            mock_write_json_file_helper):
        """Tests seeding when a cursor exists from a previous seeding."""

        # Arrange
        mock_db.session.query.return_value.all.return_value = self.mock_countries_services_objs
        expected_db_call = call.session.query(mock_CountryService).all().call_list()

        mock_CountryService.convert_list_to_dict.return_value = deepcopy(self.countries_services_dict)

        mock_read_json_file_helper.return_value = {
            'ca': 'next ca movie', 'us': 'next us movie'}
        mock_seed_movies_and_streams_from_one_request.return_value = 'end'

        expected_cursors = {'ca': 'end', 'us': 'end'}

        # Act
        seed_movies_and_streams()

        # Assert
        self.assertEqual(mock_db.mock_calls, expected_db_call)
        mock_CountryService.convert_list_to_dict.assert_called_once_with(self.mock_countries_services_objs)
        mock_read_json_file_helper.assert_called_once()
        mock_seed_movies_and_streams_from_one_request.assert_has_calls(
            [call('ca', self.countries_services_dict['ca'], 'next ca movie'),
             call('us', self.countries_services_dict['us'], 'next us movie')]
        )
        mock_write_json_file_helper.assert_called_with(ANY, expected_cursors)

    def test_seeding_when_cursors_has_end_cursor(
            self,
            mock_db,
            mock_CountryService,
            mock_read_json_file_helper,
            mock_seed_movies_and_streams_from_one_request,
            mock_write_json_file_helper):
        """Tests seeding when it has already been finished completing before."""

        # Arrange
        mock_db.session.query.return_value.all.return_value = self.mock_countries_services_objs
        expected_db_call = call.session.query(mock_CountryService).all().call_list()

        mock_CountryService.convert_list_to_dict.return_value = deepcopy(self.countries_services_dict)

        mock_read_json_file_helper.return_value = {'ca': 'end', 'us': 'end'}

        # Act
        seed_movies_and_streams()

        # Assert
        self.assertEqual(mock_db.mock_calls, expected_db_call)
        mock_CountryService.convert_list_to_dict.assert_called_once_with(self.mock_countries_services_objs)
        mock_read_json_file_helper.assert_called_once()
        mock_seed_movies_and_streams_from_one_request.assert_not_called()
        mock_write_json_file_helper.assert_not_called()

    def test_seeding_when_response_gives_next_cursor(
            self,
            mock_db,
            mock_CountryService,
            mock_read_json_file_helper,
            mock_seed_movies_and_streams_from_one_request,
            mock_write_json_file_helper):
        """
        Tests seeding when the API response indicates that there is more data to retrieve.  This also shows that
        there are no more calls to Streaming Availability API when the end of a page of movies is reached.
        """

        # Arrange
        mock_db.session.query.return_value.all.return_value = self.mock_countries_services_objs
        expected_db_call = call.session.query(mock_CountryService).all().call_list()

        mock_CountryService.convert_list_to_dict.return_value = deepcopy(self.countries_services_dict)

        mock_read_json_file_helper.return_value = {}

        def side_effect_func(country_code, service_ids, cursor):
            if country_code == 'ca':
                if cursor is None:
                    return '29583:A Dark Truth'
                elif cursor == '29583:A Dark Truth':
                    return 'end'
            if country_code == 'us':
                if cursor is None:
                    return '210942:A Deeper Shade of Blue'
                elif cursor == '210942:A Deeper Shade of Blue':
                    return 'end'
        mock_seed_movies_and_streams_from_one_request.side_effect = side_effect_func

        expected_cursors = {'ca': 'end', 'us': 'end'}

        # Act
        seed_movies_and_streams()

        # Assert
        self.assertEqual(mock_db.mock_calls, expected_db_call)
        mock_CountryService.convert_list_to_dict.assert_called_once_with(self.mock_countries_services_objs)
        mock_read_json_file_helper.assert_called_once()
        mock_seed_movies_and_streams_from_one_request.assert_has_calls(
            [call('ca', self.countries_services_dict['ca'], None),
             call('ca', self.countries_services_dict['ca'], '29583:A Dark Truth'),
             call('us', self.countries_services_dict['us'], None),
             call('us', self.countries_services_dict['us'], '210942:A Deeper Shade of Blue')]
        )
        mock_write_json_file_helper.assert_called_with(ANY, expected_cursors)

    def test_seeding_when_response_has_an_error(
            self,
            mock_db,
            mock_CountryService,
            mock_read_json_file_helper,
            mock_seed_movies_and_streams_from_one_request,
            mock_write_json_file_helper):
        """Tests seeding when the API response does not return a status code of 200."""

        # Arrange
        mock_db.session.query.return_value.all.return_value = self.mock_countries_services_objs
        expected_db_call = call.session.query(mock_CountryService).all().call_list()

        mock_CountryService.convert_list_to_dict.return_value = deepcopy(self.countries_services_dict)

        mock_read_json_file_helper.return_value = {}
        mock_seed_movies_and_streams_from_one_request.return_value = None

        # Act
        seed_movies_and_streams()

        # Assert
        self.assertEqual(mock_db.mock_calls, expected_db_call)
        mock_CountryService.convert_list_to_dict.assert_called_once_with(self.mock_countries_services_objs)
        mock_read_json_file_helper.assert_called_once()
        mock_seed_movies_and_streams_from_one_request.assert_has_calls(
            [call('ca', self.countries_services_dict['ca'], None),
             call('us', self.countries_services_dict['us'], None)]
        )
        mock_write_json_file_helper.assert_not_called()

    def test_seeding_when_there_are_no_countryservices(
            self,
            mock_db,
            mock_CountryService,
            mock_read_json_file_helper,
            mock_seed_movies_and_streams_from_one_request,
            mock_write_json_file_helper):
        """Tests seeding when there are no streaming services stored in the database."""

        # Arrange
        mock_db.session.query.return_value.all.return_value = self.mock_countries_services_objs
        expected_db_call = call.session.query(mock_CountryService).all().call_list()

        mock_CountryService.convert_list_to_dict.return_value = {}

        mock_read_json_file_helper.return_value = {}

        # Act
        seed_movies_and_streams()

        # Assert
        self.assertEqual(mock_db.mock_calls, expected_db_call)
        mock_CountryService.convert_list_to_dict.assert_called_once_with(self.mock_countries_services_objs)
        mock_seed_movies_and_streams_from_one_request.assert_not_called()
        mock_write_json_file_helper.assert_not_called()

    # Maybe add one more test for one country and service, for when there are 20+ pages or cursors.
