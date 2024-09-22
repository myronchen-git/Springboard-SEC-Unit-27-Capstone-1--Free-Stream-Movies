from src.exceptions.base_exceptions import FreeStreamMoviesServerError


class DatabaseError(FreeStreamMoviesServerError):
    """Represents a generic error related to the database, when there is no other specific error."""

    def __init__(self, message):
        super().__init__(message)
