"""Configuration for RequestContextMiddleware."""

from dataclasses import dataclass, field
from typing import Union
from uuid import uuid4

from fastapi_request_context.adapters.base import ContextAdapter
from fastapi_request_context.adapters.contextvars import ContextVarsAdapter
from fastapi_request_context.types import IdGeneratorFunc


def _default_id_generator() -> str:
    """Generate a UUID4 string."""
    return str(uuid4())


@dataclass
class RequestContextConfig:
    """Configuration for RequestContextMiddleware.

    All settings have sensible defaults, so you can use the middleware
    with zero configuration.

    Attributes:
        request_id_generator: Function to generate request IDs. Default: UUID4.
        correlation_id_generator: Function to generate correlation IDs. Default: UUID4.
        request_id_header: Header name for request ID. Default: "X-Request-Id".
        correlation_id_header: Header name for correlation ID. Default: "X-Correlation-Id".
        add_response_headers: Whether to add headers to response. Default: True.
        context_adapter: Context storage adapter. Default: ContextVarsAdapter.
        scope_types: ASGI scope types to process. Default: {"http", "websocket"}.

    Example:
        >>> from fastapi_request_context import RequestContextMiddleware, RequestContextConfig
        >>>
        >>> # Custom configuration
        >>> config = RequestContextConfig(
        ...     request_id_header="X-My-Request-Id",
        ...     add_response_headers=False,
        ... )
        >>> app = RequestContextMiddleware(app, config=config)
    """

    request_id_generator: IdGeneratorFunc = field(default=_default_id_generator)
    """Function to generate unique request IDs."""

    correlation_id_generator: IdGeneratorFunc = field(default=_default_id_generator)
    """Function to generate correlation IDs when not provided in header."""

    request_id_header: str = "X-Request-Id"
    """Header name for request ID in responses."""

    correlation_id_header: str = "X-Correlation-Id"
    """Header name for correlation ID in requests and responses."""

    add_response_headers: bool = True
    """Whether to add request_id and correlation_id to response headers."""

    context_adapter: Union[ContextAdapter, str] = field(  # noqa: UP007
        default_factory=ContextVarsAdapter,
    )
    """Context storage adapter. Can be an adapter instance or "contextvars"/"context_logging"."""

    scope_types: set[str] = field(default_factory=lambda: {"http", "websocket"})
    """ASGI scope types to process. Other types pass through unchanged."""
