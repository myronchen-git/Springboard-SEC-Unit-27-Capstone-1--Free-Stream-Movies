import sys
from os.path import abspath, dirname, join

# Adds root folder as a working directory.
# This is needed so that imports can be found.
root_dir = abspath(join(dirname(__file__), '../../'))  # nopep8
sys.path.append(root_dir)  # nopep8

# --------------------------------------------------

from unittest import TestCase
from unittest.mock import ANY, call, patch

from src.app import create_app
from src.models.common import connect_db, db
from src.models.country_service import CountryService
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
@patch('src.seed.streaming_availability_seeder.db', autospec=True)
class SeedMoviesAndStreamsUnitTests(TestCase):
    """Unit tests for seed_movies_and_streams()."""

    def setUp(self):
        self.countries_services = (
            CountryService(country_code='us', service_id='tubi'),
            CountryService(country_code='ca', service_id='pluto'),
        )

    def test_seeding_when_cursors_file_does_not_exist(
            self,
            mock_db,
            mock_read_json_file_helper,
            mock_seed_movies_and_streams_from_one_request,
            mock_write_json_file_helper):
        """Tests seeding when there has not been seeding before."""

        # Arrange
        # ! This needs to be changed once development is done. filter_by won't be needed. !
        mock_db.session.query.return_value.filter_by.return_value.all.return_value = self.countries_services
        # !
        expected_db_call = call.session.query(CountryService).filter_by(
            country_code=ANY, service_id=ANY
        ).all().call_list()

        mock_read_json_file_helper.return_value = {}
        mock_seed_movies_and_streams_from_one_request.return_value = 'end'

        expected_cursors = {'us': {'tubi': 'end'}, 'ca': {'pluto': 'end'}}

        # Act
        seed_movies_and_streams()

        # Assert
        self.assertEqual(mock_db.mock_calls, expected_db_call)
        mock_read_json_file_helper.assert_called_once()
        mock_seed_movies_and_streams_from_one_request.assert_has_calls(
            [call('us', 'tubi', None),
             call('ca', 'pluto', None)]
        )
        mock_write_json_file_helper.assert_called_with(ANY, expected_cursors)

    def test_seeding_when_cursors_only_contains_countries(
            self,
            mock_db,
            mock_read_json_file_helper,
            mock_seed_movies_and_streams_from_one_request,
            mock_write_json_file_helper):
        """
        Tests seeding when saved cursors only contain countries, as the case when seeding for the
        first time and there is an error with the request to the API.

        Note, this might not be relevant anymore.
        """

        # Arrange
        # ! This needs to be changed once development is done. filter_by won't be needed. !
        mock_db.session.query.return_value.filter_by.return_value.all.return_value = self.countries_services
        # !
        expected_db_call = call.session.query(CountryService).filter_by(
            country_code=ANY, service_id=ANY
        ).all().call_list()

        mock_read_json_file_helper.return_value = {'us': {}, 'ca': {}}
        mock_seed_movies_and_streams_from_one_request.return_value = 'end'

        expected_cursors = {'us': {'tubi': 'end'}, 'ca': {'pluto': 'end'}}

        # Act
        seed_movies_and_streams()

        # Assert
        self.assertEqual(mock_db.mock_calls, expected_db_call)
        mock_read_json_file_helper.assert_called_once()
        mock_seed_movies_and_streams_from_one_request.assert_has_calls(
            [call('us', 'tubi', None),
             call('ca', 'pluto', None)]
        )
        mock_write_json_file_helper.assert_called_with(ANY, expected_cursors)

    def test_seeding_when_cursors_has_saved_cursor(
            self,
            mock_db,
            mock_read_json_file_helper,
            mock_seed_movies_and_streams_from_one_request,
            mock_write_json_file_helper):
        """Tests seeding when a cursor exists from a previous seeding."""

        # Arrange
        # ! This needs to be changed once development is done. filter_by won't be needed. !
        mock_db.session.query.return_value.filter_by.return_value.all.return_value = self.countries_services
        # !
        expected_db_call = call.session.query(CountryService).filter_by(
            country_code=ANY, service_id=ANY
        ).all().call_list()

        mock_read_json_file_helper.return_value = {
            'us': {'tubi': 'next movie on tubi'}, 'ca': {'pluto': 'next movie on pluto'}}
        mock_seed_movies_and_streams_from_one_request.return_value = 'end'

        expected_cursors = {'us': {'tubi': 'end'}, 'ca': {'pluto': 'end'}}

        # Act
        seed_movies_and_streams()

        # Assert
        self.assertEqual(mock_db.mock_calls, expected_db_call)
        mock_read_json_file_helper.assert_called_once()
        mock_seed_movies_and_streams_from_one_request.assert_has_calls(
            [call('us', 'tubi', 'next movie on tubi'),
             call('ca', 'pluto', 'next movie on pluto')]
        )
        mock_write_json_file_helper.assert_called_with(ANY, expected_cursors)

    def test_seeding_when_cursors_has_end_cursor(
            self,
            mock_db,
            mock_read_json_file_helper,
            mock_seed_movies_and_streams_from_one_request,
            mock_write_json_file_helper):
        """Tests seeding when it has already been finished completing before."""

        # Arrange
        # ! This needs to be changed once development is done. filter_by won't be needed. !
        mock_db.session.query.return_value.filter_by.return_value.all.return_value = self.countries_services
        # !
        expected_db_call = call.session.query(CountryService).filter_by(
            country_code=ANY, service_id=ANY
        ).all().call_list()

        mock_read_json_file_helper.return_value = {'us': {'tubi': 'end'}, 'ca': {'pluto': 'end'}}

        # Act
        seed_movies_and_streams()

        # Assert
        self.assertEqual(mock_db.mock_calls, expected_db_call)
        mock_read_json_file_helper.assert_called_once()
        mock_seed_movies_and_streams_from_one_request.assert_not_called()
        mock_write_json_file_helper.assert_not_called()

    def test_seeding_when_response_gives_next_cursor(
            self,
            mock_db,
            mock_read_json_file_helper,
            mock_seed_movies_and_streams_from_one_request,
            mock_write_json_file_helper):
        """
        Tests seeding when the API response indicates that there is more data to retrieve.  This also shows that
        there are no more calls to Streaming Availability API when the end of a page of movies is reached.
        """

        # Arrange
        # ! This needs to be changed once development is done. filter_by won't be needed. !
        mock_db.session.query.return_value.filter_by.return_value.all.return_value = self.countries_services
        # !
        expected_db_call = call.session.query(CountryService).filter_by(
            country_code=ANY, service_id=ANY
        ).all().call_list()

        mock_read_json_file_helper.return_value = {}

        def side_effect_func(country_code, service_id, cursor):
            returns = {('us', 'tubi', None): '29583:A Dark Truth',
                       ('us', 'tubi', '29583:A Dark Truth'): 'end',
                       ('ca', 'pluto', None): '210942:A Deeper Shade of Blue',
                       ('ca', 'pluto', '210942:A Deeper Shade of Blue'): 'end'}
            return returns[(country_code, service_id, cursor)]
        mock_seed_movies_and_streams_from_one_request.side_effect = side_effect_func

        expected_cursors = {'us': {'tubi': 'end'}, 'ca': {'pluto': 'end'}}

        # Act
        seed_movies_and_streams()

        # Assert
        self.assertEqual(mock_db.mock_calls, expected_db_call)
        mock_read_json_file_helper.assert_called_once()
        mock_seed_movies_and_streams_from_one_request.assert_has_calls(
            [call('us', 'tubi', None),
             call('us', 'tubi', '29583:A Dark Truth'),
             call('ca', 'pluto', None),
             call('ca', 'pluto', '210942:A Deeper Shade of Blue')]
        )
        mock_write_json_file_helper.assert_called_with(ANY, expected_cursors)

    def test_seeding_when_response_has_an_error(
            self,
            mock_db,
            mock_read_json_file_helper,
            mock_seed_movies_and_streams_from_one_request,
            mock_write_json_file_helper):
        """Tests seeding when the API response does not return a status code of 200."""

        # Arrange
        # ! This needs to be changed once development is done. filter_by won't be needed. !
        mock_db.session.query.return_value.filter_by.return_value.all.return_value = self.countries_services
        # !
        expected_db_call = call.session.query(CountryService).filter_by(
            country_code=ANY, service_id=ANY
        ).all().call_list()

        mock_read_json_file_helper.return_value = {}
        mock_seed_movies_and_streams_from_one_request.return_value = None

        # Act
        seed_movies_and_streams()

        # Assert
        self.assertEqual(mock_db.mock_calls, expected_db_call)
        mock_read_json_file_helper.assert_called_once()
        mock_seed_movies_and_streams_from_one_request.assert_has_calls(
            [call('us', 'tubi', None),
             call('ca', 'pluto', None)]
        )
        mock_write_json_file_helper.assert_not_called()

    def test_seeding_when_there_are_no_countryservices(
            self,
            mock_db,
            mock_read_json_file_helper,
            mock_seed_movies_and_streams_from_one_request,
            mock_write_json_file_helper):
        """Tests seeding when there are no streaming services stored in the database."""

        # Arrange
        # ! This needs to be changed once development is done. filter_by won't be needed. !
        mock_db.session.query.return_value.filter_by.return_value.all.return_value = []
        # !
        expected_db_call = call.session.query(CountryService).filter_by(
            country_code=ANY, service_id=ANY
        ).all().call_list()

        mock_read_json_file_helper.return_value = {}

        # Act
        seed_movies_and_streams()

        # Assert
        self.assertEqual(mock_db.mock_calls, expected_db_call)
        mock_read_json_file_helper.assert_called_once()
        mock_seed_movies_and_streams_from_one_request.assert_not_called()
        mock_write_json_file_helper.assert_not_called()

    # Maybe add one more test for one country and service, for when there are 20+ pages or cursors.
