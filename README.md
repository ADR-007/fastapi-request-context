# fastapi-request-context

[![PyPI version](https://badge.fury.io/py/fastapi-request-context.svg)](https://badge.fury.io/py/fastapi-request-context)
[![Python versions](https://img.shields.io/pypi/pyversions/fastapi-request-context.svg)](https://pypi.org/project/fastapi-request-context/)
[![CI](https://github.com/ADR-007/fastapi-request-context/actions/workflows/ci.yaml/badge.svg)](https://github.com/ADR-007/fastapi-request-context/actions/workflows/ci.yaml)
![coverage](https://raw.githubusercontent.com/ADR-007/fastapi-request-context/_xml_coverage_reports/data/main/./badge.svg)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

FastAPI middleware for request ID tracking, correlation IDs, and extensible request context with first-class logging integration.

## Features

- **Automatic request ID generation** - Every request gets a unique ID
- **Correlation ID support** - Accept from header or generate for distributed tracing
- **Response header injection** - Automatically add `X-Request-Id` and `X-Correlation-Id` to responses
- **Pluggable context backends** - Use `contextvars` (default) or `context-logging`
- **Custom context fields** - Extend with your own fields via StrEnum
- **Logging integration** - JSON and human-readable formatters with automatic context injection
- **Validation utilities** - Check that routes and dependencies are async
- **Zero configuration** - Works out of the box with sensible defaults
- **Type-safe** - Full type hints and mypy strict mode

## Installation

```bash
# Basic installation
pip install fastapi-request-context

# With context-logging support
pip install fastapi-request-context[context-logging]

# With JSON formatter support
pip install fastapi-request-context[json-formatter]

# All optional dependencies
pip install fastapi-request-context[all]
```

Using uv:
```bash
uv add fastapi-request-context
```

## Quick Start

```python
from fastapi import FastAPI
from fastapi_request_context import RequestContextMiddleware

# Create your app
app = FastAPI()

# Keep reference to raw app if needed (e.g., for TaskIQ, testing)
raw_app = app

# Wrap with middleware
app = RequestContextMiddleware(app)
```

Every request now has:
- Unique `request_id` (always generated)
- `correlation_id` (from `X-Correlation-Id` header or generated)
- Both added to response headers
- Context available in all log records (including access logs!)

## Usage

### Access Context Values

```python
from fastapi_request_context import get_context, get_full_context, StandardContextField

@app.get("/")
async def root():
    request_id = get_context(StandardContextField.REQUEST_ID)
    correlation_id = get_context(StandardContextField.CORRELATION_ID)
    
    # Or get everything
    all_context = get_full_context()
    
    return {"request_id": request_id}
```

### Custom Context Fields

```python
from enum import StrEnum
from fastapi_request_context import set_context, get_context

class MyContextField(StrEnum):
    USER_ID = "user_id"
    ORG_ID = "org_id"

async def get_current_user(token: str):
    user_id = decode_token(token)
    set_context(MyContextField.USER_ID, user_id)
    return user_id

@app.get("/me")
async def me(user_id: int = Depends(get_current_user)):
    # Context is available throughout the request
    return {"user_id": get_context(MyContextField.USER_ID)}
```

### Configuration

```python
from fastapi_request_context import RequestContextMiddleware, RequestContextConfig
from uuid import uuid4

config = RequestContextConfig(
    # Custom ID generators
    request_id_generator=lambda: str(uuid4()),
    correlation_id_generator=lambda: str(uuid4()),
    
    # Custom header names
    request_id_header="X-My-Request-Id",
    correlation_id_header="X-My-Correlation-Id",
    
    # Disable response headers
    add_response_headers=False,
    
    # Use context-logging adapter
    context_adapter="context_logging",
    
    # Only process HTTP (not WebSocket)
    scope_types={"http"},
)

app = RequestContextMiddleware(app, config=config)
```

### Logging Integration

#### JSON Formatter (Production)

```python
import logging
from fastapi_request_context.formatters import JsonContextFormatter

handler = logging.StreamHandler()
handler.setFormatter(JsonContextFormatter())
logging.basicConfig(handlers=[handler], level=logging.INFO)

# Logs automatically include context (nested under "context" key by default):
# {"message": "Processing", "level": "INFO", "context": {"request_id": "...", "user_id": 123}}
```

#### Simple Formatter (Human-Readable)

```python
from fastapi_request_context import StandardContextField
from fastapi_request_context.formatters import SimpleContextFormatter

handler = logging.StreamHandler()
handler.setFormatter(SimpleContextFormatter(
    fmt="%(asctime)s %(levelname)s %(context)s %(message)s",
    shorten_fields={StandardContextField.REQUEST_ID},  # Show first 8 chars
    hidden_fields={StandardContextField.CORRELATION_ID},  # Hide completely
))
logging.basicConfig(handlers=[handler], level=logging.INFO)

# Output: 2025-01-15 10:30:00 INFO [request_id=3fa85f64… user_id=123] Processing
```

### Access Logs Integration

Context is automatically available in **all log records**, including Uvicorn access logs when using `context-logging` adapter:

```python
from fastapi_request_context import RequestContextMiddleware, RequestContextConfig

config = RequestContextConfig(context_adapter="context_logging")
app = RequestContextMiddleware(app, config=config)

# Now access logs will include request_id and correlation_id!
# Example: INFO 127.0.0.1:8000 - "GET / HTTP/1.1" 200 [request_id=abc123]
```

### Custom Context Adapter

```python
from fastapi_request_context.adapters import ContextAdapter

class RedisAdapter(ContextAdapter):
    def set_value(self, key: str, value: Any) -> None:
        redis.hset(self._request_key, key, value)
    
    def get_value(self, key: str) -> Any:
        return redis.hget(self._request_key, key)
    
    def get_all(self) -> dict[str, Any]:
        return redis.hgetall(self._request_key)
    
    def enter_context(self, initial_values: dict[str, Any]) -> None:
        self._request_key = f"request:{uuid4()}"
        redis.hmset(self._request_key, initial_values)
    
    def exit_context(self) -> None:
        redis.delete(self._request_key)

config = RequestContextConfig(context_adapter=RedisAdapter())
app = RequestContextMiddleware(app, config=config)
```

### Validation Utilities

Ensure all routes and dependencies are async (required for proper context propagation):

```python
from fastapi_request_context.validation import check_routes_and_dependencies_are_async

@app.on_event("startup")
async def validate():
    warnings = check_routes_and_dependencies_are_async(app)
    # Logs warnings for any sync routes/dependencies
    
    # Or raise an error
    check_routes_and_dependencies_are_async(app, raise_on_sync=True)
```

### Streaming Responses with Context

When using streaming responses, the iteration happens outside the original request context. Use `aiter_with_logging_context` to preserve the logging context during iteration:

```python
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from fastapi_request_context import aiter_with_logging_context, get_context, StandardContextField

app = FastAPI()

@app.get("/stream")
async def stream():
    async def generate():
        # Context is preserved here during iteration
        request_id = get_context(StandardContextField.REQUEST_ID)
        for i in range(10):
            yield f"chunk {i} (request: {request_id})\n"

    return StreamingResponse(aiter_with_logging_context(generate)())
```

> **Note:** Requires `context-logging` extra: `pip install fastapi-request-context[context-logging]`

## API Reference

### Middleware

- `RequestContextMiddleware(app, config=None)` - Main middleware class

### Configuration

- `RequestContextConfig` - Configuration dataclass with all options

### Context Functions

- `set_context(key, value)` - Set a context value
- `get_context(key)` - Get a context value (returns None if not set)
- `get_full_context()` - Get all context values as a dict
- `aiter_with_logging_context(func)` - Preserve logging context in async iterators (requires `context-logging`)

### Fields

- `StandardContextField` - Built-in fields (REQUEST_ID, CORRELATION_ID)

### Adapters

- `ContextAdapter` - Protocol for custom adapters
- `ContextVarsAdapter` - Default adapter using Python's contextvars
- `ContextLoggingAdapter` - Adapter using context-logging library (enables access log integration)

### Formatters

- `JsonContextFormatter` - JSON formatter for structured logging
- `SimpleContextFormatter` - Human-readable formatter with inline context

### Validation

- `is_async(func)` - Check if a function is async
- `check_dependencies_are_async(deps)` - Check dependencies
- `check_routes_and_dependencies_are_async(app)` - Check entire app

## Why This Library?

### vs. Manual Implementation

| Feature | Manual | This Library |
|---------|--------|--------------|
| Request ID generation | DIY | ✅ Built-in |
| Correlation ID | DIY | ✅ Built-in |
| Response headers | DIY | ✅ Automatic |
| Context storage | DIY | ✅ Pluggable |
| Logging integration | DIY | ✅ Included |
| Type safety | Maybe | ✅ Full |
| Tests | Maybe | ✅ 100% coverage |

### vs. Other Libraries

- **Zero dependencies** beyond FastAPI (optional extras available)
- **Pluggable adapters** - not locked to one context library
- **Validation utilities** - catch sync code issues early
- **Production-ready formatters** - JSON and local dev support

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

```bash
# Clone the repo
git clone https://github.com/ADR-007/fastapi-request-context.git
cd fastapi-request-context

# Install dependencies
uv sync --all-extras

# Run tests
make test

# Run linting
make lint

# Fix linting issues
make lint-fix
```

## License

MIT License - see [LICENSE](LICENSE) for details.
