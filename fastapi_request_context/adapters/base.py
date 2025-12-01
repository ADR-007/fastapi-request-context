"""Base protocol for context adapters."""

from typing import Any, Protocol, Self, runtime_checkable


@runtime_checkable
class ContextAdapter(Protocol):
    """Protocol for context storage adapters.

    Adapters provide the underlying storage mechanism for request context.
    The library provides two built-in adapters:

    - `ContextVarsAdapter`: Uses Python's built-in contextvars (default, no deps)
    - `ContextLoggingAdapter`: Uses context-logging library (optional dependency)

    Custom adapters can be created by implementing this protocol.
    Adapters are context managers - use `with adapter:` to enter/exit scope.
    See examples/custom_adapter.py for a complete example.
    """

    def set_value(self, key: str, value: Any) -> None:  # noqa: ANN401
        """Set a context value.

        Args:
            key: The context key (e.g., "request_id", "user_id").
            value: The value to store.
        """
        ...

    def get_value(self, key: str) -> Any:  # noqa: ANN401
        """Get a context value.

        Args:
            key: The context key to retrieve.

        Returns:
            The stored value, or None if not set.
        """
        ...

    def get_all(self) -> dict[str, Any]:
        """Get all context values.

        Returns:
            A copy of all stored context key-value pairs.
        """
        ...

    def __enter__(self) -> Self:
        """Enter a new context scope.

        Called at the start of each request to initialize context storage.

        Returns:
            Self for use in with statement.
        """
        ...

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> None:
        """Exit the current context scope.

        Called at the end of each request to clean up context storage.
        """
        ...
