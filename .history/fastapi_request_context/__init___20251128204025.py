"""FastAPI middleware for request ID tracking, correlation IDs, and extensible request context.

This library provides:
- Automatic request ID generation for every request
- Correlation ID support for distributed tracing
- Response header injection (X-Request-Id, X-Correlation-Id)
- Pluggable context storage (contextvars, context-logging)
- Extensible context fields via StrEnum
- Logging formatters with automatic context injection
- Validation utilities for async routes and dependencies

Basic Usage:
    >>> from fastapi import FastAPI
    >>> from fastapi_request_context import RequestContextMiddleware
    >>>
    >>> app = FastAPI()
    >>> app = RequestContextMiddleware(app)

Custom Fields:
    >>> from enum import StrEnum
    >>> from fastapi_request_context import set_context, get_context
    >>>
    >>> class MyField(StrEnum):
    ...     USER_ID = "user_id"
    >>>
    >>> set_context(MyField.USER_ID, 123)
    >>> user_id = get_context(MyField.USER_ID)
"""

from fastapi_request_context.config import RequestContextConfig
from fastapi_request_context.context import (
    get_adapter,
    get_context,
    get_full_context,
    set_adapter,
    set_context,
)
from fastapi_request_context.fields import StandardContextField
from fastapi_request_context.middleware import (
    FastAPIWrapperMiddleware,
    RequestContextMiddleware,
)

__all__ = [
    "FastAPIWrapperMiddleware",
    "RequestContextConfig",
    "RequestContextMiddleware",
    "StandardContextField",
    "get_adapter",
    "get_context",
    "get_full_context",
    "set_adapter",
    "set_context",
]

__version__ = "0.1.0"
