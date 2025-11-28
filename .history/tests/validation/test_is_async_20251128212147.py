"""Tests for is_async function."""

from fastapi_request_context.validation import is_async


def test_async_function() -> None:
    """Test that async functions are detected."""

    async def async_func() -> None:
        pass

    assert is_async(async_func) is True


def test_sync_function() -> None:
    """Test that sync functions are detected."""

    def sync_func() -> None:
        pass

    assert is_async(sync_func) is False


def test_async_callable_class() -> None:
    """Test that classes with async __call__ are detected."""

    class AsyncCallable:
        async def __call__(self) -> None:
            pass

    assert is_async(AsyncCallable()) is True


def test_sync_callable_class() -> None:
    """Test that classes with sync __call__ are detected."""

    class SyncCallable:
        def __call__(self) -> None:
            pass

    assert is_async(SyncCallable()) is False


def test_lambda() -> None:
    """Test that lambdas are detected as sync."""
    assert is_async(lambda: None) is False
