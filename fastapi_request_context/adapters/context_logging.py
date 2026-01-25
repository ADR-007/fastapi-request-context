"""Context adapter using context-logging library."""

from typing import Any, Self


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
        >>> adapter = ContextLoggingAdapter(
        ...     name="request_context",
        ...     log_execution_time=True,
        ...     fill_exception_context=True
        ... )
        >>> config = RequestContextConfig(context_adapter=adapter)
        >>> app = RequestContextMiddleware(app, config=config)

    Raises:
        ImportError: If context-logging is not installed.
    """

    def __init__(
        self,
        name: str | None = None,
        *,
        log_execution_time: bool | None = None,
        fill_exception_context: bool | None = None,
    ) -> None:
        """Initialize the adapter.

        Args:
            name: Optional name for the context.
            log_execution_time: Whether to log execution time for the context.
            fill_exception_context: Whether to fill exception context automatically.

        Raises:
            ImportError: If context-logging is not installed.
        """
        try:
            from context_logging import current_context  # noqa: F401, PLC0415
        except ImportError as e:
            msg = (
                "context-logging is required for ContextLoggingAdapter. "
                "Install with: pip install fastapi-request-context[context-logging]"
            )
            raise ImportError(msg) from e

        self._name = name
        self._log_execution_time = log_execution_time
        self._fill_exception_context = fill_exception_context
        self._context_manager: Any = None

    def set_value(self, key: str, value: Any) -> None:  # noqa: ANN401
        """Set a context value.

        Args:
            key: The context key.
            value: The value to store.
        """
        from context_logging import current_context  # noqa: PLC0415

        current_context[key] = value

    def get_value(self, key: str) -> Any:  # noqa: ANN401
        """Get a context value.

        Args:
            key: The context key to retrieve.

        Returns:
            The stored value, or None if not set.
        """
        from context_logging import current_context  # noqa: PLC0415

        return current_context.get(key)

    def get_all(self) -> dict[str, Any]:
        """Get all context values.

        Returns:
            A copy of all stored context key-value pairs.
        """
        from context_logging import current_context  # noqa: PLC0415

        return dict(current_context)

    def __enter__(self) -> Self:
        """Enter a new context scope.

        Returns:
            Self for use in with statement.
        """
        from context_logging import Context  # noqa: PLC0415

        self._context_manager = Context(
            self._name,
            log_execution_time=self._log_execution_time,
            fill_exception_context=self._fill_exception_context,
        )
        self._context_manager.__enter__()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> None:
        """Exit the current context scope.

        Note:
            The context-logging library automatically adds context to exceptions
            via `fill_exception_context` (enabled by default). It sets
            `__context_logging__` attribute on the exception to avoid double-adding.
        """
        if self._context_manager is not None:
            self._context_manager.__exit__(exc_type, exc_val, exc_tb)
            self._context_manager = None
