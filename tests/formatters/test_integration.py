"""Integration tests for formatters with middleware."""

import json
import logging
from typing import Any

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from fastapi_request_context import RequestContextConfig, RequestContextMiddleware, set_context
from fastapi_request_context.formatters import JsonContextFormatter, SimpleContextFormatter


async def test_formatter_integration_with_middleware() -> None:
    """Test formatters work correctly with middleware."""
    app = FastAPI()
    log_records: list[str] = []

    class CaptureHandler(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            log_records.append(self.format(record))

    handler = CaptureHandler()
    handler.setFormatter(JsonContextFormatter())
    logger = logging.getLogger("test_integration")
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

    @app.get("/")
    async def root() -> dict[str, Any]:
        set_context("user_id", 123)
        logger.info("Processing request")
        return {"status": "ok"}

    wrapped = RequestContextMiddleware(app)
    transport = ASGITransport(app=wrapped)  # type: ignore[arg-type]
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await client.get("/")

    assert len(log_records) == 1
    data = json.loads(log_records[0])
    assert data["message"] == "Processing request"
    # Context is nested under "context" key by default
    assert data["context"]["user_id"] == 123
    assert "request_id" in data["context"]

    logger.removeHandler(handler)


async def test_context_logging_adapter_with_json_formatter() -> None:
    """Test context-logging adapter integrates with JsonContextFormatter.

    Verifies that context values appear in the formatted JSON output
    when using the context-logging adapter.
    """
    from context_logging import setup_log_record

    setup_log_record()

    app = FastAPI()
    log_records: list[str] = []

    class CaptureHandler(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            log_records.append(self.format(record))

    handler = CaptureHandler()
    handler.setFormatter(JsonContextFormatter())
    logger = logging.getLogger("test_context_logging_json")
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

    @app.get("/")
    async def root() -> dict[str, Any]:
        set_context("tenant_id", "acme-corp")
        logger.info("Processing with context-logging")
        return {"status": "ok"}

    config = RequestContextConfig(context_adapter="context_logging")
    wrapped = RequestContextMiddleware(app, config=config)
    transport = ASGITransport(app=wrapped)  # type: ignore[arg-type]
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await client.get("/")

    assert len(log_records) == 1
    data = json.loads(log_records[0])
    assert data["message"] == "Processing with context-logging"
    # Context values should be present
    assert "request_id" in data["context"]
    assert "correlation_id" in data["context"]
    assert data["context"]["tenant_id"] == "acme-corp"

    logger.removeHandler(handler)


async def test_context_logging_adapter_with_simple_formatter() -> None:
    """Test context-logging adapter integrates with SimpleContextFormatter.

    Verifies that context values appear in the formatted output string
    when using the context-logging adapter.
    """
    from context_logging import setup_log_record

    setup_log_record()

    app = FastAPI()
    log_records: list[str] = []

    class CaptureHandler(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            log_records.append(self.format(record))

    handler = CaptureHandler()
    handler.setFormatter(SimpleContextFormatter(fmt="%(message)s %(context)s"))
    logger = logging.getLogger("test_context_logging_simple")
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

    @app.get("/")
    async def root() -> dict[str, Any]:
        set_context("user_id", 42)
        logger.info("Hello")
        return {"status": "ok"}

    config = RequestContextConfig(context_adapter="context_logging")
    wrapped = RequestContextMiddleware(app, config=config)
    transport = ASGITransport(app=wrapped)  # type: ignore[arg-type]
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await client.get("/")

    assert len(log_records) == 1
    formatted = log_records[0]
    # Should contain the message and context values
    assert "Hello" in formatted
    assert "request_id=" in formatted
    assert "correlation_id=" in formatted
    assert "user_id=42" in formatted

    logger.removeHandler(handler)
