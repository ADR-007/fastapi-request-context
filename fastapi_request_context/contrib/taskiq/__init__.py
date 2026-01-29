"""Taskiq integration for request context propagation.

This module provides middleware for Taskiq that propagates request context
from FastAPI requests to background tasks, enabling distributed tracing and
consistent logging across async task execution.

Example:
    >>> from taskiq import InMemoryBroker
    >>> from fastapi_request_context.contrib.taskiq import RequestContextTaskiqMiddleware
    >>>
    >>> broker = InMemoryBroker()
    >>> broker = broker.with_middlewares(RequestContextTaskiqMiddleware())
"""

from fastapi_request_context.contrib.taskiq.middleware import RequestContextTaskiqMiddleware

__all__ = ["RequestContextTaskiqMiddleware"]
