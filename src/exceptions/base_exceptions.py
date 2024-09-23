class FreeStreamMoviesError(Exception):
    """Represents an Exception in FreeStreamMovies.  This is the base Exception for all Exceptions."""

    def __init__(self, message, status_code):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class FreeStreamMoviesClientError(FreeStreamMoviesError):
    """Represents an error caused by the client."""

    def __init__(self, message, status_code=400):
        super().__init__(message, status_code)


class FreeStreamMoviesServerError(FreeStreamMoviesError):
    """Represents an error caused by the server."""

    def __init__(self, message, status_code=500):
        super().__init__(message, status_code)
