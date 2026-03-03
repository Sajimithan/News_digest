"""
Shared date-resolution utility.

Single source of truth for converting "today" / "yesterday" / "YYYY-MM-DD"
into an ISO-8601 date string.  Import and use in any service or route that
accepts relative date strings from users or LLM tool calls.
"""

from datetime import date, timedelta


def resolve_date(d: str) -> str:
    """
    Convert a relative or absolute date string to ``YYYY-MM-DD``.

    Recognised values (case-insensitive):
        ``"today"``      → today's date
        ``"yesterday"``  → yesterday's date
        ``"YYYY-MM-DD"`` → returned unchanged after strip

    Args:
        d: Raw date string from user input or an LLM tool-call argument.

    Returns:
        ISO-8601 date string, e.g. ``"2026-02-24"``.
    """
    d = (d or "").strip().lower()
    if d == "today":
        return date.today().isoformat()
    if d == "yesterday":
        return (date.today() - timedelta(days=1)).isoformat()
    return d


def validate_iso_date(d: str) -> str:
    """
    Assert that ``d`` is a valid ``YYYY-MM-DD`` string.

    Args:
        d: Date string to validate.

    Returns:
        The same string if valid.

    Raises:
        ValueError: If the string cannot be parsed as an ISO-8601 date.
    """
    date.fromisoformat(d)   # raises ValueError if malformed
    return d
