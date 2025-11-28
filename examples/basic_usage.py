"""Basic usage example - zero configuration.

This example shows the simplest way to use fastapi-request-context.
Every request automatically gets:
- Unique request_id (always generated)
- Correlation_id (from header or generated)
- Both added to response headers
"""

from fastapi import FastAPI

from fastapi_request_context import (
    RequestContextMiddleware,
    StandardContextField,
    get_context,
    get_full_context,
)

app = FastAPI()


@app.get("/")
async def root() -> dict[str, str]:
    """Simple endpoint that returns request IDs."""
    return {
        "request_id": get_context(StandardContextField.REQUEST_ID),
        "correlation_id": get_context(StandardContextField.CORRELATION_ID),
    }


@app.get("/full-context")
async def full_context() -> dict[str, str]:
    """Return all context values."""
    return get_full_context()


# Wrap with middleware - that's it!
app = RequestContextMiddleware(app)  # type: ignore[assignment]

if __name__ == "__main__":
    import uvicorn

    print("Starting server at http://localhost:8000")
    print("Try: curl -v http://localhost:8000/")
    print("Try: curl -H 'X-Correlation-Id: my-trace-123' http://localhost:8000/")
    uvicorn.run(app, host="0.0.0.0", port=8000)  # noqa: S104
