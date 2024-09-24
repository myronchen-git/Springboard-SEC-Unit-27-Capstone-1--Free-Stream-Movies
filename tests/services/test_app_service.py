import sys
from os.path import abspath, dirname, join

# Adds root folder as a working directory.
# This is needed so that imports can be found.
root_dir = abspath(join(dirname(__file__), '../../'))  # nopep8
sys.path.append(root_dir)  # nopep8

# --------------------------------------------------

from copy import deepcopy
from unittest import TestCase
from unittest.mock import MagicMock, patch

from src.app import create_app
from src.exceptions.StreamingAvailabilityApiError import \
    StreamingAvailabilityApiError
from src.exceptions.UpsertError import UpsertError
from src.models.common import connect_db, db
from src.services.app_service import AppService

# ==================================================

app = create_app("freestreammovies_test", testing=True)
connect_db(app)
app.app_context().push()

db.drop_all()
db.create_all()

# --------------------------------------------------


@patch('src.services.app_service.requests', autospec=True)
@patch('src.services.app_service.RAPID_API_KEY')
class AppServiceSearchMoviesByTitleUnitTests(TestCase):
    """Unit tests for AppService.search_movies_by_title()."""

    def setUp(self):
        # Arrange
        self.country_code = 'us'
        self.title = 'batman'

        self.app_service = AppService()
        self.url = f'{self.app_service.STREAMING_AVAILABILITY_BASE_URL}/shows/search/title'

        # Arrange expected
        self.expected_query_string = {'country': self.country_code,
                                      'title': self.title,
                                      'show_type': 'movie'}

    def test_search_for_a_movie(
            self,
            mock_RAPID_API_KEY,
            mock_requests
    ):
        """Searching for a movie returns a list of movies in JSON format."""

        # Arrange
        movies = [
            {'id': '1', 'title': 'batman1'},
            {'id': '2', 'title': 'batman2'}
        ]

        # Arrange mocks
        mock_response = MagicMock(name='mock_response')
        mock_response.status_code = 200
        mock_response.json.return_value = deepcopy(movies)
        mock_requests.get.return_value = mock_response

        # Arrange expected
        expected_headers = {'X-RapidAPI-Key': mock_RAPID_API_KEY}

        # Act
        result = self.app_service.search_movies_by_title(self.country_code, self.title)

        # Assert
        self.assertEqual(result, movies)
        mock_requests.get.assert_called_once_with(
            self.url,
            headers=expected_headers,
            params=self.expected_query_string
        )

    def test_status_code_not_200(
            self,
            mock_RAPID_API_KEY,
            mock_requests
    ):
        """Receiving a response status code that is not 200 should throw an exception."""

        # Arrange mocks
        mock_response = MagicMock(name='mock_response')
        mock_response.status_code = 500
        mock_requests.get.return_value = mock_response

        # Arrange expected
        expected_headers = {'X-RapidAPI-Key': mock_RAPID_API_KEY}

        # Act/Assert
        self.assertRaises(
            StreamingAvailabilityApiError,
            self.app_service.search_movies_by_title,
            self.country_code,
            self.title
        )
        mock_requests.get.assert_called_once_with(
            self.url,
            headers=expected_headers,
            params=self.expected_query_string
        )


@patch('src.services.app_service.convert_show_json_into_movie_object', autospec=True)
@patch('src.services.app_service.db', autospec=True)
@patch('src.services.app_service.StreamingOption', autospec=True)
@patch('src.services.app_service.MoviePoster', autospec=True)
@patch('src.services.app_service.Movie', autospec=True)
@patch('src.services.app_service.transform_show', autospec=True)
@patch('src.services.app_service.requests', autospec=True)
@patch('src.services.app_service.RAPID_API_KEY')
class AppServiceGetMovieDataUnitTests(TestCase):
    """Unit tests for AppService.get_movie_data()."""

    def setUp(self):
        self.movie_id = "123"

        self.app_service = AppService()
        self.url = f'{self.app_service.STREAMING_AVAILABILITY_BASE_URL}/shows/{self.movie_id}'

        self.returned_show_json = {'id': '1', 'title': 'movie1'}

    def test_gets_movie_data(
            self,
            mock_RAPID_API_KEY,
            mock_requests,
            mock_transform_show,
            mock_Movie,
            mock_MoviePoster,
            mock_StreamingOption,
            mock_db,
            mock_convert_show_json_into_movie_object
    ):
        """Retrieves movie data from Streaming Availability API and returns a Movie object."""

        # Arrange mocks
        mock_response = MagicMock(name='mock_response')
        mock_response.status_code = 200
        mock_response.json.return_value = deepcopy(self.returned_show_json)
        mock_requests.get.return_value = mock_response

        mock_movies = MagicMock(name='mock_movies')
        mock_movie_posters = MagicMock(name='mock_movie_posters')
        mock_streaming_options = MagicMock(name='mock_streaming_options')
        mock_transform_show.return_value = {
            'movies': mock_movies,
            'movie_posters': mock_movie_posters,
            'streaming_options': mock_streaming_options
        }

        mock_movie_object = MagicMock(name='mock_movie_object')
        mock_convert_show_json_into_movie_object.return_value = mock_movie_object

        # Arrange expected
        expected_headers = {'X-RapidAPI-Key': mock_RAPID_API_KEY}

        # Act
        result = self.app_service.get_movie_data(self.movie_id)

        # Assert
        self.assertIs(result, mock_movie_object)

        mock_requests.get.assert_called_once_with(
            self.url,
            headers=expected_headers
        )

        mock_transform_show.assert_called_once_with(self.returned_show_json)
        mock_Movie.upsert_database.assert_called_once_with(mock_movies)
        mock_MoviePoster.upsert_database.assert_called_once_with(mock_movie_posters)
        mock_StreamingOption.insert_database.assert_called_once_with(mock_streaming_options)

        mock_db.session.commit.assert_called_once()

        mock_convert_show_json_into_movie_object.assert_called_once_with(self.returned_show_json)

    def test_status_code_not_200(
            self,
            mock_RAPID_API_KEY,
            mock_requests,
            mock_transform_show,
            mock_Movie,
            mock_MoviePoster,
            mock_StreamingOption,
            mock_db,
            mock_convert_show_json_into_movie_object
    ):
        """Receiving a response status code that is not 200 should throw an exception."""

        # Arrange mocks
        mock_response = MagicMock(name='mock_response')
        mock_response.status_code = 400
        mock_requests.get.return_value = mock_response

        # Arrange expected
        expected_headers = {'X-RapidAPI-Key': mock_RAPID_API_KEY}

        # Act/Assert
        self.assertRaises(
            StreamingAvailabilityApiError,
            self.app_service.get_movie_data,
            self.movie_id
        )
        mock_requests.get.assert_called_once_with(
            self.url,
            headers=expected_headers
        )

        mock_transform_show.assert_not_called()
        mock_Movie.assert_not_called()
        mock_MoviePoster.assert_not_called()
        mock_StreamingOption.assert_not_called()
        mock_db.assert_not_called()
        mock_convert_show_json_into_movie_object.assert_not_called()

    def test_database_commit_fail(
            self,
            mock_RAPID_API_KEY,
            mock_requests,
            mock_transform_show,
            mock_Movie,
            mock_MoviePoster,
            mock_StreamingOption,
            mock_db,
            mock_convert_show_json_into_movie_object
    ):
        """If committing the SQLAlchemy session throws an exception, then an exception should be thrown."""

        # Arrange mocks
        mock_response = MagicMock(name='mock_response')
        mock_response.status_code = 200
        mock_response.json.return_value = deepcopy(self.returned_show_json)
        mock_requests.get.return_value = mock_response

        mock_movies = MagicMock(name='mock_movies')
        mock_movie_posters = MagicMock(name='mock_movie_posters')
        mock_streaming_options = MagicMock(name='mock_streaming_options')
        mock_transform_show.return_value = {
            'movies': mock_movies,
            'movie_posters': mock_movie_posters,
            'streaming_options': mock_streaming_options
        }

        mock_db.session.commit.side_effect = UpsertError("")

        # Arrange expected
        expected_headers = {'X-RapidAPI-Key': mock_RAPID_API_KEY}

        # Act/Assert
        self.assertRaises(
            UpsertError,
            self.app_service.get_movie_data,
            self.movie_id
        )

        mock_requests.get.assert_called_once_with(
            self.url,
            headers=expected_headers
        )

        mock_transform_show.assert_called_once_with(self.returned_show_json)
        mock_Movie.upsert_database.assert_called_once_with(mock_movies)
        mock_MoviePoster.upsert_database.assert_called_once_with(mock_movie_posters)
        mock_StreamingOption.insert_database.assert_called_once_with(mock_streaming_options)

        mock_convert_show_json_into_movie_object.assert_not_called()
