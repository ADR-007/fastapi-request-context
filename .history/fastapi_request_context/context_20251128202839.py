"""Context management functions."""

from enum import Enum
from typing import Any

from fastapi_request_context.adapters.base import ContextAdapter
from fastapi_request_context.adapters.contextvars import ContextVarsAdapter
from fastapi_request_context.types import ContextDict

# Global adapter instance, set by middleware
_adapter: ContextAdapter = ContextVarsAdapter()


def set_adapter(adapter: ContextAdapter) -> None:
    """Set the global context adapter.

    This is called by the middleware during initialization.
    You typically don't need to call this directly.

    Args:
        adapter: The context adapter to use.
    """
    global _adapter  # noqa: PLW0603
    _adapter = adapter


def get_adapter() -> ContextAdapter:
    """Get the current context adapter.

    Returns:
        The currently configured context adapter.
    """
    return _adapter


def set_context(key: str | Enum, value: Any) -> None:
    """Set a context value.

    The value will be available throughout the request lifecycle and
    automatically included in log records (when using appropriate adapters
    and formatters).

    Args:
        key: The context key. Can be a string or an Enum (uses .value).
        value: The value to store.

    Example:
        >>> from enum import StrEnum
        >>> from fastapi_request_context import set_context
        >>>
        >>> class MyField(StrEnum):
        ...     USER_ID = "user_id"
        >>>
        >>> set_context(MyField.USER_ID, 123)
        >>> set_context("custom_field", "custom_value")
    """
    field_key = key.value if isinstance(key, Enum) else key
    _adapter.set_value(field_key, value)


def get_context(key: str | Enum) -> Any:
    """Get a context value.

    Args:
        key: The context key. Can be a string or an Enum (uses .value).

    Returns:
        The stored value, or None if not set.

    Example:
        >>> from fastapi_request_context import get_context, StandardContextField
        >>>
        >>> request_id = get_context(StandardContextField.REQUEST_ID)
        >>> user_id = get_context("user_id")
    """
    field_key = key.value if isinstance(key, Enum) else key
    return _adapter.get_value(field_key)


def get_full_context() -> ContextDict:
    """Get all context values.

    Returns:
        A copy of all stored context key-value pairs.

    Example:
        >>> from fastapi_request_context import get_full_context
        >>>
        >>> context = get_full_context()
        >>> print(context)
        {'request_id': '...', 'correlation_id': '...', 'user_id': 123}
    """
    return _adapter.get_all()
