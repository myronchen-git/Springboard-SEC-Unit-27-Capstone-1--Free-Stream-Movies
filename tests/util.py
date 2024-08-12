from models.movie import Movie
from models.service import Service
from models.streaming_option import StreamingOption

# ==================================================


def service_generator(n: int) -> list[Service]:
    """Creates n Services, with zero-indexed naming, and returning them in a List."""

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


def movie_generator(n: int) -> list[Movie]:
    """Creates n Movies, with zero-indexed naming, and returning them in a List."""

    if n < 0 or n > 100:
        raise ValueError("n has to be between 0 to 100, inclusive.")

    output = []

    for i in range(n):
        output.append(
            Movie(
                id=i,
                imdb_id=f"tt04685{i:02d}",
                tmdb_id=f"movie/1{i:02d}",
                title=f"Movie {i:02d}",
                overview="batman",
                release_year=2008,
                original_title=f"The Movie {i:02d}",
                directors=["Christopher Nolan"],
                cast=["Christian Bale", "Heath Ledger", "Michael Caine"],
                rating=i,
                runtime=120
            ))

    return output


def streaming_option_generator(n: int, movie_id: str, country_code: str, service_id: str) -> list[StreamingOption]:
    """Creates n StreamingOptions, with zero-indexed naming, and returning them in a List."""

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
