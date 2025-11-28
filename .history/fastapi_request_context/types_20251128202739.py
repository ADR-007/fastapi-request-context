"""Type aliases and protocols for fastapi-request-context."""

from collections.abc import Callable
from typing import Any, Protocol


class IdGenerator(Protocol):
    """Protocol for ID generator functions."""

    def __call__(self) -> str:
        """Generate a unique ID string."""
        ...


ContextKey = str
"""Type alias for context keys."""

ContextValue = Any
"""Type alias for context values."""

ContextDict = dict[ContextKey, ContextValue]
"""Type alias for context dictionary."""

IdGeneratorFunc = Callable[[], str]
"""Type alias for ID generator functions."""
