"""Integration tests for formatters with middleware."""

import json
import logging
from typing import Any

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from fastapi_request_context import RequestContextMiddleware, set_context
from fastapi_request_context.formatters import JsonContextFormatter


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
