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


def test_exception_gets_context_added() -> None:
    """Test that exceptions get context appended to args."""
    adapter = ContextVarsAdapter()
    exc = None

    try:
        with adapter:
            adapter.set_value("request_id", "123")
            adapter.set_value("user_id", "456")
            raise ValueError("test error")
    except ValueError as e:
        exc = e

    assert exc is not None
    assert exc.args == ("test error", {"request_id": "123", "user_id": "456"})
    assert getattr(exc, "__context_logging__", False) is True


def test_exception_not_modified_if_already_has_context() -> None:
    """Test that exceptions with __context_logging__ are not modified."""
    adapter = ContextVarsAdapter()
    exc = None

    try:
        with adapter:
            adapter.set_value("request_id", "123")
            error = ValueError("test error")
            error.__context_logging__ = True  # type: ignore[attr-defined]
            raise error
    except ValueError as e:
        exc = e

    assert exc is not None
    # args should remain unchanged
    assert exc.args == ("test error",)


def test_exception_not_modified_if_context_empty() -> None:
    """Test that exceptions are not modified if context is empty."""
    adapter = ContextVarsAdapter()
    exc = None

    try:
        with adapter:
            # No context values set
            raise ValueError("test error")
    except ValueError as e:
        exc = e

    assert exc is not None
    assert exc.args == ("test error",)
    assert getattr(exc, "__context_logging__", False) is False
