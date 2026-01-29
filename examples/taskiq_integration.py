"""Example of using Taskiq with request context propagation.

This example demonstrates how to:
1. Set up a Taskiq broker with the RequestContextTaskiqMiddleware
2. Send tasks from FastAPI endpoints with automatic context propagation
3. Access request context (correlation_id, custom fields) within tasks
4. Maintain distributed tracing across async task boundaries
"""

import logging
import logging.config

from fastapi import FastAPI
from taskiq import InMemoryBroker

from fastapi_request_context import (
    RequestContextMiddleware,
    get_context,
    set_context,
)
from fastapi_request_context.contrib.taskiq import RequestContextTaskiqMiddleware
from fastapi_request_context.fields import StandardContextField
from fastapi_request_context.formatters.json import JsonContextFormatter

logging.config.dictConfig(
    {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "json": {
                "()": JsonContextFormatter,
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "json",
                "stream": "ext://sys.stdout",
            },
        },
        "root": {
            "level": "INFO",
            "handlers": ["console"],
        },
    },
)

logger = logging.getLogger(__name__)

broker = InMemoryBroker()
broker = broker.with_middlewares(RequestContextTaskiqMiddleware())

app = FastAPI()
app = RequestContextMiddleware(app)


@broker.task
async def process_user_data(user_id: int) -> dict:
    """Background task that processes user data.

    The request context from the originating request is automatically
    available here, including correlation_id and any custom fields.
    """
    correlation_id = get_context(StandardContextField.CORRELATION_ID)
    task_id = get_context(StandardContextField.TASK_ID)
    request_user_id = get_context("user_id")

    logger.info(
        "Processing user data in background task",
        extra={
            "user_id": user_id,
            "request_user_id": request_user_id,
        },
    )

    return {
        "correlation_id": correlation_id,
        "task_id": task_id,
        "user_id": user_id,
        "status": "processed",
    }


@app.post("/users/{user_id}/process")
async def trigger_processing(user_id: int) -> dict:
    """Endpoint that triggers background processing.

    The current request context (correlation_id, custom fields) will be
    automatically propagated to the background task.
    """
    set_context("user_id", user_id)

    logger.info("Triggering background processing", extra={"user_id": user_id})

    task = await process_user_data.kiq(user_id)

    correlation_id = get_context(StandardContextField.CORRELATION_ID)
    request_id = get_context(StandardContextField.REQUEST_ID)

    return {
        "message": "Processing started",
        "task_id": task.task_id,
        "correlation_id": correlation_id,
        "request_id": request_id,
    }


@app.get("/health")
async def health_check() -> dict:
    """Health check endpoint."""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, port=8000)
