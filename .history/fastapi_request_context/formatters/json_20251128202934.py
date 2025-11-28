"""JSON formatter for production logging."""

import logging
from typing import Any

from fastapi_request_context.context import get_full_context


class JsonContextFormatter(logging.Formatter):
    """JSON formatter that includes request context.

    Outputs log records as JSON with automatic context injection.
    Ideal for production environments with log aggregation (ELK, CloudWatch, etc.).

    If python-json-logger is installed, uses it for better JSON formatting.
    Otherwise, falls back to a simple JSON implementation.

    Example:
        >>> import logging
        >>> from fastapi_request_context.formatters import JsonContextFormatter
        >>>
        >>> handler = logging.StreamHandler()
        >>> handler.setFormatter(JsonContextFormatter())
        >>> logging.basicConfig(handlers=[handler], level=logging.INFO)
        >>>
        >>> logging.info("Request processed")
        # Output: {"message": "Request processed", "level": "INFO",
        #          "request_id": "...", "correlation_id": "..."}

    Attributes:
        context_key: Key name for nested context in output (None for flat).
        include_standard_fields: Include level, name, timestamp in output.
    """

    def __init__(
        self,
        fmt: str | None = None,
        datefmt: str | None = None,
        context_key: str | None = None,
        include_standard_fields: bool = True,
    ) -> None:
        """Initialize the formatter.

        Args:
            fmt: Format string (unused, kept for compatibility).
            datefmt: Date format string.
            context_key: If set, nest context under this key.
                        If None, merge context at top level.
            include_standard_fields: Include level, logger name, timestamp.
        """
        super().__init__(fmt=fmt, datefmt=datefmt)
        self.context_key = context_key
        self.include_standard_fields = include_standard_fields
        self._json_formatter: logging.Formatter | None = None

        # Try to use python-json-logger if available
        try:
            from pythonjsonlogger import jsonlogger

            self._json_formatter = jsonlogger.JsonFormatter(datefmt=datefmt)
        except ImportError:
            pass

    def format(self, record: logging.LogRecord) -> str:
        """Format the log record as JSON.

        Args:
            record: The log record to format.

        Returns:
            JSON-formatted string.
        """
        import json

        # Build base log data
        log_data: dict[str, Any] = {
            "message": record.getMessage(),
        }

        if self.include_standard_fields:
            log_data.update({
                "level": record.levelname,
                "logger": record.name,
                "timestamp": self.formatTime(record, self.datefmt),
            })

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Add context
        context = get_full_context()
        if context:
            if self.context_key:
                log_data[self.context_key] = context
            else:
                log_data.update(context)

        return json.dumps(log_data, default=str)
