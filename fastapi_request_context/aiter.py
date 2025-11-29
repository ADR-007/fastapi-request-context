"""Utilities for async iterators with context preservation."""

from collections.abc import AsyncIterator, Awaitable, Callable
from functools import wraps


def aiter_with_logging_context[**P, R](
    func: Callable[P, Awaitable[AsyncIterator[R]] | AsyncIterator[R]],
) -> Callable[P, AsyncIterator[R]]:
    """Wrap an async iterator function to preserve logging context during iteration.

    This is useful for streaming responses where iteration happens outside
    the original request context. The context is captured when this decorator
    is called and restored during iteration.

    Requires the `context-logging` package to be installed.

    Example:
        ```python
        from fastapi import FastAPI
        from fastapi.responses import StreamingResponse
        from fastapi_request_context import aiter_with_logging_context

        app = FastAPI()

        @app.get("/stream")
        async def stream():
            async def generate():
                # Context is preserved here during iteration
                for i in range(10):
                    yield f"chunk {i}"

            return StreamingResponse(aiter_with_logging_context(generate)())
        ```

    Args:
        func: An async function that returns an async iterator.

    Returns:
        A wrapped function that preserves the logging context during iteration.

    Raises:
        ImportError: If `context-logging` package is not installed.
    """
    try:
        from context_logging import Context, current_context  # noqa: PLC0415
    except ImportError as e:  # pragma: no cover
        msg = (
            "The 'context-logging' package is required for aiter_with_logging_context. "
            "Install it with: pip install fastapi-request-context[context-logging]"
        )
        raise ImportError(msg) from e

    current_context_dict = dict(current_context)

    @wraps(func)
    async def wrapper(*args: P.args, **kwargs: P.kwargs) -> AsyncIterator[R]:
        with Context(**current_context_dict):
            result = func(*args, **kwargs)
            if isinstance(result, Awaitable):
                result = await result

            async for item in result:
                yield item

    return wrapper
