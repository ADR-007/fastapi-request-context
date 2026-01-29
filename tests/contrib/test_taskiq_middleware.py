"""Tests for Taskiq middleware integration."""

import json
from typing import Any

import pytest
from taskiq import InMemoryBroker, TaskiqMessage, TaskiqResult

from fastapi_request_context import (
    get_context,
    get_full_context,
    set_context,
)
from fastapi_request_context.adapters.base import ContextAdapter
from fastapi_request_context.adapters.contextvars import ContextVarsAdapter
from fastapi_request_context.context import set_adapter
from fastapi_request_context.contrib.taskiq import RequestContextTaskiqMiddleware
from fastapi_request_context.fields import StandardContextField


@pytest.fixture(autouse=True)
def reset_context_adapter() -> None:
    """Reset context adapter before each test."""
    adapter = ContextVarsAdapter()
    set_adapter(adapter)


def test_initialization() -> None:
    """Test middleware initializes correctly."""
    middleware = RequestContextTaskiqMiddleware()
    assert middleware.REQUEST_CONTEXT_LABEL == "X-Request-Context"
    assert middleware._current_context.get() is None


def test_pre_send_captures_context() -> None:
    """Test that pre_send captures and serializes current context."""
    middleware = RequestContextTaskiqMiddleware()

    adapter = ContextVarsAdapter()
    with adapter:
        set_context(StandardContextField.CORRELATION_ID, "test-correlation-123")
        set_context(StandardContextField.REQUEST_ID, "should-be-removed")
        set_context("user_id", 42)
        set_context("custom_field", "custom_value")

        message = TaskiqMessage(
            task_id="task-123",
            task_name="test_task",
            labels={},
            args=[],
            kwargs={},
        )

        result_message = middleware.pre_send(message)

        assert middleware.REQUEST_CONTEXT_LABEL in result_message.labels
        context_str = result_message.labels[middleware.REQUEST_CONTEXT_LABEL]
        context_data = json.loads(context_str)

        assert context_data["correlation_id"] == "test-correlation-123"
        assert context_data["user_id"] == 42
        assert context_data["custom_field"] == "custom_value"
        assert "request_id" not in context_data


def test_pre_send_preserves_existing_labels() -> None:
    """Test that pre_send preserves existing message labels."""
    middleware = RequestContextTaskiqMiddleware()

    adapter = ContextVarsAdapter()
    with adapter:
        set_context("test_key", "test_value")

        message = TaskiqMessage(
            task_id="task-123",
            task_name="test_task",
            labels={"existing_label": "existing_value"},
            args=[],
            kwargs={},
        )

        result_message = middleware.pre_send(message)

        assert "existing_label" in result_message.labels
        assert result_message.labels["existing_label"] == "existing_value"
        assert middleware.REQUEST_CONTEXT_LABEL in result_message.labels


def test_pre_send_with_empty_context() -> None:
    """Test that pre_send works with empty context."""
    middleware = RequestContextTaskiqMiddleware()

    message = TaskiqMessage(
        task_id="task-123",
        task_name="test_task",
        labels={},
        args=[],
        kwargs={},
    )

    result_message = middleware.pre_send(message)

    assert middleware.REQUEST_CONTEXT_LABEL in result_message.labels
    context_str = result_message.labels[middleware.REQUEST_CONTEXT_LABEL]
    context_data = json.loads(context_str)
    assert isinstance(context_data, dict)


def test_pre_execute_restores_context() -> None:
    """Test that pre_execute restores context from message."""
    middleware = RequestContextTaskiqMiddleware()

    context_data = {
        "correlation_id": "restored-correlation-456",
        "user_id": 99,
        "org_id": "org-abc",
    }
    context_str = json.dumps(context_data)

    message = TaskiqMessage(
        task_id="task-456",
        task_name="test_task",
        labels={middleware.REQUEST_CONTEXT_LABEL: context_str},
        args=[],
        kwargs={},
    )

    result_message = middleware.pre_execute(message)

    assert result_message == message
    assert get_context(StandardContextField.CORRELATION_ID) == "restored-correlation-456"
    assert get_context(StandardContextField.TASK_ID) == "task-456"
    assert get_context("user_id") == 99
    assert get_context("org_id") == "org-abc"

    middleware.post_save(
        message,
        TaskiqResult(is_err=False, log=None, return_value=None, execution_time=0.0),
    )


def test_pre_execute_adds_task_id() -> None:
    """Test that pre_execute adds TASK_ID to context."""
    middleware = RequestContextTaskiqMiddleware()

    message = TaskiqMessage(
        task_id="task-789",
        task_name="test_task",
        labels={middleware.REQUEST_CONTEXT_LABEL: "{}"},
        args=[],
        kwargs={},
    )

    middleware.pre_execute(message)

    assert get_context(StandardContextField.TASK_ID) == "task-789"

    middleware.post_save(
        message,
        TaskiqResult(is_err=False, log=None, return_value=None, execution_time=0.0),
    )


def test_pre_execute_without_context_label() -> None:
    """Test that pre_execute handles missing context label."""
    middleware = RequestContextTaskiqMiddleware()

    message = TaskiqMessage(
        task_id="task-999",
        task_name="test_task",
        labels={},
        args=[],
        kwargs={},
    )

    result_message = middleware.pre_execute(message)

    assert result_message == message
    assert get_context(StandardContextField.TASK_ID) == "task-999"
    full_context = get_full_context()
    assert StandardContextField.TASK_ID.value in full_context

    middleware.post_save(
        message,
        TaskiqResult(is_err=False, log=None, return_value=None, execution_time=0.0),
    )


def test_post_save_cleans_up_context() -> None:
    """Test that post_save properly cleans up context."""
    middleware = RequestContextTaskiqMiddleware()

    message = TaskiqMessage(
        task_id="task-cleanup",
        task_name="test_task",
        labels={middleware.REQUEST_CONTEXT_LABEL: json.dumps({"test_key": "test_value"})},
        args=[],
        kwargs={},
    )

    middleware.pre_execute(message)
    assert get_context("test_key") == "test_value"
    assert get_context(StandardContextField.TASK_ID) == "task-cleanup"

    result: TaskiqResult[Any] = TaskiqResult(
        is_err=False,
        log=None,
        return_value={"status": "success"},
        execution_time=0.0,
    )
    middleware.post_save(message, result)

    assert middleware._current_context.get() is None


def test_post_save_without_context() -> None:
    """Test that post_save handles case when no context was set."""
    middleware = RequestContextTaskiqMiddleware()

    message = TaskiqMessage(
        task_id="task-no-context",
        task_name="test_task",
        labels={},
        args=[],
        kwargs={},
    )

    result: TaskiqResult[Any] = TaskiqResult(
        is_err=False,
        log=None,
        return_value=None,
        execution_time=0.0,
    )
    middleware.post_save(message, result)


def test_full_lifecycle() -> None:
    """Test complete lifecycle: pre_send -> pre_execute -> post_save."""
    middleware = RequestContextTaskiqMiddleware()

    adapter = ContextVarsAdapter()
    with adapter:
        set_context(StandardContextField.CORRELATION_ID, "lifecycle-correlation")
        set_context(StandardContextField.REQUEST_ID, "lifecycle-request-123")
        set_context("user_id", 777)

        send_message = TaskiqMessage(
            task_id="lifecycle-task",
            task_name="test_task",
            labels={},
            args=[],
            kwargs={},
        )

        sent_message = middleware.pre_send(send_message)
        assert middleware.REQUEST_CONTEXT_LABEL in sent_message.labels

        context_str = sent_message.labels[middleware.REQUEST_CONTEXT_LABEL]
        context_data = json.loads(context_str)
        assert "request_id" not in context_data
        assert context_data["correlation_id"] == "lifecycle-correlation"
        assert context_data["user_id"] == 777

    execute_message = TaskiqMessage(
        task_id="lifecycle-task",
        task_name="test_task",
        labels=sent_message.labels,
        args=[],
        kwargs={},
    )

    middleware.pre_execute(execute_message)
    assert get_context(StandardContextField.CORRELATION_ID) == "lifecycle-correlation"
    assert get_context(StandardContextField.TASK_ID) == "lifecycle-task"
    assert get_context("user_id") == 777

    result: TaskiqResult[Any] = TaskiqResult(
        is_err=False,
        log=None,
        return_value="done",
        execution_time=0.0,
    )
    middleware.post_save(execute_message, result)


def test_context_isolation_between_tasks() -> None:
    """Test that context is properly isolated between different task executions."""
    middleware = RequestContextTaskiqMiddleware()

    message1 = TaskiqMessage(
        task_id="task-1",
        task_name="test_task",
        labels={middleware.REQUEST_CONTEXT_LABEL: json.dumps({"user_id": 1})},
        args=[],
        kwargs={},
    )

    middleware.pre_execute(message1)
    assert get_context("user_id") == 1
    assert get_context(StandardContextField.TASK_ID) == "task-1"

    result1: TaskiqResult[Any] = TaskiqResult(
        is_err=False,
        log=None,
        return_value=None,
        execution_time=0.0,
    )
    middleware.post_save(message1, result1)

    message2 = TaskiqMessage(
        task_id="task-2",
        task_name="test_task",
        labels={middleware.REQUEST_CONTEXT_LABEL: json.dumps({"user_id": 2})},
        args=[],
        kwargs={},
    )

    middleware.pre_execute(message2)
    assert get_context("user_id") == 2
    assert get_context(StandardContextField.TASK_ID) == "task-2"

    result2: TaskiqResult[Any] = TaskiqResult(
        is_err=False,
        log=None,
        return_value=None,
        execution_time=0.0,
    )
    middleware.post_save(message2, result2)


def test_adapter_context_manager_called() -> None:
    """Test that adapter __enter__ and __exit__ are called."""
    middleware = RequestContextTaskiqMiddleware()

    message = TaskiqMessage(
        task_id="adapter-test",
        task_name="test_task",
        labels={middleware.REQUEST_CONTEXT_LABEL: json.dumps({"key": "value"})},
        args=[],
        kwargs={},
    )

    middleware.pre_execute(message)
    adapter = middleware._current_context.get()
    assert adapter is not None
    assert isinstance(adapter, ContextAdapter)

    result: TaskiqResult[Any] = TaskiqResult(
        is_err=False,
        log=None,
        return_value=None,
        execution_time=0.0,
    )
    middleware.post_save(message, result)
    assert middleware._current_context.get() is None


async def test_integration_with_inmemory_broker() -> None:
    """Test middleware integration with InMemoryBroker."""
    broker = InMemoryBroker()
    broker = broker.with_middlewares(RequestContextTaskiqMiddleware())

    @broker.task
    async def test_task(value: int) -> dict[str, Any]:
        correlation_id = get_context(StandardContextField.CORRELATION_ID)
        task_id = get_context(StandardContextField.TASK_ID)
        user_id = get_context("user_id")

        return {
            "correlation_id": correlation_id,
            "task_id": task_id,
            "user_id": user_id,
            "value": value,
        }

    adapter = ContextVarsAdapter()
    with adapter:
        set_context(StandardContextField.CORRELATION_ID, "integration-test-123")
        set_context(StandardContextField.REQUEST_ID, "should-not-propagate")
        set_context("user_id", 999)
        task = await test_task.kiq(42)

    result = await task.wait_result()

    assert not result.is_err
    assert result.return_value["correlation_id"] == "integration-test-123"
    assert result.return_value["user_id"] == 999
    assert result.return_value["value"] == 42
    assert result.return_value["task_id"] == task.task_id


async def test_multiple_tasks_with_different_contexts() -> None:
    """Test that different tasks get their own context properly."""
    broker = InMemoryBroker()
    broker = broker.with_middlewares(RequestContextTaskiqMiddleware())

    @broker.task
    async def context_reader() -> dict[str, Any]:
        return {
            "correlation_id": get_context(StandardContextField.CORRELATION_ID),
            "task_id": get_context(StandardContextField.TASK_ID),
            "user_id": get_context("user_id"),
        }

    adapter = ContextVarsAdapter()
    with adapter:
        set_context(StandardContextField.CORRELATION_ID, "context-1")
        set_context("user_id", 100)
        task1 = await context_reader.kiq()

        set_context(StandardContextField.CORRELATION_ID, "context-2")
        set_context("user_id", 200)
        task2 = await context_reader.kiq()

    result1 = await task1.wait_result()
    result2 = await task2.wait_result()

    assert result1.return_value["correlation_id"] == "context-1"
    assert result1.return_value["user_id"] == 100
    assert result2.return_value["correlation_id"] == "context-2"
    assert result2.return_value["user_id"] == 200


def test_import_error_message() -> None:
    """Test that helpful error message is raised when taskiq is not available."""
    import importlib
    import sys
    from unittest.mock import patch

    def reload_middleware() -> None:
        import fastapi_request_context.contrib.taskiq.middleware

        importlib.reload(fastapi_request_context.contrib.taskiq.middleware)

    with (
        patch.dict(sys.modules, {"taskiq": None}),
        pytest.raises(
            ImportError,
            match="taskiq is required",
        ),
    ):
        reload_middleware()
