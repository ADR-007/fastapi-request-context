"""Tests for context adapters."""

import pytest

from fastapi_request_context.adapters import (
    ContextAdapter,
    ContextLoggingAdapter,
    ContextVarsAdapter,
)


class TestContextVarsAdapter:
    """Tests for ContextVarsAdapter."""

    def test_set_and_get_value(self) -> None:
        """Test basic set and get operations."""
        adapter = ContextVarsAdapter()
        adapter.enter_context({})

        try:
            adapter.set_value("key1", "value1")
            assert adapter.get_value("key1") == "value1"
        finally:
            adapter.exit_context()

    def test_get_nonexistent_value(self) -> None:
        """Test getting a nonexistent key returns None."""
        adapter = ContextVarsAdapter()
        adapter.enter_context({})

        try:
            assert adapter.get_value("nonexistent") is None
        finally:
            adapter.exit_context()

    def test_get_all(self) -> None:
        """Test getting all values."""
        adapter = ContextVarsAdapter()
        adapter.enter_context({"initial": "value"})

        try:
            adapter.set_value("key1", "value1")
            adapter.set_value("key2", "value2")

            all_values = adapter.get_all()
            assert all_values == {
                "initial": "value",
                "key1": "value1",
                "key2": "value2",
            }
        finally:
            adapter.exit_context()

    def test_enter_context_with_initial_values(self) -> None:
        """Test entering context with initial values."""
        adapter = ContextVarsAdapter()
        adapter.enter_context({"request_id": "123", "correlation_id": "456"})

        try:
            assert adapter.get_value("request_id") == "123"
            assert adapter.get_value("correlation_id") == "456"
        finally:
            adapter.exit_context()

    def test_exit_context_clears_values(self) -> None:
        """Test that exiting context clears values."""
        adapter = ContextVarsAdapter()

        adapter.enter_context({"key": "value"})
        assert adapter.get_value("key") == "value"
        adapter.exit_context()

        # After exit, context is empty
        assert adapter.get_value("key") is None

    def test_get_all_returns_copy(self) -> None:
        """Test that get_all returns a copy, not the original dict."""
        adapter = ContextVarsAdapter()
        adapter.enter_context({"key": "value"})

        try:
            all_values = adapter.get_all()
            all_values["new_key"] = "new_value"

            # Original should be unchanged
            assert adapter.get_value("new_key") is None
        finally:
            adapter.exit_context()

    def test_implements_protocol(self) -> None:
        """Test that adapter implements ContextAdapter protocol."""
        adapter = ContextVarsAdapter()
        assert isinstance(adapter, ContextAdapter)


class TestContextLoggingAdapter:
    """Tests for ContextLoggingAdapter."""

    def test_set_and_get_value(self) -> None:
        """Test basic set and get operations."""
        adapter = ContextLoggingAdapter()
        adapter.enter_context({})

        try:
            adapter.set_value("key1", "value1")
            assert adapter.get_value("key1") == "value1"
        finally:
            adapter.exit_context()

    def test_get_nonexistent_value(self) -> None:
        """Test getting a nonexistent key returns None."""
        adapter = ContextLoggingAdapter()
        adapter.enter_context({})

        try:
            assert adapter.get_value("nonexistent") is None
        finally:
            adapter.exit_context()

    def test_get_all(self) -> None:
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

    def test_enter_context_with_initial_values(self) -> None:
        """Test entering context with initial values."""
        adapter = ContextLoggingAdapter()
        adapter.enter_context({"request_id": "123"})

        try:
            assert adapter.get_value("request_id") == "123"
        finally:
            adapter.exit_context()

    def test_implements_protocol(self) -> None:
        """Test that adapter implements ContextAdapter protocol."""
        adapter = ContextLoggingAdapter()
        assert isinstance(adapter, ContextAdapter)


class TestContextLoggingAdapterImportError:
    """Tests for ContextLoggingAdapter when context-logging is not installed."""

    def test_import_error_message(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that helpful error message is shown when context-logging missing."""
        import sys

        # Remove context_logging from modules to simulate it not being installed
        original_modules = dict(sys.modules)
        sys.modules["context_logging"] = None  # type: ignore[assignment]

        try:
            # Need to reimport to trigger the import check
            import importlib

            from fastapi_request_context.adapters import context_logging

            importlib.reload(context_logging)

            with pytest.raises(ImportError, match="context-logging is required"):
                context_logging.ContextLoggingAdapter()
        finally:
            sys.modules.update(original_modules)
