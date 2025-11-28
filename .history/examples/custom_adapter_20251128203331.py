"""Custom context adapter example.

This example shows how to create a custom context adapter
for specialized storage needs (Redis, database, etc.).
"""

from typing import Any

from fastapi import FastAPI

from fastapi_request_context import (
    RequestContextConfig,
    RequestContextMiddleware,
    get_context,
)
from fastapi_request_context.adapters.base import ContextAdapter


class InMemoryAdapter(ContextAdapter):
    """Simple in-memory adapter for demonstration.

    In a real application, you might use Redis, a database,
    or another storage backend.
    """

    def __init__(self) -> None:
        """Initialize the adapter."""
        self._storage: dict[str, Any] = {}

    def set_value(self, key: str, value: Any) -> None:
        """Store a value."""
        self._storage[key] = value
        print(f"  [InMemoryAdapter] Set {key}={value}")

    def get_value(self, key: str) -> Any:
        """Retrieve a value."""
        value = self._storage.get(key)
        print(f"  [InMemoryAdapter] Get {key}={value}")
        return value

    def get_all(self) -> dict[str, Any]:
        """Get all stored values."""
        return dict(self._storage)

    def enter_context(self, initial_values: dict[str, Any]) -> None:
        """Initialize context with values."""
        self._storage = dict(initial_values)
        print(f"  [InMemoryAdapter] Enter context: {initial_values}")

    def exit_context(self) -> None:
        """Clean up context."""
        print(f"  [InMemoryAdapter] Exit context: {self._storage}")
        self._storage.clear()


app = FastAPI()


@app.get("/")
async def root() -> dict[str, Any]:
    """Show current context values."""
    return {
        "request_id": get_context("request_id"),
        "correlation_id": get_context("correlation_id"),
    }


# Create custom adapter
custom_adapter = InMemoryAdapter()

# Configure middleware with custom adapter
config = RequestContextConfig(context_adapter=custom_adapter)
app = RequestContextMiddleware(app, config=config)  # type: ignore[assignment]

if __name__ == "__main__":
    import uvicorn

    print("Starting server with custom adapter at http://localhost:8000")
    print("Watch the console to see adapter calls")
    print("Try: curl http://localhost:8000/")
    uvicorn.run(app, host="0.0.0.0", port=8000)  # noqa: S104
