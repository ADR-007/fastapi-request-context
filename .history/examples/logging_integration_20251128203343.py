"""Logging integration example.

This example shows how to set up logging formatters
that automatically include request context in log messages.
"""

import logging
import sys

from fastapi import FastAPI

from fastapi_request_context import (
    RequestContextMiddleware,
    StandardContextField,
    set_context,
)
from fastapi_request_context.formatters import JsonContextFormatter, LocalContextFormatter


def setup_json_logging() -> None:
    """Set up JSON logging for production environments."""
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonContextFormatter())
    logging.basicConfig(handlers=[handler], level=logging.INFO, force=True)


def setup_local_logging() -> None:
    """Set up human-readable logging for local development."""
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        LocalContextFormatter(
            fmt="%(asctime)s %(levelname)s %(context)s %(message)s",
            # Shorten UUIDs for readability
            shorten_fields={
                StandardContextField.REQUEST_ID,
                StandardContextField.CORRELATION_ID,
            },
            shorten_length=8,
        )
    )
    logging.basicConfig(handlers=[handler], level=logging.INFO, force=True)


# Choose based on environment
USE_JSON = False  # Set to True for production-style output
if USE_JSON:
    setup_json_logging()
else:
    setup_local_logging()

logger = logging.getLogger(__name__)

app = FastAPI()


@app.get("/")
async def root() -> dict[str, str]:
    """Endpoint that logs with context."""
    logger.info("Processing request")
    return {"status": "ok"}


@app.get("/process/{item_id}")
async def process_item(item_id: int) -> dict[str, str]:
    """Endpoint that does more processing with logging."""
    logger.info("Starting to process item")

    # Add custom context
    set_context("item_id", item_id)

    logger.info("Fetching item from database")
    # ... database operation ...

    logger.info("Processing item")
    # ... processing ...

    logger.info("Completed processing")
    return {"status": "processed", "item_id": str(item_id)}


@app.get("/error")
async def trigger_error() -> dict[str, str]:
    """Endpoint that logs an error."""
    logger.error("Something went wrong!")
    return {"status": "error"}


# Apply middleware
app = RequestContextMiddleware(app)  # type: ignore[assignment]

if __name__ == "__main__":
    import uvicorn

    print("Starting server at http://localhost:8000")
    print(f"Logging mode: {'JSON' if USE_JSON else 'Local'}")
    print("Try: curl http://localhost:8000/")
    print("Try: curl http://localhost:8000/process/123")
    print("Try: curl http://localhost:8000/error")
    uvicorn.run(app, host="0.0.0.0", port=8000)  # noqa: S104
