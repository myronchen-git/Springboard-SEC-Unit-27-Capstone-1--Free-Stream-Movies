from src.exceptions.base_exceptions import FreeStreamMoviesServerError


class StreamingAvailabilityApiError(FreeStreamMoviesServerError):
    """Represents when Streaming Availability API returns a status code that is not 200."""

    def __init__(self, message, status_code=500):
        super().__init__(message, status_code)
