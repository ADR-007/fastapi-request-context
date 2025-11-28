"""Context storage adapters."""

from fastapi_request_context.adapters.base import ContextAdapter
from fastapi_request_context.adapters.context_logging import ContextLoggingAdapter
from fastapi_request_context.adapters.contextvars import ContextVarsAdapter

__all__ = [
    "ContextAdapter",
    "ContextLoggingAdapter",
    "ContextVarsAdapter",
]
