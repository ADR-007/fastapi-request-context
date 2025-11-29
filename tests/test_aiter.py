"""Tests for aiter_with_logging_context."""

from collections.abc import AsyncIterator

from context_logging import Context, current_context

from fastapi_request_context import aiter_with_logging_context


async def test_aiter_with_logging_context() -> None:
    """Test that context is preserved during iteration."""

    async def func() -> AsyncIterator[int]:
        yield current_context.get("var")

    with Context(var=42):
        result_aiter = aiter_with_logging_context(func)

    result = [r async for r in result_aiter()]
    assert result == [42]


async def test_aiter_with_logging_context_awaitable() -> None:
    """Test that awaitable async iterators work."""

    async def as_aiter(items: list[int]) -> AsyncIterator[int]:
        for item in items:
            yield item

    async def func() -> AsyncIterator[int]:
        return as_aiter([current_context.get("var")])

    with Context(var=42):
        result_aiter = aiter_with_logging_context(func)

    result = [r async for r in result_aiter()]
    assert result == [42]


async def test_aiter_with_logging_context_multiple_values() -> None:
    """Test that multiple context values are preserved."""

    async def func() -> AsyncIterator[dict[str, int]]:
        yield {
            "a": current_context.get("a"),
            "b": current_context.get("b"),
        }

    with Context(a=1, b=2):
        result_aiter = aiter_with_logging_context(func)

    result = [r async for r in result_aiter()]
    assert result == [{"a": 1, "b": 2}]


async def test_aiter_with_logging_context_with_args() -> None:
    """Test that function arguments are passed through."""

    async def func(multiplier: int) -> AsyncIterator[int]:
        yield current_context.get("var") * multiplier

    with Context(var=10):
        result_aiter = aiter_with_logging_context(func)

    result = [r async for r in result_aiter(5)]
    assert result == [50]


async def test_aiter_with_logging_context_with_kwargs() -> None:
    """Test that function keyword arguments are passed through."""

    async def func(*, prefix: str) -> AsyncIterator[str]:
        yield f"{prefix}-{current_context.get('var')}"

    with Context(var="value"):
        result_aiter = aiter_with_logging_context(func)

    result = [r async for r in result_aiter(prefix="test")]
    assert result == ["test-value"]
