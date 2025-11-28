"""Tests for logging formatters."""

import json
import logging
from typing import Any

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from fastapi_request_context import (
    RequestContextMiddleware,
    set_context,
)
from fastapi_request_context.formatters import JsonContextFormatter, SimpleContextFormatter


class TestJsonContextFormatter:
    """Tests for JsonContextFormatter."""

    def test_basic_formatting(self) -> None:
        """Test basic JSON log formatting."""
        formatter = JsonContextFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        output = formatter.format(record)
        data = json.loads(output)

        assert data["message"] == "Test message"
        assert data["level"] == "INFO"
        assert data["logger"] == "test"
        assert "timestamp" in data

    def test_includes_context(self) -> None:
        """Test that context is included in JSON output."""
        from fastapi_request_context.adapters import ContextVarsAdapter
        from fastapi_request_context.context import set_adapter

        adapter = ContextVarsAdapter()
        set_adapter(adapter)
        adapter.enter_context({"request_id": "test-123", "user_id": 456})

        try:
            formatter = JsonContextFormatter()
            record = logging.LogRecord(
                name="test",
                level=logging.INFO,
                pathname="test.py",
                lineno=1,
                msg="Test message",
                args=(),
                exc_info=None,
            )

            output = formatter.format(record)
            data = json.loads(output)

            assert data["request_id"] == "test-123"
            assert data["user_id"] == 456
        finally:
            adapter.exit_context()

    def test_context_key_nesting(self) -> None:
        """Test nesting context under a specific key."""
        from fastapi_request_context.adapters import ContextVarsAdapter
        from fastapi_request_context.context import set_adapter

        adapter = ContextVarsAdapter()
        set_adapter(adapter)
        adapter.enter_context({"request_id": "test-123"})

        try:
            formatter = JsonContextFormatter(context_key="context")
            record = logging.LogRecord(
                name="test",
                level=logging.INFO,
                pathname="test.py",
                lineno=1,
                msg="Test message",
                args=(),
                exc_info=None,
            )

            output = formatter.format(record)
            data = json.loads(output)

            assert "context" in data
            assert data["context"]["request_id"] == "test-123"
        finally:
            adapter.exit_context()

    def test_exclude_standard_fields(self) -> None:
        """Test excluding standard fields from output."""
        formatter = JsonContextFormatter(include_standard_fields=False)
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        output = formatter.format(record)
        data = json.loads(output)

        assert "message" in data
        assert "level" not in data
        assert "logger" not in data
        assert "timestamp" not in data

    def test_exception_formatting(self) -> None:
        """Test that exceptions are included in output."""
        formatter = JsonContextFormatter()

        try:
            raise ValueError("Test error")  # noqa: TRY301
        except ValueError:
            import sys

            exc_info = sys.exc_info()

        record = logging.LogRecord(
            name="test",
            level=logging.ERROR,
            pathname="test.py",
            lineno=1,
            msg="Error occurred",
            args=(),
            exc_info=exc_info,
        )

        output = formatter.format(record)
        data = json.loads(output)

        assert "exception" in data
        assert "ValueError" in data["exception"]


class TestLocalContextFormatter:
    """Tests for LocalContextFormatter."""

    def test_basic_formatting(self) -> None:
        """Test basic local log formatting."""
        formatter = LocalContextFormatter(fmt="%(levelname)s %(context)s %(message)s")
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        output = formatter.format(record)
        assert "INFO" in output
        assert "Test message" in output

    def test_includes_context(self) -> None:
        """Test that context is included in output."""
        from fastapi_request_context.adapters import ContextVarsAdapter
        from fastapi_request_context.context import set_adapter

        adapter = ContextVarsAdapter()
        set_adapter(adapter)
        adapter.enter_context({"request_id": "test-123", "user_id": 456})

        try:
            formatter = LocalContextFormatter(fmt="%(context)s %(message)s")
            record = logging.LogRecord(
                name="test",
                level=logging.INFO,
                pathname="test.py",
                lineno=1,
                msg="Test message",
                args=(),
                exc_info=None,
            )

            output = formatter.format(record)
            assert "request_id=test-123" in output
            assert "user_id=456" in output
        finally:
            adapter.exit_context()

    def test_shorten_fields(self) -> None:
        """Test shortening of specified fields."""
        from fastapi_request_context.adapters import ContextVarsAdapter
        from fastapi_request_context.context import set_adapter

        adapter = ContextVarsAdapter()
        set_adapter(adapter)
        adapter.enter_context({"request_id": "12345678901234567890"})

        try:
            formatter = LocalContextFormatter(
                fmt="%(context)s %(message)s",
                shorten_fields={"request_id"},
                shorten_length=8,
            )
            record = logging.LogRecord(
                name="test",
                level=logging.INFO,
                pathname="test.py",
                lineno=1,
                msg="Test message",
                args=(),
                exc_info=None,
            )

            output = formatter.format(record)
            assert "request_id=12345678" in output
            assert "12345678901234567890" not in output
        finally:
            adapter.exit_context()

    def test_hidden_fields(self) -> None:
        """Test hiding of specified fields."""
        from fastapi_request_context.adapters import ContextVarsAdapter
        from fastapi_request_context.context import set_adapter

        adapter = ContextVarsAdapter()
        set_adapter(adapter)
        adapter.enter_context(
            {
                "request_id": "shown",
                "correlation_id": "hidden",
            },
        )

        try:
            formatter = LocalContextFormatter(
                fmt="%(context)s %(message)s",
                hidden_fields={"correlation_id"},
            )
            record = logging.LogRecord(
                name="test",
                level=logging.INFO,
                pathname="test.py",
                lineno=1,
                msg="Test message",
                args=(),
                exc_info=None,
            )

            output = formatter.format(record)
            assert "request_id=shown" in output
            assert "correlation_id" not in output
        finally:
            adapter.exit_context()

    def test_empty_context(self) -> None:
        """Test formatting when context is empty."""
        from fastapi_request_context.adapters import ContextVarsAdapter
        from fastapi_request_context.context import set_adapter

        adapter = ContextVarsAdapter()
        set_adapter(adapter)
        adapter.enter_context({})

        try:
            formatter = LocalContextFormatter(fmt="%(context)s %(message)s")
            record = logging.LogRecord(
                name="test",
                level=logging.INFO,
                pathname="test.py",
                lineno=1,
                msg="Test message",
                args=(),
                exc_info=None,
            )

            output = formatter.format(record)
            # Should not have empty brackets
            assert "[]" not in output
            assert "Test message" in output
        finally:
            adapter.exit_context()

    def test_default_format(self) -> None:
        """Test default format string when none provided."""
        formatter = LocalContextFormatter()
        assert formatter._fmt is not None
        assert "%(context)s" in formatter._fmt


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
    assert data["user_id"] == 123
    assert "request_id" in data

    logger.removeHandler(handler)
