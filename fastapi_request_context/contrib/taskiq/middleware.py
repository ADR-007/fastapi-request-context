"""Taskiq middleware for request context propagation."""

import json
from contextvars import ContextVar
from typing import TYPE_CHECKING, Any

from fastapi_request_context.context import get_adapter, get_full_context, set_context
from fastapi_request_context.fields import StandardContextField

if TYPE_CHECKING:
    from taskiq import TaskiqMessage, TaskiqResult

    from fastapi_request_context.adapters.base import ContextAdapter


try:
    from taskiq import TaskiqMiddleware
except ImportError as e:
    msg = "taskiq is required for RequestContextTaskiqMiddleware. Install with: pip install taskiq"
    raise ImportError(msg) from e


class RequestContextTaskiqMiddleware(TaskiqMiddleware):
    """Taskiq middleware that propagates request context to background tasks.

    This middleware:
    1. Captures the current request context when a task is sent
    2. Removes the REQUEST_ID (each task gets its own)
    3. Serializes the context and attaches it to the task message
    4. Restores the context when the task executes
    5. Adds the TASK_ID to the restored context

    Example:
        >>> from taskiq import InMemoryBroker
        >>> from fastapi_request_context.contrib.taskiq import RequestContextTaskiqMiddleware
        >>>
        >>> broker = InMemoryBroker()
        >>> broker = broker.with_middlewares(RequestContextTaskiqMiddleware())
        >>>
        >>> @broker.task
        ... async def my_task():
        ...     # Context from the originating request is available here
        ...     correlation_id = get_context(StandardContextField.CORRELATION_ID)
        ...     task_id = get_context(StandardContextField.TASK_ID)

    Note:
        This middleware requires the context-logging adapter or a compatible
        adapter that supports context manager protocol for proper cleanup.
    """

    REQUEST_CONTEXT_LABEL = "X-Request-Context"

    def __init__(self) -> None:
        """Initialize the middleware with a context variable for tracking."""
        super().__init__()
        self._current_context: ContextVar[ContextAdapter | None] = ContextVar(
            "current_taskiq_context",
            default=None,
        )

    def pre_send(self, message: "TaskiqMessage") -> "TaskiqMessage":
        """Capture and attach current request context to the task message.

        Args:
            message: The task message being sent.

        Returns:
            Modified message with request context attached.
        """
        full_context = get_full_context()
        full_context.pop(StandardContextField.REQUEST_ID.value, None)
        context_str = json.dumps(full_context)

        return message.model_copy(
            update={
                "labels": message.labels | {self.REQUEST_CONTEXT_LABEL: context_str},
            },
        )

    def pre_execute(self, message: "TaskiqMessage") -> "TaskiqMessage":
        """Restore request context before task execution.

        Args:
            message: The task message being executed.

        Returns:
            The original message (unmodified).
        """
        context_str = message.labels.get(self.REQUEST_CONTEXT_LABEL, "{}")
        context_data = json.loads(context_str)

        context_data[StandardContextField.TASK_ID.value] = message.task_id

        adapter = get_adapter()
        adapter.__enter__()

        for key, value in context_data.items():
            set_context(key, value)

        self._current_context.set(adapter)

        return message

    def post_save(
        self,
        message: "TaskiqMessage",  # noqa: ARG002
        result: "TaskiqResult[Any]",  # noqa: ARG002
    ) -> None:
        """Clean up context after task execution.

        Args:
            message: The task message that was executed.
            result: The task execution result.
        """
        adapter = self._current_context.get()
        if adapter is not None:
            adapter.__exit__(None, None, None)
            self._current_context.set(None)
