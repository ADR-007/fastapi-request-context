"""Tests for ContextVarsAdapter."""

from fastapi_request_context.adapters import ContextAdapter, ContextVarsAdapter


def test_set_and_get_value() -> None:
    """Test basic set and get operations."""
    adapter = ContextVarsAdapter()
    with adapter:
        adapter.set_value("key1", "value1")
        assert adapter.get_value("key1") == "value1"


def test_get_nonexistent_value() -> None:
    """Test getting a nonexistent key returns None."""
    adapter = ContextVarsAdapter()
    with adapter:
        assert adapter.get_value("nonexistent") is None


def test_get_all() -> None:
    """Test getting all values."""
    adapter = ContextVarsAdapter()
    with adapter:
        adapter.set_value("initial", "value")
        adapter.set_value("key1", "value1")
        adapter.set_value("key2", "value2")

        all_values = adapter.get_all()
        assert all_values == {
            "initial": "value",
            "key1": "value1",
            "key2": "value2",
        }


def test_context_manager_sets_values() -> None:
    """Test that context manager allows setting values."""
    adapter = ContextVarsAdapter()
    with adapter:
        adapter.set_value("request_id", "123")
        adapter.set_value("correlation_id", "456")
        assert adapter.get_value("request_id") == "123"
        assert adapter.get_value("correlation_id") == "456"


def test_exit_clears_values() -> None:
    """Test that exiting context clears values."""
    adapter = ContextVarsAdapter()

    with adapter:
        adapter.set_value("key", "value")
        assert adapter.get_value("key") == "value"

    # After exit, context is empty
    assert adapter.get_value("key") is None


def test_get_all_returns_copy() -> None:
    """Test that get_all returns a copy, not the original dict."""
    adapter = ContextVarsAdapter()
    with adapter:
        adapter.set_value("key", "value")
        all_values = adapter.get_all()
        all_values["new_key"] = "new_value"

        # Original should be unchanged
        assert adapter.get_value("new_key") is None


def test_implements_protocol() -> None:
    """Test that adapter implements ContextAdapter protocol."""
    adapter = ContextVarsAdapter()
    assert isinstance(adapter, ContextAdapter)


def test_set_value_without_context() -> None:
    """Test that set_value does nothing when context not entered."""
    adapter = ContextVarsAdapter()
    # Should not raise, just do nothing
    adapter.set_value("key", "value")
    # Value should be None since context was never entered
    assert adapter.get_value("key") is None
