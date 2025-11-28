"""Local development formatter with human-readable output."""

import logging
from collections.abc import Set as AbstractSet

from fastapi_request_context.context import get_full_context


class LocalContextFormatter(logging.Formatter):
    """Human-readable formatter for local development.

    Outputs log records in a readable format with context inline.
    Supports shortening UUIDs and hiding fields for cleaner output.

    Example:
        >>> import logging
        >>> from fastapi_request_context import StandardContextField
        >>> from fastapi_request_context.formatters import LocalContextFormatter
        >>>
        >>> formatter = LocalContextFormatter(
        ...     fmt="%(asctime)s %(levelname)s %(context)s %(message)s",
        ...     shorten_fields={StandardContextField.REQUEST_ID},
        ...     hidden_fields={StandardContextField.CORRELATION_ID},
        ... )
        >>> handler = logging.StreamHandler()
        >>> handler.setFormatter(formatter)
        >>> logging.basicConfig(handlers=[handler], level=logging.INFO)
        >>>
        >>> logging.info("Request processed")
        # Output: 2025-01-15 10:30:00 INFO [request_id=3fa85f64] Request processed

    Attributes:
        shorten_fields: Fields to truncate to 8 characters (e.g., UUIDs).
        hidden_fields: Fields to completely hide from output.
        shorten_length: Number of characters for shortened fields.
    """

    def __init__(
        self,
        fmt: str | None = None,
        datefmt: str | None = None,
        shorten_fields: AbstractSet[str] | None = None,
        hidden_fields: AbstractSet[str] | None = None,
        shorten_length: int = 8,
    ) -> None:
        """Initialize the formatter.

        Args:
            fmt: Format string. Use %(context)s for context placeholder.
            datefmt: Date format string.
            shorten_fields: Set of field names to truncate.
            hidden_fields: Set of field names to hide.
            shorten_length: Length for shortened field values.
        """
        # Default format if not provided
        if fmt is None:
            fmt = "%(asctime)s %(levelname)s %(context)s %(message)s"

        super().__init__(fmt=fmt, datefmt=datefmt)
        self.shorten_fields = shorten_fields or set()
        self.hidden_fields = hidden_fields or set()
        self.shorten_length = shorten_length

    def _format_context(self) -> str:
        """Format context values for display.

        Returns:
            Formatted context string like "[key1=val1 key2=val2]".
        """
        context = get_full_context()
        if not context:
            return ""

        parts: list[str] = []
        for key, value in context.items():
            # Skip hidden fields
            if key in self.hidden_fields:
                continue

            # Shorten if configured
            str_value = str(value)
            if key in self.shorten_fields and len(str_value) > self.shorten_length:
                str_value = str_value[: self.shorten_length]

            parts.append(f"{key}={str_value}")

        if not parts:
            return ""

        return f"[{' '.join(parts)}]"

    def format(self, record: logging.LogRecord) -> str:
        """Format the log record with context.

        Args:
            record: The log record to format.

        Returns:
            Formatted string with context.
        """
        # Add context to record for format string
        record.context = self._format_context()  # type: ignore[attr-defined, unused-ignore]
        return super().format(record)
