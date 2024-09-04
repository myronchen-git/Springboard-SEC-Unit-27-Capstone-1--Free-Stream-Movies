from src.exceptions.base_exceptions import FreeStreamMoviesServerError


class StreamingAvailabilityApiError(FreeStreamMoviesServerError):
    """
    Represents when Streaming Availability API returns a status code
    that is not 200 and not the fault of the client.
    """

    def __init__(self, message):
        super().__init__(message)