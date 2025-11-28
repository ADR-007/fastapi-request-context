"""Tests for check_dependencies_are_async function."""

import pytest

from fastapi_request_context.validation import check_dependencies_are_async


def test_all_async() -> None:
    """Test that no warnings for all async dependencies."""

    async def dep1() -> None:
        pass

    async def dep2() -> None:
        pass

    warnings = check_dependencies_are_async([dep1, dep2])
    assert warnings == []


def test_sync_dependency() -> None:
    """Test that sync dependencies generate warnings."""

    def sync_dep() -> None:
        pass

    async def async_dep() -> None:
        pass

    warnings = check_dependencies_are_async([sync_dep, async_dep])
    assert len(warnings) == 1
    assert "sync_dep" in warnings[0]


def test_raise_on_sync() -> None:
    """Test that raise_on_sync raises ValueError."""

    def sync_dep() -> None:
        pass

    with pytest.raises(ValueError, match="Sync dependencies found"):
        check_dependencies_are_async([sync_dep], raise_on_sync=True)
