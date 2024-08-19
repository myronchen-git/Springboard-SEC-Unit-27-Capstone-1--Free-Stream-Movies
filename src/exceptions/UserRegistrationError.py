from src.exceptions.base_exceptions import FreeStreamMoviesClientError


class UserRegistrationError(FreeStreamMoviesClientError):
    """Represents an error raised during user registration."""

    def __init__(self, message):
        super().__init__(message)
