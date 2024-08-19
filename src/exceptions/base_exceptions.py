class FreeStreamMoviesClientError(Exception):
    """Represents an error caused by the client."""

    def __init__(self, message):
        super().__init__(message)


class FreeStreamMoviesServerError(Exception):
    """Represents an error caused by the server."""

    def __init__(self, message):
        super().__init__(message)
