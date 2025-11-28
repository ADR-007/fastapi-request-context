"""Pytest configuration and fixtures."""

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from fastapi_request_context import RequestContextMiddleware


@pytest.fixture
def app() -> FastAPI:
    """Create a basic FastAPI app."""
    return FastAPI()


@pytest.fixture
def app_with_middleware(app: FastAPI) -> FastAPI:
    """Create a FastAPI app wrapped with RequestContextMiddleware."""
    return RequestContextMiddleware(app)  # type: ignore[return-value]


@pytest.fixture
async def client(app_with_middleware: FastAPI) -> AsyncClient:
    """Create an async test client."""
    transport = ASGITransport(app=app_with_middleware)  # type: ignore[arg-type]
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
