"""Request context middleware for FastAPI."""

from typing import Any

from starlette.types import ASGIApp, Message, Receive, Scope, Send

from fastapi_request_context.adapters.base import ContextAdapter
from fastapi_request_context.adapters.context_logging import ContextLoggingAdapter
from fastapi_request_context.adapters.contextvars import ContextVarsAdapter
from fastapi_request_context.config import RequestContextConfig
from fastapi_request_context.context import set_adapter
from fastapi_request_context.fields import StandardContextField


def _get_adapter(adapter_config: ContextAdapter | str) -> ContextAdapter:
    """Get adapter instance from config value.

    Args:
        adapter_config: Either an adapter instance or a string identifier.

    Returns:
        A ContextAdapter instance.

    Raises:
        ValueError: If string identifier is not recognized.
    """
    if isinstance(adapter_config, str):
        if adapter_config == "contextvars":
            return ContextVarsAdapter()
        if adapter_config == "context_logging":
            return ContextLoggingAdapter()
        msg = f"Unknown adapter: {adapter_config}. Use 'contextvars' or 'context_logging'."
        raise ValueError(msg)
    return adapter_config


def _get_header_value(scope: Scope, header_name: str) -> str | None:
    """Extract header value from ASGI scope (case-insensitive).

    Args:
        scope: ASGI scope.
        header_name: Header name to find.

    Returns:
        Header value or None if not found.
    """
    headers: list[tuple[bytes, bytes]] = scope.get("headers", [])
    header_name_lower = header_name.lower().encode()
    for name, value in headers:
        if name.lower() == header_name_lower:
            return value.decode()
    return None


class RequestContextMiddleware:
    """ASGI middleware for request context management.

    This middleware:
    1. Generates a unique request_id for each request
    2. Accepts or generates a correlation_id for distributed tracing
    3. Stores both in context (accessible via get_context())
    4. Adds both to response headers

    The middleware can wrap a FastAPI application or any ASGI app.

    Example:
        >>> from fastapi import FastAPI
        >>> from fastapi_request_context import RequestContextMiddleware
        >>>
        >>> app = FastAPI()
        >>> app = RequestContextMiddleware(app)

    With configuration:
        >>> from fastapi_request_context import RequestContextMiddleware, RequestContextConfig
        >>>
        >>> config = RequestContextConfig(
        ...     request_id_header="X-My-Request-Id",
        ...     add_response_headers=False,
        ... )
        >>> app = RequestContextMiddleware(app, config=config)
    """

    def __init__(
        self,
        app: ASGIApp,
        config: RequestContextConfig | None = None,
    ) -> None:
        """Initialize the middleware.

        Args:
            app: The ASGI application to wrap.
            config: Optional configuration. Uses defaults if not provided.
        """
        self.app = app
        self.config = config or RequestContextConfig()
        self._adapter = _get_adapter(self.config.context_adapter)
        # Set global adapter for context functions
        set_adapter(self._adapter)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Process ASGI request.

        Args:
            scope: ASGI scope.
            receive: ASGI receive function.
            send: ASGI send function.
        """
        # Only process configured scope types
        if scope["type"] not in self.config.scope_types:
            await self.app(scope, receive, send)
            return

        # Generate request_id (always new for security)
        request_id = self.config.request_id_generator()

        # Get or generate correlation_id
        correlation_id = (
            _get_header_value(
                scope,
                self.config.correlation_id_header,
            )
            or self.config.correlation_id_generator()
        )

        # Set up context
        initial_context: dict[str, Any] = {
            StandardContextField.REQUEST_ID.value: request_id,
            StandardContextField.CORRELATION_ID.value: correlation_id,
        }

        self._adapter.enter_context(initial_context)

        try:
            if self.config.add_response_headers:
                # Wrap send to inject headers
                async def send_with_headers(message: Message) -> None:
                    if message["type"] == "http.response.start":
                        headers: list[tuple[bytes, bytes]] = list(
                            message.get("headers", []),
                        )
                        headers.append(
                            (
                                self.config.request_id_header.lower().encode(),
                                request_id.encode(),
                            ),
                        )
                        headers.append(
                            (
                                self.config.correlation_id_header.lower().encode(),
                                correlation_id.encode(),
                            ),
                        )
                        message = {**message, "headers": headers}
                    await send(message)

                await self.app(scope, receive, send_with_headers)
            else:
                await self.app(scope, receive, send)
        finally:
            self._adapter.exit_context()


