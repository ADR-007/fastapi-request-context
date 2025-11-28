"""Tests for validation utilities."""

import pytest
from fastapi import Depends, FastAPI

from fastapi_request_context.validation import (
    check_dependencies_are_async,
    check_routes_and_dependencies_are_async,
    is_async,
)


class TestIsAsync:
    """Tests for is_async function."""

    def test_async_function(self) -> None:
        """Test that async functions are detected."""

        async def async_func() -> None:
            pass

        assert is_async(async_func) is True

    def test_sync_function(self) -> None:
        """Test that sync functions are detected."""

        def sync_func() -> None:
            pass

        assert is_async(sync_func) is False

    def test_async_callable_class(self) -> None:
        """Test that classes with async __call__ are detected."""

        class AsyncCallable:
            async def __call__(self) -> None:
                pass

        assert is_async(AsyncCallable()) is True

    def test_sync_callable_class(self) -> None:
        """Test that classes with sync __call__ are detected."""

        class SyncCallable:
            def __call__(self) -> None:
                pass

        assert is_async(SyncCallable()) is False

    def test_lambda(self) -> None:
        """Test that lambdas are detected as sync."""
        assert is_async(lambda: None) is False


class TestCheckDependenciesAreAsync:
    """Tests for check_dependencies_are_async function."""

    def test_all_async(self) -> None:
        """Test that no warnings for all async dependencies."""

        async def dep1() -> None:
            pass

        async def dep2() -> None:
            pass

        warnings = check_dependencies_are_async([dep1, dep2])
        assert warnings == []

    def test_sync_dependency(self) -> None:
        """Test that sync dependencies generate warnings."""

        def sync_dep() -> None:
            pass

        async def async_dep() -> None:
            pass

        warnings = check_dependencies_are_async([sync_dep, async_dep])
        assert len(warnings) == 1
        assert "sync_dep" in warnings[0]

    def test_raise_on_sync(self) -> None:
        """Test that raise_on_sync raises ValueError."""

        def sync_dep() -> None:
            pass

        with pytest.raises(ValueError, match="Sync dependencies found"):
            check_dependencies_are_async([sync_dep], raise_on_sync=True)


class TestCheckRoutesAndDependenciesAreAsync:
    """Tests for check_routes_and_dependencies_are_async function."""

    def test_all_async_routes(self) -> None:
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

    def test_sync_route(self) -> None:
        """Test that sync routes generate warnings."""
        app = FastAPI()

        @app.get("/sync")
        def sync_route() -> dict[str, str]:
            return {"status": "ok"}

        warnings = check_routes_and_dependencies_are_async(app)
        assert len(warnings) == 1
        assert "sync_route" in warnings[0]
        assert "/sync" in warnings[0]

    def test_sync_dependency(self) -> None:
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

    def test_raise_on_sync_routes(self) -> None:
        """Test that raise_on_sync raises ValueError for sync routes."""
        app = FastAPI()

        @app.get("/sync")
        def sync_route() -> dict[str, str]:
            return {"status": "ok"}

        with pytest.raises(ValueError, match="Sync routes/dependencies found"):
            check_routes_and_dependencies_are_async(app, raise_on_sync=True)

    def test_mixed_routes(self) -> None:
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

    def test_multiple_sync_dependencies(self) -> None:
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

    def test_route_level_dependencies(self) -> None:
        """Test that route-level dependencies are checked."""

        def sync_dep() -> None:
            pass

        app = FastAPI()

        @app.get("/", dependencies=[Depends(sync_dep)])
        async def route() -> dict[str, str]:
            return {"status": "ok"}

        warnings = check_routes_and_dependencies_are_async(app)
        assert any("sync_dep" in w for w in warnings)
