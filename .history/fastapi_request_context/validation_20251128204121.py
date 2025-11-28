"""Validation utilities for async routes and dependencies.

Context variables (and thus request context) require async code to work correctly.
Sync routes running in thread pools won't have access to the context set in the
async middleware. This module provides utilities to check that all routes and
dependencies are async.
"""

import asyncio
import inspect
import logging
from collections.abc import Callable
from typing import Any

from fastapi import FastAPI
from fastapi.routing import APIRoute

logger = logging.getLogger(__name__)


def is_async(func: Callable[..., Any]) -> bool:
    """Check if a function is async.

    Handles regular functions, coroutine functions, and classes with __call__.

    Args:
        func: Function to check.

    Returns:
        True if the function is async, False otherwise.
    """
    if asyncio.iscoroutinefunction(func):
        return True

    # Check for callable classes with async __call__
    if callable(func) and hasattr(func, "__call__"):  # noqa: B004
        return asyncio.iscoroutinefunction(func.__call__)  # type: ignore[operator]

    return False


def _get_dependency_functions(depends: Any) -> list[Callable[..., Any]]:  # noqa: ANN401
    """Extract dependency functions from a Depends object.

    Args:
        depends: A Depends object or similar.

    Returns:
        List of dependency callable functions.
    """
    functions: list[Callable[..., Any]] = []

    # Handle Depends object
    if hasattr(depends, "dependency") and depends.dependency is not None:
        functions.append(depends.dependency)

    return functions


def _get_route_dependencies(route: APIRoute) -> list[Callable[..., Any]]:
    """Get all dependency functions from a route.

    Args:
        route: FastAPI route to inspect.

    Returns:
        List of dependency callable functions.
    """
    dependencies: list[Callable[..., Any]] = []

    # Route-level dependencies
    for depends in route.dependencies or []:
        dependencies.extend(_get_dependency_functions(depends))

    # Endpoint parameter dependencies
    if route.endpoint:
        sig = inspect.signature(route.endpoint)
        for param in sig.parameters.values():
            if param.default is not inspect.Parameter.empty:
                dependencies.extend(_get_dependency_functions(param.default))

    return dependencies


def check_dependencies_are_async(
    dependencies: list[Callable[..., Any]],
    *,
    raise_on_sync: bool = False,
) -> list[str]:
    """Check that all dependencies are async.

    Args:
        dependencies: List of dependency functions to check.
        raise_on_sync: If True, raise an error for sync dependencies.

    Returns:
        List of warning messages for sync dependencies.

    Raises:
        ValueError: If raise_on_sync is True and sync dependencies found.
    """
    warnings: list[str] = []

    for dep in dependencies:
        if not is_async(dep):
            name = getattr(dep, "__name__", str(dep))
            msg = f"Sync dependency: {name}"
            warnings.append(msg)
            logger.warning(msg)

    if raise_on_sync and warnings:
        error_msg = "Sync dependencies found:\n" + "\n".join(f"  - {w}" for w in warnings)
        raise ValueError(error_msg)

    return warnings


def check_routes_and_dependencies_are_async(
    app: FastAPI,
    *,
    raise_on_sync: bool = False,
) -> list[str]:
    """Check that all routes and dependencies in a FastAPI app are async.

    This is important because context variables only work correctly in async code.
    Sync routes running in thread pools won't have access to request context.

    Call this at application startup to catch issues early.

    Args:
        app: FastAPI application to check.
        raise_on_sync: If True, raise an error for sync routes/dependencies.

    Returns:
        List of warning messages for sync routes/dependencies.

    Raises:
        ValueError: If raise_on_sync is True and sync items found.

    Example:
        >>> from fastapi import FastAPI
        >>> from fastapi_request_context.validation import (
        ...     check_routes_and_dependencies_are_async
        ... )
        >>>
        >>> app = FastAPI()
        >>>
        >>> @app.on_event("startup")
        ... async def validate():
        ...     check_routes_and_dependencies_are_async(app)
    """
    warnings: list[str] = []

    for route in app.routes:
        if not isinstance(route, APIRoute):
            continue

        # Check endpoint
        if route.endpoint and not is_async(route.endpoint):
            name = getattr(route.endpoint, "__name__", str(route.endpoint))
            msg = f"Sync route: {route.methods} {route.path} ({name})"
            warnings.append(msg)
            logger.warning(msg)

        # Check dependencies
        dependencies = _get_route_dependencies(route)
        dep_warnings = check_dependencies_are_async(dependencies)
        warnings.extend(f"  in {route.path}: {dep_warning}" for dep_warning in dep_warnings)

    if raise_on_sync and warnings:
        error_msg = "Sync routes/dependencies found:\n" + "\n".join(f"  - {w}" for w in warnings)
        raise ValueError(error_msg)

    return warnings
