from src.exceptions.base_exceptions import FreeStreamMoviesClientError


class UnrecognizedValueError(FreeStreamMoviesClientError):
    """When a client gives a value that is outside the bounds of acceptable values."""

    def __init__(self, message):
        super().__init__(message)
