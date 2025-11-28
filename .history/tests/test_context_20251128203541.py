"""Tests for context functions."""

import sys

if sys.version_info >= (3, 11):
    from enum import StrEnum
else:
    from enum import Enum

    class StrEnum(str, Enum):
        pass

from typing import Any

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from fastapi_request_context import (
    RequestContextMiddleware,
    StandardContextField,
    get_context,
    get_full_context,
    set_context,
)


class CustomField(StrEnum):
    """Custom context field for testing."""

    USER_ID = "user_id"
    ORG_ID = "org_id"


@pytest.fixture
def app_with_custom_fields() -> FastAPI:
    """Create app that sets and gets custom fields."""
    app = FastAPI()

    @app.get("/set-and-get")
    async def set_and_get() -> dict[str, Any]:
        # Set custom fields
        set_context(CustomField.USER_ID, 123)
        set_context(CustomField.ORG_ID, "org-456")
        set_context("string_key", "string_value")

        # Get them back
        return {
            "user_id": get_context(CustomField.USER_ID),
            "org_id": get_context(CustomField.ORG_ID),
            "string_key": get_context("string_key"),
            "request_id": get_context(StandardContextField.REQUEST_ID),
        }

    @app.get("/full-context")
    async def full_context() -> dict[str, Any]:
        set_context(CustomField.USER_ID, 999)
        return get_full_context()

    return app


@pytest.fixture
async def custom_client(app_with_custom_fields: FastAPI) -> AsyncClient:
    """Create test client for custom fields app."""
    wrapped = RequestContextMiddleware(app_with_custom_fields)
    transport = ASGITransport(app=wrapped)  # type: ignore[arg-type]
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


async def test_set_and_get_enum_fields(custom_client: AsyncClient) -> None:
    """Test setting and getting context using StrEnum fields."""
    response = await custom_client.get("/set-and-get")
    assert response.status_code == 200

    data = response.json()
    assert data["user_id"] == 123
    assert data["org_id"] == "org-456"


async def test_set_and_get_string_keys(custom_client: AsyncClient) -> None:
    """Test setting and getting context using string keys."""
    response = await custom_client.get("/set-and-get")
    assert response.status_code == 200

    data = response.json()
    assert data["string_key"] == "string_value"


async def test_standard_fields_available(custom_client: AsyncClient) -> None:
    """Test that standard fields are always available."""
    response = await custom_client.get("/set-and-get")
    assert response.status_code == 200

    data = response.json()
    assert data["request_id"] is not None


async def test_full_context_includes_all(custom_client: AsyncClient) -> None:
    """Test that get_full_context includes all fields."""
    response = await custom_client.get("/full-context")
    assert response.status_code == 200

    data = response.json()
    assert "request_id" in data
    assert "correlation_id" in data
    assert "user_id" in data
    assert data["user_id"] == 999


async def test_get_nonexistent_key(custom_client: AsyncClient) -> None:
    """Test that getting a nonexistent key returns None."""
    app = FastAPI()

    @app.get("/")
    async def root() -> dict[str, Any]:
        return {"value": get_context("nonexistent")}

    wrapped = RequestContextMiddleware(app)
    transport = ASGITransport(app=wrapped)  # type: ignore[arg-type]
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/")

    assert response.status_code == 200
    assert response.json()["value"] is None


async def test_context_isolation_between_requests() -> None:
    """Test that context is isolated between concurrent requests."""
    app = FastAPI()
    import asyncio

    @app.get("/slow/{value}")
    async def slow_route(value: str) -> dict[str, Any]:
        set_context("my_value", value)
        await asyncio.sleep(0.01)  # Small delay
        return {
            "set_value": value,
            "got_value": get_context("my_value"),
        }

    wrapped = RequestContextMiddleware(app)
    transport = ASGITransport(app=wrapped)  # type: ignore[arg-type]
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Run two requests concurrently
        responses = await asyncio.gather(
            client.get("/slow/first"),
            client.get("/slow/second"),
        )

    # Each request should see its own value
    for response in responses:
        data = response.json()
        assert data["set_value"] == data["got_value"]


async def test_set_various_value_types(custom_client: AsyncClient) -> None:
    """Test setting various types of values."""
    app = FastAPI()

    @app.get("/")
    async def root() -> dict[str, Any]:
        set_context("int_val", 42)
        set_context("float_val", 3.14)
        set_context("bool_val", True)
        set_context("list_val", [1, 2, 3])
        set_context("dict_val", {"key": "value"})
        set_context("none_val", None)

        return {
            "int_val": get_context("int_val"),
            "float_val": get_context("float_val"),
            "bool_val": get_context("bool_val"),
            "list_val": get_context("list_val"),
            "dict_val": get_context("dict_val"),
            "none_val": get_context("none_val"),
        }

    wrapped = RequestContextMiddleware(app)
    transport = ASGITransport(app=wrapped)  # type: ignore[arg-type]
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/")

    data = response.json()
    assert data["int_val"] == 42
    assert data["float_val"] == 3.14
    assert data["bool_val"] is True
    assert data["list_val"] == [1, 2, 3]
    assert data["dict_val"] == {"key": "value"}
    assert data["none_val"] is None
