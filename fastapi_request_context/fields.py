"""Standard context field definitions."""

from enum import StrEnum


class StandardContextField(StrEnum):
    """Standard context fields provided by the library.

    These are the built-in fields that the middleware automatically sets.
    Applications can define their own StrEnum for custom fields.

    Example:
        >>> from enum import StrEnum
        >>> class MyAppField(StrEnum):
        ...     USER_ID = "user_id"
        ...     ORG_ID = "org_id"
        >>>
        >>> set_context(MyAppField.USER_ID, 123)
    """

    REQUEST_ID = "request_id"
    """Unique identifier for this request. Always generated, never from header."""

    CORRELATION_ID = "correlation_id"
    """Correlation ID for distributed tracing. May be from header or generated."""
