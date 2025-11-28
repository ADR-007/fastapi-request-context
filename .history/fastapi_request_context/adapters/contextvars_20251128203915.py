"""Context adapter using Python's built-in contextvars."""

from contextvars import ContextVar
from typing import Any

from fastapi_request_context.types import ContextDict

# Module-level ContextVar to ensure proper async isolation
_context_var: ContextVar[ContextDict | None] = ContextVar(
    "fastapi_request_context",
    default=None,
)


class ContextVarsAdapter:
    """Context adapter using Python's built-in contextvars.

    This is the default adapter as it has no external dependencies.
    It stores all context values in a module-level ContextVar containing a dict.

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

    def set_value(self, key: str, value: Any) -> None:
        """Set a context value.

        Args:
            key: The context key.
            value: The value to store.
        """
        context = _context_var.get()
        context[key] = value

    def get_value(self, key: str) -> Any:
        """Get a context value.

        Args:
            key: The context key to retrieve.

        Returns:
            The stored value, or None if not set.
        """
        return _context_var.get().get(key)

    def get_all(self) -> dict[str, Any]:
        """Get all context values.

        Returns:
            A copy of all stored context key-value pairs.
        """
        return dict(_context_var.get())

    def enter_context(self, initial_values: dict[str, Any]) -> None:
        """Enter a new context scope with initial values.

        Args:
            initial_values: Initial context values to set.
        """
        # Set a new dict for this context - contextvars handles isolation
        _context_var.set(dict(initial_values))

    def exit_context(self) -> None:
        """Exit the current context scope.

        Clears the context dict. Each async task has its own copy due to
        contextvars copy-on-write semantics.
        """
        _context_var.set({})
