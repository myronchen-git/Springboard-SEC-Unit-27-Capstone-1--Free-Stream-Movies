import sys
from os.path import abspath, dirname, join

# Adds root folder as a working directory.
# This is needed so that imports can be found.
root_dir = abspath(join(dirname(__file__), '../../'))  # nopep8
sys.path.append(root_dir)  # nopep8

# --------------------------------------------------

from unittest import TestCase
from unittest.mock import call, patch

from src.app import create_app
from src.exceptions.UnrecognizedValueError import UnrecognizedValueError
from src.models.common import connect_db, db
from src.models.movie import Movie
from src.models.movie_poster import MoviePoster
from tests.utility_functions import movie_generator, movie_poster_generator

# ==================================================

app = create_app("freestreammovies_test", testing=True)
connect_db(app)
app.app_context().push()

db.drop_all()
db.create_all()

# --------------------------------------------------


class MoviePosterUnitTestsGetMoviePosters(TestCase):
    """Unit tests for MoviePoster.get_movie_posters()."""

    def tearDown(self):
        db.session.rollback()

    @patch('src.models.movie_poster.MoviePoster.size', autospec=True)
    @patch('src.models.movie_poster.MoviePoster.type', autospec=True)
    @patch('src.models.movie_poster.MoviePoster.movie_id', autospec=True)
    @patch('src.models.movie_poster.db', autospec=True)
    def test_successful_query_and_data_return(
        self,
        mock_db,
        mock_movie_poster_movie_id,
        mock_movie_poster_type,
        mock_movie_poster_size
    ):
        """Tests that a list of MoviePosters is returned when given valid arguments."""

        # Arrange
        movie_ids = ('123',)
        types = ('verticalPoster',)
        sizes = ('w240',)

        movie_posters = movie_poster_generator(movie_ids)

        mock_db.session.query.return_value.filter.return_value.all.return_value = movie_posters

        expected_call = call.session.query(MoviePoster).filter(
            mock_movie_poster_movie_id.in_(movie_ids),
            mock_movie_poster_type.in_(types),
            mock_movie_poster_size.in_(sizes)
        ).all().call_list()

        # Act
        result = MoviePoster.get_movie_posters(movie_ids, types, sizes)

        # Assert
        self.assertEqual(result, movie_posters)

        self.assertEqual(mock_db.mock_calls, expected_call)
        mock_movie_poster_movie_id.in_.assert_called_with(movie_ids)
        mock_movie_poster_type.in_.assert_called_with(types)
        mock_movie_poster_size.in_.assert_called_with(sizes)

    @patch('src.models.movie_poster.db', autospec=True)
    def test_invalid_argument_for_type(self, mock_db):
        """Passing an invalid type for an argument should throw an exception."""

        # Arrange
        movie_ids = ('123',)
        types = ('verticalPoster', 'diagonalPoster')
        sizes = ('w240',)

        # Act / Assert
        self.assertRaises(UnrecognizedValueError, MoviePoster.get_movie_posters, *(movie_ids, types, sizes))
        mock_db.assert_not_called()

    @patch('src.models.movie_poster.db', autospec=True)
    def test_invalid_argument_for_size(self, mock_db):
        """Passing an invalid size for an argument should throw an exception."""

        # Arrange
        movie_ids = ('123',)
        types = ('verticalPoster')
        sizes = ('w240', 'w9999')

        # Act / Assert
        self.assertRaises(UnrecognizedValueError, MoviePoster.get_movie_posters, *(movie_ids, types, sizes))
        mock_db.assert_not_called()


class MoviePosterUnitTestsConvertListToDict(TestCase):
    """Unit tests for MoviePoster.convert_list_to_dict()."""

    def test_convert_movie_posters_list_to_dict(self):
        """Passing in a list[MoviePoster] should return a dictionary."""

        # Arrange
        movie_posters = [
            MoviePoster(
                movie_id='1',
                type='verticalPoster',
                size='w240',
                link='www.example.com/image/1/w240'
            ),
            MoviePoster(
                movie_id='1',
                type='verticalPoster',
                size='w360',
                link='www.example.com/image/1/w360'
            ),
            MoviePoster(
                movie_id='2',
                type='verticalPoster',
                size='w240',
                link='www.example.com/image/2/w240'
            ),
        ]

        expected_result = {
            '1': {
                'verticalPoster': {
                    'w240': 'www.example.com/image/1/w240',
                    'w360': 'www.example.com/image/1/w360'
                }
            },
            '2': {
                'verticalPoster': {
                    'w240': 'www.example.com/image/2/w240',
                }
            }
        }

        # Act
        result = MoviePoster.convert_list_to_dict(movie_posters)

        # Assert
        self.assertEqual(result, expected_result)

    def test_convert_empty_movie_posters_list_to_empty_dict(self):
        """Passing an empty list should return an empty dictionary."""

        # Arrange
        movie_posters = []

        # Act
        result = MoviePoster.convert_list_to_dict(movie_posters)

        # Assert
        self.assertEqual(result, {})


class MoviePosterIntegrationTestsGetMoviePosters(TestCase):
    """Integration tests for MoviePoster.get_movie_posters()."""

    def setUp(self):
        db.session.query(MoviePoster).delete()
        db.session.query(Movie).delete()
        db.session.commit()

        movies = movie_generator(2)
        db.session.add_all(movies)

        movie_posters = tuple(movie_poster_generator(('0', '1')))
        db.session.add_all(movie_posters)
        db.session.commit()

    def tearDown(self):
        db.session.rollback()

    def test_get_no_movie_posters(self):
        """Tests that no movie posters are retrieved when there aren't any for a movie."""

        # Arrange
        movie_ids = ('3',)
        types = ('verticalPoster',)
        sizes = ('w240',)

        # Act
        result = MoviePoster.get_movie_posters(movie_ids, types, sizes)

        # Assert
        self.assertEqual(len(result), 0)

    def test_get_one_movie_poster(self):
        """Tests that one movie poster is retrieved for a specific movie ID, type, and size."""

        # Arrange
        movie_ids = ('0',)
        types = ('verticalPoster',)
        sizes = ('w240',)

        # Act
        result = MoviePoster.get_movie_posters(movie_ids, types, sizes)

        # Assert
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].movie_id, movie_ids[0])
        self.assertEqual(result[0].type, types[0])
        self.assertEqual(result[0].size, sizes[0])

    def test_get_many_movie_posters(self):
        """Tests that multiple movie posters are retrieved when given multiple movie IDs, types, or sizes."""

        # Arrange
        movie_ids = ('0', '1')
        types = ('verticalPoster',)
        sizes = ('w240', 'w720')

        # Act
        result = MoviePoster.get_movie_posters(movie_ids, types, sizes)

        # Assert
        self.assertEqual(len(result), len(movie_ids) * len(types) * len(sizes))

        result_movie_ids = {movie_poster.movie_id for movie_poster in result}
        for movie_id in movie_ids:
            self.assertIn(movie_id, result_movie_ids)

        result_types = {movie_poster.type for movie_poster in result}
        for type in types:
            self.assertIn(type, result_types)

        result_sizes = {movie_poster.size for movie_poster in result}
        for size in sizes:
            self.assertIn(size, result_sizes)