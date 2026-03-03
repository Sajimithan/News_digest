"""
Custom application exception classes.

Raise these from services or routes; the global handlers in handlers.py
will convert them to the correct HTTP status code and JSON shape.
"""


class ProviderError(Exception):
    """
    Raised when an external news provider (Guardian, NewsAPI, etc.) fails —
    network error, bad API key, unexpected response format, rate-limit, etc.

    Attributes:
        provider: Name of the provider that failed (e.g. "NewsAPI.org").
        message:  Human-readable description of the failure.
    """

    def __init__(self, message: str, provider: str = "unknown") -> None:
        super().__init__(message)
        self.provider = provider
        self.message = message


class DataNotFoundError(Exception):
    """
    Raised when a requested resource (e.g. news for a specific date) does not
    exist in the database and no live data could be fetched.

    Attributes:
        message: Human-readable description of what was not found.
    """

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class InputValidationError(Exception):
    """
    Raised for malformed user input that fails before Pydantic validation —
    e.g. an invalid date string or a missing required field in a JSON payload.

    Attributes:
        message: Human-readable description of the validation failure.
        field:   Optional name of the offending field.
    """

    def __init__(self, message: str, field: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.field = field
