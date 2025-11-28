"""Tests for RequestContextMiddleware."""

from typing import Any
from uuid import UUID

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from fastapi_request_context import (
    RequestContextConfig,
    RequestContextMiddleware,
    StandardContextField,
    get_context,
    get_full_context,
)


@pytest.fixture
def sample_app() -> FastAPI:
    """Create a sample FastAPI app with a test route."""
    app = FastAPI()

    @app.get("/")
    async def root() -> dict[str, Any]:
        return {
            "request_id": get_context(StandardContextField.REQUEST_ID),
            "correlation_id": get_context(StandardContextField.CORRELATION_ID),
        }

    @app.get("/full-context")
    async def full_context() -> dict[str, Any]:
        return get_full_context()

    return app


@pytest.fixture
def wrapped_app(sample_app: FastAPI) -> RequestContextMiddleware:
    """Create the sample app wrapped with middleware."""
    return RequestContextMiddleware(sample_app)


@pytest.fixture
async def test_client(wrapped_app: RequestContextMiddleware) -> AsyncClient:
    """Create async test client."""
    transport = ASGITransport(app=wrapped_app)  # type: ignore[arg-type]
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


async def test_generates_request_id(test_client: AsyncClient) -> None:
    """Test that request_id is always generated."""
    response = await test_client.get("/")
    assert response.status_code == 200

    data = response.json()
    assert data["request_id"] is not None
    # Verify it's a valid UUID
    UUID(data["request_id"])


async def test_generates_correlation_id(test_client: AsyncClient) -> None:
    """Test that correlation_id is generated when not provided."""
    response = await test_client.get("/")
    assert response.status_code == 200

    data = response.json()
    assert data["correlation_id"] is not None
    UUID(data["correlation_id"])


async def test_accepts_correlation_id_from_header(test_client: AsyncClient) -> None:
    """Test that correlation_id is accepted from request header."""
    custom_correlation_id = "test-correlation-123"
    response = await test_client.get(
        "/",
        headers={"X-Correlation-Id": custom_correlation_id},
    )
    assert response.status_code == 200

    data = response.json()
    assert data["correlation_id"] == custom_correlation_id


async def test_ignores_request_id_from_header(test_client: AsyncClient) -> None:
    """Test that request_id from header is ignored (security best practice)."""
    custom_request_id = "should-be-ignored"
    response = await test_client.get(
        "/",
        headers={"X-Request-Id": custom_request_id},
    )
    assert response.status_code == 200

    data = response.json()
    # Should be a new UUID, not the provided value
    assert data["request_id"] != custom_request_id
    UUID(data["request_id"])  # Verify it's a valid UUID


async def test_adds_headers_to_response(test_client: AsyncClient) -> None:
    """Test that request_id and correlation_id are added to response headers."""
    response = await test_client.get("/")
    assert response.status_code == 200

    # Check headers
    assert "x-request-id" in response.headers
    assert "x-correlation-id" in response.headers

    # Verify they match the context values
    data = response.json()
    assert response.headers["x-request-id"] == data["request_id"]
    assert response.headers["x-correlation-id"] == data["correlation_id"]


async def test_unique_request_ids_per_request(test_client: AsyncClient) -> None:
    """Test that each request gets a unique request_id."""
    response1 = await test_client.get("/")
    response2 = await test_client.get("/")

    data1 = response1.json()
    data2 = response2.json()

    assert data1["request_id"] != data2["request_id"]


async def test_correlation_id_case_insensitive(test_client: AsyncClient) -> None:
    """Test that correlation_id header is case-insensitive."""
    custom_correlation_id = "test-correlation-lowercase"

    response = await test_client.get(
        "/",
        headers={"x-correlation-id": custom_correlation_id},
    )
    assert response.status_code == 200

    data = response.json()
    assert data["correlation_id"] == custom_correlation_id


async def test_full_context_includes_both_ids(test_client: AsyncClient) -> None:
    """Test that full context includes both request_id and correlation_id."""
    response = await test_client.get("/full-context")
    assert response.status_code == 200

    data = response.json()
    assert "request_id" in data
    assert "correlation_id" in data


async def test_custom_id_generator() -> None:
    """Test custom ID generator functions."""
    counter = {"value": 0}

    def custom_request_id() -> str:
        counter["value"] += 1
        return f"req-{counter['value']}"

    def custom_correlation_id() -> str:
        return "static-correlation"

    app = FastAPI()

    @app.get("/")
    async def root() -> dict[str, Any]:
        return {
            "request_id": get_context(StandardContextField.REQUEST_ID),
            "correlation_id": get_context(StandardContextField.CORRELATION_ID),
        }

    config = RequestContextConfig(
        request_id_generator=custom_request_id,
        correlation_id_generator=custom_correlation_id,
    )
    wrapped = RequestContextMiddleware(app, config=config)

    transport = ASGITransport(app=wrapped)  # type: ignore[arg-type]
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response1 = await client.get("/")
        response2 = await client.get("/")

    data1 = response1.json()
    data2 = response2.json()

    assert data1["request_id"] == "req-1"
    assert data2["request_id"] == "req-2"
    assert data1["correlation_id"] == "static-correlation"


async def test_custom_header_names() -> None:
    """Test custom header names configuration."""
    app = FastAPI()

    @app.get("/")
    async def root() -> dict[str, str]:
        return {"status": "ok"}

    config = RequestContextConfig(
        request_id_header="X-Custom-Request-Id",
        correlation_id_header="X-Custom-Correlation-Id",
    )
    wrapped = RequestContextMiddleware(app, config=config)

    transport = ASGITransport(app=wrapped)  # type: ignore[arg-type]
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/")

    assert "x-custom-request-id" in response.headers
    assert "x-custom-correlation-id" in response.headers


async def test_disable_response_headers() -> None:
    """Test disabling response headers."""
    app = FastAPI()

    @app.get("/")
    async def root() -> dict[str, str]:
        return {"status": "ok"}

    config = RequestContextConfig(add_response_headers=False)
    wrapped = RequestContextMiddleware(app, config=config)

    transport = ASGITransport(app=wrapped)  # type: ignore[arg-type]
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/")

    assert "x-request-id" not in response.headers
    assert "x-correlation-id" not in response.headers


async def test_scope_type_filtering() -> None:
    """Test that non-http scope types pass through unchanged."""
    app = FastAPI()

    @app.get("/")
    async def root() -> dict[str, str]:
        return {"status": "ok"}

    config = RequestContextConfig(scope_types={"http"})  # Only http, not websocket
    wrapped = RequestContextMiddleware(app, config=config)

    transport = ASGITransport(app=wrapped)  # type: ignore[arg-type]
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/")

    # HTTP should work
    assert response.status_code == 200


async def test_adapter_string_contextvars() -> None:
    """Test that 'contextvars' string works as adapter config."""
    app = FastAPI()

    @app.get("/")
    async def root() -> dict[str, Any]:
        return {"request_id": get_context(StandardContextField.REQUEST_ID)}

    config = RequestContextConfig(context_adapter="contextvars")
    wrapped = RequestContextMiddleware(app, config=config)

    transport = ASGITransport(app=wrapped)  # type: ignore[arg-type]
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/")

    assert response.status_code == 200
    assert response.json()["request_id"] is not None


async def test_adapter_string_context_logging() -> None:
    """Test that 'context_logging' string works as adapter config."""
    app = FastAPI()

    @app.get("/")
    async def root() -> dict[str, Any]:
        return {"request_id": get_context(StandardContextField.REQUEST_ID)}

    config = RequestContextConfig(context_adapter="context_logging")
    wrapped = RequestContextMiddleware(app, config=config)

    transport = ASGITransport(app=wrapped)  # type: ignore[arg-type]
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/")

    assert response.status_code == 200
    assert response.json()["request_id"] is not None


async def test_adapter_string_invalid() -> None:
    """Test that invalid adapter string raises ValueError."""
    app = FastAPI()

    config = RequestContextConfig(context_adapter="invalid")  # type: ignore[arg-type]

    with pytest.raises(ValueError, match="Unknown adapter"):
        RequestContextMiddleware(app, config=config)


async def test_non_http_scope_passes_through() -> None:
    """Test that non-HTTP scope types pass through without processing."""

    async def mock_app(
        scope: dict[str, Any],
        receive: Any,
        send: Any,
    ) -> None:
        # Just verify it was called
        await send({"type": "lifespan.startup.complete"})

    config = RequestContextConfig(scope_types={"http"})
    wrapped = RequestContextMiddleware(mock_app, config=config)

    received_messages: list[dict[str, Any]] = []

    async def mock_send(message: dict[str, Any]) -> None:
        received_messages.append(message)

    # Simulate a lifespan scope (not http)
    await wrapped({"type": "lifespan"}, lambda: None, mock_send)

    # Should have passed through to mock_app
    assert len(received_messages) == 1
    assert received_messages[0]["type"] == "lifespan.startup.complete"
