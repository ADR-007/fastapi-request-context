"""Tests for ContextLoggingAdapter."""

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
