"""Tests for JsonContextFormatter."""

import json
import logging
import sys

from fastapi_request_context.formatters import JsonContextFormatter


def test_basic_formatting() -> None:
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


def test_includes_context() -> None:
    """Test that context is included in JSON output (nested by default)."""
    from fastapi_request_context.adapters import ContextVarsAdapter
    from fastapi_request_context.context import set_adapter

    adapter = ContextVarsAdapter()
    set_adapter(adapter)
    with adapter:
        adapter.set_value("request_id", "test-123")
        adapter.set_value("user_id", 456)

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

        # Default is nested under "context" key
        assert data["context"]["request_id"] == "test-123"
        assert data["context"]["user_id"] == 456


def test_flat_context_merge() -> None:
    """Test flat context merging when context_key=None."""
    from fastapi_request_context.adapters import ContextVarsAdapter
    from fastapi_request_context.context import set_adapter

    adapter = ContextVarsAdapter()
    set_adapter(adapter)
    with adapter:
        adapter.set_value("request_id", "test-123")
        adapter.set_value("user_id", 456)

        formatter = JsonContextFormatter(context_key=None)
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

        # With context_key=None, context is merged flat
        assert data["request_id"] == "test-123"
        assert data["user_id"] == 456


def test_context_key_nesting() -> None:
    """Test nesting context under a specific key."""
    from fastapi_request_context.adapters import ContextVarsAdapter
    from fastapi_request_context.context import set_adapter

    adapter = ContextVarsAdapter()
    set_adapter(adapter)
    with adapter:
        adapter.set_value("request_id", "test-123")

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


def test_exclude_standard_fields() -> None:
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


def test_exception_formatting() -> None:
    """Test that exceptions are included in output."""
    formatter = JsonContextFormatter()

    try:
        raise ValueError("Test error")  # noqa: TRY301
    except ValueError:
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
