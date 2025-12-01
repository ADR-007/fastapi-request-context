"""Tests for ContextLoggingAdapter."""

import logging
import sys

import pytest

from fastapi_request_context.adapters import ContextAdapter, ContextLoggingAdapter


def test_set_and_get_value() -> None:
    """Test basic set and get operations."""
    adapter = ContextLoggingAdapter()
    adapter.enter_context({})

    try:
        adapter.set_value("key1", "value1")
        assert adapter.get_value("key1") == "value1"
    finally:
        adapter.exit_context()


def test_get_nonexistent_value() -> None:
    """Test getting a nonexistent key returns None."""
    adapter = ContextLoggingAdapter()
    adapter.enter_context({})

    try:
        assert adapter.get_value("nonexistent") is None
    finally:
        adapter.exit_context()


def test_get_all() -> None:
    """Test getting all values."""
    adapter = ContextLoggingAdapter()
    adapter.enter_context({"initial": "value"})

    try:
        adapter.set_value("key1", "value1")

        all_values = adapter.get_all()
        assert "initial" in all_values
        assert "key1" in all_values
    finally:
        adapter.exit_context()


def test_enter_context_with_initial_values() -> None:
    """Test entering context with initial values."""
    adapter = ContextLoggingAdapter()
    adapter.enter_context({"request_id": "123"})

    try:
        assert adapter.get_value("request_id") == "123"
    finally:
        adapter.exit_context()


def test_implements_protocol() -> None:
    """Test that adapter implements ContextAdapter protocol."""
    adapter = ContextLoggingAdapter()
    assert isinstance(adapter, ContextAdapter)


def test_exit_context_without_enter() -> None:
    """Test that exit_context does nothing when not entered."""
    adapter = ContextLoggingAdapter()
    # Should not raise, just do nothing
    adapter.exit_context()


def test_import_error_message(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that helpful error message is shown when context-logging missing."""
    import importlib

    from fastapi_request_context.adapters import context_logging

    # Remove context_logging from modules to simulate it not being installed
    original_modules = dict(sys.modules)
    sys.modules["context_logging"] = None  # type: ignore[assignment]

    try:
        importlib.reload(context_logging)

        with pytest.raises(ImportError, match="context-logging is required"):
            context_logging.ContextLoggingAdapter()
    finally:
        sys.modules.update(original_modules)


def test_context_injected_into_log_records(caplog: pytest.LogCaptureFixture) -> None:
    """Test that context values are automatically injected into log records.

    The context-logging library requires setup_log_record() to be called
    to enable automatic context injection. This test verifies that context
    values set via ContextLoggingAdapter appear in log records via record.context.
    """
    from context_logging import setup_log_record

    setup_log_record()

    adapter = ContextLoggingAdapter()
    adapter.enter_context({"request_id": "test-request-123", "user_id": "user-456"})

    try:
        logger = logging.getLogger("test_context_logging")
        with caplog.at_level(logging.INFO):
            logger.info("Test message")

        assert len(caplog.records) == 1
        record = caplog.records[0]

        # context-logging injects context into record.context attribute
        assert hasattr(record, "context")
        assert record.context["request_id"] == "test-request-123"  # type: ignore[attr-defined]
        assert record.context["user_id"] == "user-456"  # type: ignore[attr-defined]
    finally:
        adapter.exit_context()


def test_context_injection_with_dynamic_values(caplog: pytest.LogCaptureFixture) -> None:
    """Test that dynamically set context values appear in log records.

    Verifies that values added after entering the context (via set_value)
    also appear in log records via record.context.
    """
    from context_logging import setup_log_record

    setup_log_record()

    adapter = ContextLoggingAdapter()
    adapter.enter_context({"request_id": "req-001"})

    try:
        logger = logging.getLogger("test_context_logging_dynamic")

        # Set additional context after entering
        adapter.set_value("correlation_id", "corr-xyz")
        adapter.set_value("tenant_id", "tenant-abc")

        with caplog.at_level(logging.INFO):
            logger.info("Processing request")

        assert len(caplog.records) == 1
        record = caplog.records[0]

        # Both initial and dynamic values should be in record.context
        assert hasattr(record, "context")
        assert record.context["request_id"] == "req-001"  # type: ignore[attr-defined]
        assert record.context["correlation_id"] == "corr-xyz"  # type: ignore[attr-defined]
        assert record.context["tenant_id"] == "tenant-abc"  # type: ignore[attr-defined]
    finally:
        adapter.exit_context()
