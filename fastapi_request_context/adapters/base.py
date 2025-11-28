"""Base protocol for context adapters."""

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class ContextAdapter(Protocol):
    """Protocol for context storage adapters.

    Adapters provide the underlying storage mechanism for request context.
    The library provides two built-in adapters:

    - `ContextVarsAdapter`: Uses Python's built-in contextvars (default, no deps)
    - `ContextLoggingAdapter`: Uses context-logging library (optional dependency)

    Custom adapters can be created by implementing this protocol.

    Example:
        >>> class RedisAdapter(ContextAdapter):
        ...     def set_value(self, key: str, value: Any) -> None:
        ...         redis.hset(self._request_key, key, value)
        ...
        ...     def get_value(self, key: str) -> Any:
        ...         return redis.hget(self._request_key, key)
        ...
        ...     def get_all(self) -> dict[str, Any]:
        ...         return redis.hgetall(self._request_key)
        ...
        ...     def enter_context(self, initial_values: dict[str, Any]) -> None:
        ...         self._request_key = f"request:{uuid4()}"
        ...         redis.hmset(self._request_key, initial_values)
        ...
        ...     def exit_context(self) -> None:
        ...         redis.delete(self._request_key)
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

    def enter_context(self, initial_values: dict[str, Any]) -> None:
        """Enter a new context scope with initial values.

        Called at the start of each request to initialize context storage.

        Args:
            initial_values: Initial context values to set (e.g., request_id).
        """
        ...

    def exit_context(self) -> None:
        """Exit the current context scope.

        Called at the end of each request to clean up context storage.
        """
        ...
