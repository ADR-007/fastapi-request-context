"""Tests for check_routes_and_dependencies_are_async function."""

import pytest
from fastapi import Depends, FastAPI

from fastapi_request_context.validation import check_routes_and_dependencies_are_async


def test_all_async_routes() -> None:
    """Test that no warnings for all async routes."""
    app = FastAPI()

    @app.get("/")
    async def async_route() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/create")
    async def async_create() -> dict[str, str]:
        return {"status": "created"}

    warnings = check_routes_and_dependencies_are_async(app)
    assert warnings == []


def test_sync_route() -> None:
    """Test that sync routes generate warnings."""
    app = FastAPI()

    @app.get("/sync")
    def sync_route() -> dict[str, str]:
        return {"status": "ok"}

    warnings = check_routes_and_dependencies_are_async(app)
    assert len(warnings) == 1
    assert "sync_route" in warnings[0]
    assert "/sync" in warnings[0]


def test_sync_dependency() -> None:
    """Test that sync dependencies generate warnings."""

    def sync_dep() -> int:
        return 42

    app = FastAPI()

    @app.get("/")
    async def route(value: int = Depends(sync_dep)) -> dict[str, int]:
        return {"value": value}

    warnings = check_routes_and_dependencies_are_async(app)
    assert len(warnings) >= 1
    assert any("sync_dep" in w for w in warnings)


def test_raise_on_sync_routes() -> None:
    """Test that raise_on_sync raises ValueError for sync routes."""
    app = FastAPI()

    @app.get("/sync")
    def sync_route() -> dict[str, str]:
        return {"status": "ok"}

    with pytest.raises(ValueError, match="Sync routes/dependencies found"):
        check_routes_and_dependencies_are_async(app, raise_on_sync=True)


def test_mixed_routes() -> None:
    """Test with mix of sync and async routes."""
    app = FastAPI()

    @app.get("/async")
    async def async_route() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/sync")
    def sync_route() -> dict[str, str]:
        return {"status": "ok"}

    warnings = check_routes_and_dependencies_are_async(app)
    assert len(warnings) == 1
    assert "/sync" in warnings[0]


def test_multiple_sync_dependencies() -> None:
    """Test that multiple sync dependencies generate warnings."""

    def sync_dep1() -> int:
        return 42

    def sync_dep2() -> str:
        return "hello"

    app = FastAPI()

    @app.get("/")
    async def route(
        v1: int = Depends(sync_dep1),
        v2: str = Depends(sync_dep2),
    ) -> dict[str, int | str]:
        return {"v1": v1, "v2": v2}

    warnings = check_routes_and_dependencies_are_async(app)
    # Should detect both sync dependencies
    assert any("sync_dep1" in w for w in warnings)
    assert any("sync_dep2" in w for w in warnings)


def test_route_level_dependencies() -> None:
    """Test that route-level dependencies are checked."""

    def sync_dep() -> None:
        pass

    app = FastAPI()

    @app.get("/", dependencies=[Depends(sync_dep)])
    async def route() -> dict[str, str]:
        return {"status": "ok"}

    warnings = check_routes_and_dependencies_are_async(app)
    assert any("sync_dep" in w for w in warnings)
