"""Pytest configuration and fixtures."""

from collections.abc import AsyncGenerator
from typing import Any

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from fastapi_request_context import RequestContextMiddleware


@pytest.fixture
def app() -> FastAPI:
    """Create a basic FastAPI app."""
    return FastAPI()


@pytest.fixture
def app_with_middleware(app: FastAPI) -> Any:
    """Create a FastAPI app wrapped with RequestContextMiddleware."""
    return RequestContextMiddleware(app)


@pytest.fixture
async def client(app_with_middleware: Any) -> AsyncGenerator[AsyncClient, None]:
    """Create an async test client."""
    transport = ASGITransport(app=app_with_middleware)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
