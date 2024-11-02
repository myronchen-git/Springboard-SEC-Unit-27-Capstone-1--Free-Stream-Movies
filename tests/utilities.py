from copy import deepcopy
from unittest.mock import MagicMock

from src.models.movie import Movie
from src.models.movie_poster import MoviePoster
from src.models.service import Service
from src.models.streaming_option import StreamingOption

# ==================================================


def service_generator(n: int) -> list[Service]:
    """
    Creates n Services, with zero-indexed naming, and returning them in a List.

    :param n: The number of streaming services to create.
    :return: A list of fake Services.
    :raise ValueError: If n is negative or over 100.
    """

    if n < 0 or n > 100:
        raise ValueError("n has to be between 0 to 100, inclusive.")

    output = []

    for i in range(n):
        output.append(
            Service(
                id=f"service{i:02d}",
                name=f"Service TV {i:02d}",
                home_page=f"www.streamingservice{i:02d}.com",
                theme_color_code="#ffff13",
                light_theme_image="https://media.movieofthenight.com/services/tubi/logo-light-theme.svg",
                dark_theme_image="https://media.movieofthenight.com/services/tubi/logo-dark-theme.svg",
                white_image="https://media.movieofthenight.com/services/tubi/logo-white.svg"
            ))

    return output


def movie_generator(n: int, rating: int = None) -> list[Movie]:
    """
    Creates n Movies, with zero-indexed naming, and returning them in a List.

    :param n: The number of movies to create.
    :param rating: The rating the movies should have.
    :return: A list of fake Movies.
    :raise ValueError: If n is negative or over 100.
    """

    if n < 0 or n > 100:
        raise ValueError("n has to be between 0 to 100, inclusive.")

    output = []

    for i in range(n):
        output.append(
            Movie(
                id=str(i),
                imdb_id=f"tt04685{i:02d}",
                tmdb_id=f"movie/1{i:02d}",
                title=f"Movie {i:02d}",
                overview="batman",
                release_year=2008,
                original_title=f"The Movie {i:02d}",
                directors=["Christopher Nolan"],
                cast=["Christian Bale", "Heath Ledger", "Michael Caine"],
                rating=rating or i,
                runtime=120
            ))

    return output


def movie_poster_generator(movie_ids: list[str]) -> list[MoviePoster]:
    """
    Creates MoviePosters from list of IDs, for all types and sizes, and returns them in a List.

    :param movie_ids: A list of movie IDs to create posters for.
    :return: A list of fake MoviePosters.
    """

    output = []

    for movie_id in movie_ids:
        for type in MoviePoster.Types:
            for size in MoviePoster.VerticalSizes:
                output.append(
                    MoviePoster(
                        movie_id=movie_id,
                        type=type,
                        size=size,
                        link=f'www.example.com/{movie_id}/{type}/{size}'
                    )
                )

    return output


def streaming_option_generator(n: int, movie_id: str, country_code: str, service_id: str) -> list[StreamingOption]:
    """
    Creates n StreamingOptions, with zero-indexed naming, and returning them in a List.

    :param n: The number of streaming options to create.
    :param movie_id: The movie ID to create streaming options for.
    :param country_code: The country code to create streaming options for.
    :param service_id: The service ID to create streaming options for.
    :return: A list of fake StreamingOptions.
    :raise ValueError: If n is negative or over 100.
    """

    if n < 0 or n > 100:
        raise ValueError("n has to be between 0 to 100, inclusive.")

    output = []

    for i in range(n):
        output.append(
            StreamingOption(
                movie_id=movie_id,
                country_code=country_code,
                service_id=service_id,
                link=f"www.example{i:02d}.com",
                expires_soon=False
            ))

    return output

# ==================================================


class CopyingMock(MagicMock):
    """
    For copying the arguments given to mocks, since Mocks will only store references.

    This is used for assertions, when determining if the arguments to mock calls are correct.  Originally, when a mock
    is called with the same mutable argument, the list of call arguments will only show the last value for the mutable
    argument, no matter the value the mock was given at the time.

    see
    https://docs.python.org/3/library/unittest.mock-examples.html#coping-with-mutable-arguments
    """

    def __call__(self, /, *args, **kwargs):
        args = deepcopy(args)
        kwargs = deepcopy(kwargs)
        return super().__call__(*args, **kwargs)
