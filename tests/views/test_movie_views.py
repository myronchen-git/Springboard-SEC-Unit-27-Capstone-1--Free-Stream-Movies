import sys
from os.path import abspath, dirname, join

# Adds root folder as a working directory.
# This is needed so that imports can be found.
root_dir = abspath(join(dirname(__file__), '../../'))  # nopep8
sys.path.append(root_dir)  # nopep8

# --------------------------------------------------

from types import MappingProxyType
from unittest import TestCase
from unittest.mock import ANY, MagicMock, patch
from urllib import parse

from flask import url_for

from src.app import (COOKIE_COUNTRY_CODE_NAME, STREAMING_AVAILABILITY_BASE_URL,
                     create_app)
from src.models.common import connect_db, db
from src.models.movie import Movie
from src.models.movie_poster import MoviePoster
from src.models.service import Service
from src.models.streaming_option import StreamingOption
from tests.data import show_stargate
from tests.utilities import (movie_generator, movie_poster_generator,
                             service_generator, streaming_option_generator)

# ==================================================

app = create_app("freestreammovies_test", testing=True)
app.config.update(
    WTF_CSRF_ENABLED=False,
    SERVER_NAME="localhost:5000"
)

connect_db(app)
app.app_context().push()

db.drop_all()
db.create_all()

# --------------------------------------------------


@patch('src.app.requests', autospec=True)
class MovieSearchViewIntegrationTests(TestCase):
    """Integration tests for views involving movie searches.  This mocks calls to external API."""

    def test_search_title(self, mock_requests):
        """Tests for successfully searching for a movie title and displaying results."""

        # Arrange
        url = url_for("search_titles")
        country_code = 'us'
        title = "Stargate"
        query_string = {"title": title}

        mock_response = MagicMock(name='mock_response')
        mock_response.status_code = 200
        mock_response.json.return_value = [MappingProxyType(show_stargate)]
        mock_requests.get.return_value = mock_response

        expected_movie_poster_link_path = parse.urlparse(show_stargate['imageSet']['verticalPoster']['w240']).path

        # Act
        with app.test_client() as client:
            client.set_cookie(COOKIE_COUNTRY_CODE_NAME, country_code)
            resp = client.get(url, query_string=query_string)
            html = resp.get_data(as_text=True)

        # Assert
            self.assertEqual(resp.status_code, 200)
            self.assertIn("Search Results", html)
            self.assertIn(title, html)
            self.assertIn(expected_movie_poster_link_path, html)

            mock_requests.get.assert_called_once()

    def test_search_title_with_no_results(self, mock_requests):
        """Tests for successfully searching for a movie title that doesn't exist."""

        # Arrange
        url = url_for("search_titles")
        country_code = 'us'
        query_string = {"title": "plpmnb"}

        mock_response = MagicMock(name='mock_response')
        mock_response.status_code = 200
        mock_response.json.return_value = []
        mock_requests.get.return_value = mock_response

        # Act
        with app.test_client() as client:
            client.set_cookie(COOKIE_COUNTRY_CODE_NAME, country_code)
            resp = client.get(url, query_string=query_string)
            html = resp.get_data(as_text=True)

        # Assert
            self.assertEqual(resp.status_code, 200)
            self.assertIn("Search Results", html)
            self.assertIn("No results found.", html)

            mock_requests.get.assert_called_once()

    def test_search_title_with_missing_required_parameter(self, mock_requests):
        """Doing a title search without movie title should redirect to the homepage."""

        # Arrange
        url = url_for("search_titles")
        country_code = 'us'

        # Act
        with app.test_client() as client:
            client.set_cookie(COOKIE_COUNTRY_CODE_NAME, country_code)
            resp = client.get(url)

        # Assert
            self.assertEqual(resp.status_code, 302)
            self.assertEqual(resp.location, url_for("home"))

            mock_requests.assert_not_called()

    def test_search_title_with_ext_api_return_not_200(self, mock_requests):
        """When the external API returns a status that is not 200, an error should be displayed in the HTML. """

        # Arrange
        url = url_for("search_titles")
        country_code = 'us'
        title = "Stargate"
        query_string = {"title": title}

        status_code = 404
        reason = "Not Found"

        mock_response = MagicMock(name='mock_response')
        mock_response.status_code = status_code
        mock_response.reason = reason
        mock_requests.get.return_value = mock_response

        expected_api_url = f"{STREAMING_AVAILABILITY_BASE_URL}/shows/search/title"
        expected_api_params = {"country": country_code,
                               "title": title,
                               "show_type": "movie"}

        # Act
        with app.test_client() as client:
            client.set_cookie(COOKIE_COUNTRY_CODE_NAME, country_code)
            resp = client.get(url, query_string=query_string)
            html = resp.get_data(as_text=True)

        # Assert
            self.assertEqual(resp.status_code, status_code)
            self.assertIn(str(status_code), html)
            self.assertIn(reason, html)

            mock_requests.get.assert_called_once_with(expected_api_url, headers=ANY, params=expected_api_params)


@patch('src.app.requests', autospec=True)
class MovieDetailsViewIntegrationTests(TestCase):
    """Integration tests for the view of a movie's details page.  This mocks calls to external API."""

    def setUp(self):
        db.session.query(StreamingOption).delete()
        db.session.query(Service).delete()
        db.session.query(Movie).delete()
        db.session.query(MoviePoster).delete()
        db.session.commit()

    def tearDown(self):
        db.session.rollback()

    def test_movie_details_page_with_data_in_local_database(self, mock_requests):
        """Tests that a movie's details page is loaded with existing data from the local database."""

        # Arrange
        country_code = 'us'

        service = service_generator(1)[0]
        movie = movie_generator(1)[0]
        streaming_option = streaming_option_generator(1, movie.id, country_code, service.id)[0]
        movie_posters = movie_poster_generator([movie.id])

        db.session.add_all([service, movie, streaming_option, *movie_posters])
        db.session.commit()

        url = url_for('movie_details_page', movie_id=movie.id)

        # Act
        with app.test_client() as client:
            client.set_cookie(COOKIE_COUNTRY_CODE_NAME, country_code)
            resp = client.get(url, follow_redirects=True)
            html = resp.get_data(as_text=True)

        # Assert
            self.assertEqual(resp.status_code, 200)
            self.assertIn(movie.title, html)
            self.assertIn(streaming_option.link, html)
            self.assertIn(service.light_theme_image, html)
            self.assertIn(f'www.example.com/{movie.id}/verticalPoster/w360', html)  # movie poster link
            self.assertIn(f'alt="{movie.title} Poster"', html)

            mock_requests.assert_not_called()

    def test_movie_details_page_with_only_movie_data_in_local_database(self, mock_requests):
        """Tests that a movie's details page is loaded from the local database, but there are no streaming options."""

        # Arrange
        country_code = 'us'

        movie = movie_generator(1)[0]
        movie_posters = movie_poster_generator([movie.id])

        db.session.add_all([movie, *movie_posters])
        db.session.commit()

        url = url_for('movie_details_page', movie_id=movie.id)

        # Act
        with app.test_client() as client:
            client.set_cookie(COOKIE_COUNTRY_CODE_NAME, country_code)
            resp = client.get(url, follow_redirects=True)
            html = resp.get_data(as_text=True)

        # Assert
            self.assertEqual(resp.status_code, 200)
            self.assertIn(movie.title, html)
            self.assertIn('Not Free', html)
            self.assertIn(f'www.example.com/{movie.id}/verticalPoster/w360', html)  # movie poster link
            self.assertIn(f'alt="{movie.title} Poster"', html)

            mock_requests.assert_not_called()

    def test_movie_details_page_without_movie_data_in_local_database(self, mock_requests):
        """
        Tests that a movie's details page is loaded from the external API if it doesn't exist in the local database.

        !WARNING!
        Values used in here are contemporary.  They are retrieved from an external source and may change in the future.
        """

        # Arrange
        country_code = 'us'
        movie_id = '2332'  # Stargate
        url = url_for('movie_details_page', movie_id=movie_id)

        pluto = Service(
            id='plutotv',
            name='Pluto TV',
            home_page='https://pluto.tv/',
            theme_color_code='#fff200',
            light_theme_image='https://media.movieofthenight.com/services/plutotv/logo-light-theme.svg',
            dark_theme_image='https://media.movieofthenight.com/services/plutotv/logo-dark-theme.svg',
            white_image='https://media.movieofthenight.com/services/plutotv/logo-white.svg'
        )

        tubi = Service(
            id='tubi',
            name='Tubi',
            home_page='https://tubitv.com/',
            theme_color_code='#ffff13',
            light_theme_image='https://media.movieofthenight.com/services/tubi/logo-light-theme.svg',
            dark_theme_image='https://media.movieofthenight.com/services/tubi/logo-dark-theme.svg',
            white_image='https://media.movieofthenight.com/services/tubi/logo-white.svg'
        )

        db.session.add_all([pluto, tubi])
        db.session.commit()

        mock_response = MagicMock(name='mock_response')
        mock_response.status_code = 200
        mock_response.json.return_value = MappingProxyType(show_stargate)
        mock_requests.get.return_value = mock_response

        expected_movie_poster_link_path = parse.urlparse(show_stargate['imageSet']['verticalPoster']['w360']).path

        # Act
        with app.test_client() as client:
            client.set_cookie(COOKIE_COUNTRY_CODE_NAME, country_code)
            resp = client.get(url, follow_redirects=True)
            html = resp.get_data(as_text=True)

        # Assert
            self.assertEqual(resp.status_code, 200)
            self.assertIn(show_stargate['title'], html)
            self.assertIn(show_stargate['streamingOptions']['us'][1]['link'], html)
            self.assertIn(show_stargate['streamingOptions']['us'][2]['link'], html)

            self.assertIn(expected_movie_poster_link_path, html)
            self.assertIn(f'alt="{show_stargate['title']} Poster"', html)

            mock_requests.get.assert_called_once()

    def test_movie_details_page_for_nonexistent_movie(self, mock_requests):
        """Tests displaying an error in the HTML if a movie ID does not belong to a movie."""

        # Arrange
        country_code = 'us'
        movie_id = '0'
        url = url_for('movie_details_page', movie_id=movie_id)

        status_code = 404
        reason = "Not Found"

        mock_response = MagicMock(name='mock_response')
        mock_response.status_code = status_code
        mock_response.reason = reason
        mock_requests.get.return_value = mock_response

        expected_api_url = f"{STREAMING_AVAILABILITY_BASE_URL}/shows/{movie_id}"

        # Act
        with app.test_client() as client:
            client.set_cookie(COOKIE_COUNTRY_CODE_NAME, country_code)
            resp = client.get(url, follow_redirects=True)
            html = resp.get_data(as_text=True)

        # Assert
            self.assertEqual(resp.status_code, status_code)
            self.assertIn(str(status_code), html)
            self.assertIn(reason, html)

            mock_requests.get.assert_called_once_with(expected_api_url, headers=ANY)
