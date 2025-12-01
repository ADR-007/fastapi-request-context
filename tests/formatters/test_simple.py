"""Tests for SimpleContextFormatter."""

import logging

from fastapi_request_context.formatters import SimpleContextFormatter


def test_basic_formatting() -> None:
    """Test basic local log formatting."""
    formatter = SimpleContextFormatter(fmt="%(levelname)s %(context)s %(message)s")
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


def test_includes_context() -> None:
    """Test that context is included in output."""
    from fastapi_request_context.adapters import ContextVarsAdapter
    from fastapi_request_context.context import set_adapter

    adapter = ContextVarsAdapter()
    set_adapter(adapter)
    adapter.enter_context({"request_id": "test-123", "user_id": 456})

    try:
        formatter = SimpleContextFormatter(fmt="%(context)s %(message)s")
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


def test_shorten_fields() -> None:
    """Test shortening of specified fields."""
    from fastapi_request_context.adapters import ContextVarsAdapter
    from fastapi_request_context.context import set_adapter

    adapter = ContextVarsAdapter()
    set_adapter(adapter)
    adapter.enter_context({"request_id": "12345678901234567890"})

    try:
        formatter = SimpleContextFormatter(
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
        assert "request_id=12345678…" in output
        assert "12345678901234567890" not in output
    finally:
        adapter.exit_context()


def test_hidden_fields() -> None:
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
        formatter = SimpleContextFormatter(
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


def test_empty_context() -> None:
    """Test formatting when context is empty."""
    from fastapi_request_context.adapters import ContextVarsAdapter
    from fastapi_request_context.context import set_adapter

    adapter = ContextVarsAdapter()
    set_adapter(adapter)
    adapter.enter_context({})

    try:
        formatter = SimpleContextFormatter(fmt="%(context)s %(message)s")
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


def test_all_fields_hidden() -> None:
    """Test formatting when all fields are hidden."""
    from fastapi_request_context.adapters import ContextVarsAdapter
    from fastapi_request_context.context import set_adapter

    adapter = ContextVarsAdapter()
    set_adapter(adapter)
    adapter.enter_context({"request_id": "test-123", "user_id": "456"})

    try:
        formatter = SimpleContextFormatter(
            fmt="%(context)s %(message)s",
            hidden_fields={"request_id", "user_id"},
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
        # Should return empty string for context when all hidden
        assert "[]" not in output
        assert "request_id" not in output
        assert "user_id" not in output
        assert "Test message" in output
    finally:
        adapter.exit_context()


def test_default_format() -> None:
    """Test default format string when none provided."""
    formatter = SimpleContextFormatter()
    assert formatter._fmt is not None
    assert "%(context)s" in formatter._fmt
