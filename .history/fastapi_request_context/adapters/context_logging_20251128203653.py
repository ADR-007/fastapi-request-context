"""Context adapter using context-logging library."""

from typing import Any


class ContextLoggingAdapter:
    """Context adapter using the context-logging library.

    This adapter integrates with the context-logging library for automatic
    context injection into log records. Requires the optional dependency:

        pip install fastapi-request-context[context-logging]

    Benefits over ContextVarsAdapter:
        - Automatic injection into log records
        - Thread-safe with copy-on-write semantics
        - Built-in support for nested contexts

    Example:
        >>> from fastapi_request_context import RequestContextMiddleware, RequestContextConfig
        >>> from fastapi_request_context.adapters import ContextLoggingAdapter
        >>>
        >>> config = RequestContextConfig(context_adapter=ContextLoggingAdapter())
        >>> app = RequestContextMiddleware(app, config=config)

    Raises:
        ImportError: If context-logging is not installed.
    """

    def __init__(self) -> None:
        """Initialize the adapter.

        Raises:
            ImportError: If context-logging is not installed.
        """
        try:
            from context_logging import current_context  # noqa: F401
        except ImportError as e:
            msg = (
                "context-logging is required for ContextLoggingAdapter. "
                "Install with: pip install fastapi-request-context[context-logging]"
            )
            raise ImportError(msg) from e

        self._context_manager: Any = None

    def set_value(self, key: str, value: Any) -> None:
        """Set a context value.

        Args:
            key: The context key.
            value: The value to store.
        """
        from context_logging import current_context

        current_context[key] = value

    def get_value(self, key: str) -> Any:
        """Get a context value.

        Args:
            key: The context key to retrieve.

        Returns:
            The stored value, or None if not set.
        """
        from context_logging import current_context

        return current_context.get(key)

    def get_all(self) -> dict[str, Any]:
        """Get all context values.

        Returns:
            A copy of all stored context key-value pairs.
        """
        from context_logging import current_context

        return dict(current_context)

    def enter_context(self, initial_values: dict[str, Any]) -> None:
        """Enter a new context scope with initial values.

        Args:
            initial_values: Initial context values to set.
        """
        from context_logging import Context

        self._context_manager = Context(**initial_values)
        self._context_manager.__enter__()

    def exit_context(self) -> None:
        """Exit the current context scope."""
        if self._context_manager is not None:
            self._context_manager.__exit__(None, None, None)
            self._context_manager = None
