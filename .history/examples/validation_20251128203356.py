"""Validation utilities example.

This example shows how to use validation utilities to check
that all routes and dependencies are async.

Context variables only work correctly with async code. Sync routes
running in thread pools won't have access to request context.
"""

from contextlib import asynccontextmanager
from typing import Any, AsyncIterator

from fastapi import Depends, FastAPI

from fastapi_request_context import RequestContextMiddleware, get_context
from fastapi_request_context.validation import check_routes_and_dependencies_are_async


# Example: Async dependency (correct)
async def async_dependency() -> int:
    """This dependency is async - context will work correctly."""
    return 42


# Example: Sync dependency (will generate warning)
def sync_dependency() -> str:
    """This dependency is sync - may have context issues."""
    return "sync value"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Lifespan context that validates routes on startup."""
    # Check all routes and dependencies are async
    warnings = check_routes_and_dependencies_are_async(app)

    if warnings:
        print("\n⚠️  Sync routes/dependencies detected:")
        for warning in warnings:
            print(f"   - {warning}")
        print("\nContext propagation may not work correctly for these.")
        print("Consider making them async.\n")
    else:
        print("\n✅ All routes and dependencies are async!\n")

    yield


app = FastAPI(lifespan=lifespan)


# Async route (correct)
@app.get("/async-route")
async def async_route(value: int = Depends(async_dependency)) -> dict[str, Any]:
    """This route is async - context works correctly."""
    return {
        "status": "ok",
        "value": value,
        "request_id": get_context("request_id"),
    }


# Sync route (will generate warning)
@app.get("/sync-route")
def sync_route() -> dict[str, Any]:
    """This route is sync - context may not work."""
    # WARNING: get_context() may return None in sync routes!
    return {
        "status": "ok",
        "request_id": get_context("request_id"),  # May be None!
    }


# Route with sync dependency (will generate warning)
@app.get("/sync-dep")
async def route_with_sync_dep(value: str = Depends(sync_dependency)) -> dict[str, Any]:
    """This route has a sync dependency - may have issues."""
    return {
        "status": "ok",
        "value": value,
    }


# Apply middleware
app = RequestContextMiddleware(app)  # type: ignore[assignment]

if __name__ == "__main__":
    import uvicorn

    print("Starting server at http://localhost:8000")
    print("Watch startup output for validation warnings")
    uvicorn.run(app, host="0.0.0.0", port=8000)  # noqa: S104
