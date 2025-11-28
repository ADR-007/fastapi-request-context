"""Context adapter using Python's built-in contextvars."""

from contextvars import ContextVar, Token
from typing import Any

from fastapi_request_context.types import ContextDict


class ContextVarsAdapter:
    """Context adapter using Python's built-in contextvars.

    This is the default adapter as it has no external dependencies.
    It stores all context values in a single ContextVar containing a dict.

    Note:
        This adapter works correctly with async code. However, sync code
        running in thread pools may not see context values. Use the
        validation utilities to ensure all routes and dependencies are async.

    Example:
        >>> from fastapi_request_context import RequestContextMiddleware, RequestContextConfig
        >>> from fastapi_request_context.adapters import ContextVarsAdapter
        >>>
        >>> config = RequestContextConfig(context_adapter=ContextVarsAdapter())
        >>> app = RequestContextMiddleware(app, config=config)
    """

    def __init__(self) -> None:
        """Initialize the adapter with a ContextVar."""
        self._context_var: ContextVar[ContextDict] = ContextVar(
            "request_context",
            default={},
        )
        self._token: Token[ContextDict] | None = None

    def set_value(self, key: str, value: Any) -> None:
        """Set a context value.

        Args:
            key: The context key.
            value: The value to store.
        """
        context = self._context_var.get()
        context[key] = value

    def get_value(self, key: str) -> Any:
        """Get a context value.

        Args:
            key: The context key to retrieve.

        Returns:
            The stored value, or None if not set.
        """
        return self._context_var.get().get(key)

    def get_all(self) -> dict[str, Any]:
        """Get all context values.

        Returns:
            A copy of all stored context key-value pairs.
        """
        return dict(self._context_var.get())

    def enter_context(self, initial_values: dict[str, Any]) -> None:
        """Enter a new context scope with initial values.

        Args:
            initial_values: Initial context values to set.
        """
        self._token = self._context_var.set(dict(initial_values))

    def exit_context(self) -> None:
        """Exit the current context scope and reset to previous state."""
        if self._token is not None:
            self._context_var.reset(self._token)
            self._token = None
