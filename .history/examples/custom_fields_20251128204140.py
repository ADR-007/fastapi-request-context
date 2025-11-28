"""Using custom context fields.

This example shows how to define and use custom context fields
for your application. Use StrEnum for type-safe field access.
"""

import sys

if sys.version_info >= (3, 11):
    from enum import StrEnum
else:
    from enum import Enum

    class StrEnum(str, Enum):
        """Backport of StrEnum for Python 3.10."""

from typing import Annotated

from fastapi import Depends, FastAPI, Header

from fastapi_request_context import (
    RequestContextMiddleware,
    StandardContextField,
    get_context,
    get_full_context,
    set_context,
)


class MyContextField(StrEnum):
    """Custom context fields for this application."""

    USER_ID = "user_id"
    ORGANIZATION_ID = "organization_id"
    TENANT_ID = "tenant_id"


app = FastAPI()


async def get_current_user(
    authorization: Annotated[str | None, Header()] = None,
) -> int | None:
    """Dependency that extracts user from auth header and stores in context."""
    if not authorization:
        return None

    # In real app, decode JWT token here
    user_id = 12345

    # Store in context - will be available throughout request
    set_context(MyContextField.USER_ID, user_id)
    set_context(MyContextField.ORGANIZATION_ID, "org-abc")

    return user_id


@app.get("/me")
async def me(user_id: int | None = Depends(get_current_user)) -> dict[str, str | int | None]:
    """Endpoint that uses custom context fields."""
    return {
        "user_id": user_id,
        "org_id": get_context(MyContextField.ORGANIZATION_ID),
        "request_id": get_context(StandardContextField.REQUEST_ID),
    }


@app.get("/debug-context")
async def debug_context(
    user_id: int | None = Depends(get_current_user),
) -> dict[str, str | int | None]:
    """Show all context values for debugging."""
    return get_full_context()


# Apply middleware
app = RequestContextMiddleware(app)  # type: ignore[assignment]

if __name__ == "__main__":
    import uvicorn

    print("Starting server at http://localhost:8000")
    print("Try: curl http://localhost:8000/me")
    print("Try: curl -H 'Authorization: Bearer token' http://localhost:8000/me")
    print("Try: curl -H 'Authorization: Bearer token' http://localhost:8000/debug-context")
    uvicorn.run(app, host="0.0.0.0", port=8000)  # noqa: S104
