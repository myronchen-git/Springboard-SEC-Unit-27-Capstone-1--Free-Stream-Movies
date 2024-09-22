from src.exceptions.base_exceptions import FreeStreamMoviesServerError


class UpsertError(FreeStreamMoviesServerError):
    """Represents an error raised when updating/inserting to database."""

    def __init__(self, message):
        super().__init__(message)
