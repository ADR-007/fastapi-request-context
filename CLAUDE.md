# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**fastapi-request-context** is a FastAPI middleware library for request ID tracking, correlation IDs, and extensible request context with first-class logging integration.

Key capabilities:
- Automatic request ID generation (always new, never from header - security best practice)
- Correlation ID support (from header or generated - for distributed tracing)
- Response header injection (X-Request-Id, X-Correlation-Id)
- Pluggable context backends (contextvars default, context-logging optional)
- Extensible context fields via StrEnum
- Logging formatters with automatic context injection
- Validation utilities to ensure async routes/dependencies

## Development Commands

### Testing
```bash
# Run tests with pytest
make test
uv run pytest tests/ -v

# Run tests for all Python/FastAPI versions
make test-all
uv run tox

# Run coverage
make coverage
uv run coverage run -m pytest tests/
uv run coverage report
uv run coverage html
```

### Linting and Type Checking
```bash
# Run all linters and type checker
make lint
uv run ruff check fastapi_request_context tests/ examples/
uv run ruff format --check fastapi_request_context tests/ examples/
uv run mypy fastapi_request_context tests/

# Auto-fix linting issues
make lint-fix
uv run ruff format fastapi_request_context tests/ examples/
uv run ruff check --fix fastapi_request_context tests/ examples/
```

### Package Management
```bash
# Install dependencies (including optional deps)
uv sync --all-extras

# Add a dependency
uv add package-name

# Add a dev dependency
uv add --dev package-name

# Add an optional dependency
# Edit pyproject.toml [project.optional-dependencies] section
```

## Architecture

### Core Flow: Request Context Lifecycle

```
1. Request arrives → Middleware intercepts
2. Generate request_id (always new)
3. Extract/generate correlation_id (from header or new)
4. Store in context via adapter.enter_context()
5. Inject headers into response via send_with_headers()
6. Clean up via adapter.exit_context() in finally block
```

### Key Architectural Decisions

**Adapter Pattern for Context Storage**
The library uses a pluggable adapter system to decouple context storage from the middleware logic:
- `ContextAdapter` protocol in `adapters/base.py` defines the interface
- `ContextVarsAdapter` (default): Uses Python's built-in contextvars, no dependencies
- `ContextLoggingAdapter` (optional): Uses context-logging library for integration with access logs
- Custom adapters can be implemented by users

**Why This Matters**: When modifying context behavior, changes must be made in the adapter, not the middleware. The middleware only calls `enter_context()`, `exit_context()`, and users call `set_value()`, `get_value()`, `get_all()` via context.py wrappers.

**Security: Request ID Always Generated**
The middleware always generates a new request_id using the configured generator, never accepting it from request headers. This prevents:
- ID exhaustion attacks
- ID injection attacks
- Request forgery

Correlation IDs are accepted from headers because they're meant for distributed tracing across services.

**Global Adapter Pattern**
The library uses a global adapter instance (`_adapter` in `context.py`) that's set by the middleware during initialization. This allows `get_context()`, `set_context()`, and `get_full_context()` to work without passing the adapter around.

**Why This Matters**: When adding new context functions, they should use `_adapter` not create new instances. The middleware calls `set_adapter()` during `__init__`.

**Response Header Injection via Send Wrapper**
Headers are injected by wrapping the ASGI `send` callable. The wrapper intercepts `http.response.start` messages and modifies the headers list before forwarding to the original send.

**Why This Matters**: Any changes to header injection must happen in the `send_with_headers` closure inside `RequestContextMiddleware.__call__()`. Don't try to modify the response object directly - ASGI doesn't work that way.

### Module Organization

```
fastapi_request_context/
├── middleware.py       # RequestContextMiddleware - entry point, orchestrates request handling
├── context.py          # Global context functions - get_context(), set_context(), etc.
├── config.py           # RequestContextConfig dataclass - all configuration options
├── fields.py           # StandardContextField enum - built-in fields (REQUEST_ID, CORRELATION_ID)
├── types.py            # Type aliases (ContextDict, etc.)
├── adapters/
│   ├── base.py         # ContextAdapter Protocol - interface for storage backends
│   ├── contextvars.py  # Default adapter using Python's contextvars
│   └── context_logging.py  # Optional adapter using context-logging library
├── formatters/
│   ├── json.py         # JsonContextFormatter - for production JSON logs
│   └── simple.py       # SimpleContextFormatter - human-readable dev logs
└── validation.py       # Utilities to check routes/dependencies are async
```

### Context Adapters: How They Work

Each adapter must implement the `ContextAdapter` protocol:
1. `enter_context(initial_values)` - Called when request starts
2. `set_value(key, value)` - Store a context value
3. `get_value(key)` - Retrieve a context value
4. `get_all()` - Get all context as dict
5. `exit_context()` - Called when request ends (cleanup)

**ContextVarsAdapter** (default):
- Uses a single ContextVar that stores a dict
- In `enter_context()`: Creates new dict and sets it via `.set()`
- In `exit_context()`: Resets the ContextVar
- Leverages Python's automatic context propagation in async code

**ContextLoggingAdapter**:
- Wraps the context-logging library
- Enables automatic context inclusion in ALL log records, including Uvicorn access logs
- Uses context_logging.setup_log_record() in enter_context()
- Uses context_logging.clear_log_record() in exit_context()

### Validation Utilities: Why They Exist

Context variables only work correctly in async code. Sync routes run in thread pools and lose context.

The `validation.py` module provides:
- `is_async(func)` - Checks if a function is async (handles callables, classes)
- `check_dependencies_are_async()` - Validates dependency list
- `check_routes_and_dependencies_are_async(app)` - Scans entire FastAPI app

**When to use**: Call `check_routes_and_dependencies_are_async(app)` in an `@app.on_event("startup")` handler to catch issues early in development.

## Testing Strategy

### Test Structure
```
tests/
├── conftest.py                   # Shared fixtures (test_app, client, etc.)
├── test_middleware.py            # Middleware behavior, header injection
├── test_context.py               # Context get/set/get_all functions
├── adapters/
│   ├── test_contextvars.py       # ContextVarsAdapter
│   └── test_context_logging.py  # ContextLoggingAdapter
├── formatters/
│   ├── test_json.py              # JsonContextFormatter
│   ├── test_simple.py            # SimpleContextFormatter
│   └── test_integration.py       # Full logging integration
└── validation/
    ├── test_is_async.py          # is_async() function
    ├── test_dependencies.py      # Dependency checking
    └── test_routes.py            # Route checking
```

### Coverage Requirements
- Minimum coverage: 90% (enforced by tox)
- Target coverage: 100% (enforced by coverage environment)
- Coverage excludes: Protocol stubs, TYPE_CHECKING blocks, abstract methods

**When writing new features**: Add comprehensive tests before implementation. Follow TDD when possible.

### Testing Patterns

**Testing Middleware**: Use httpx.AsyncClient with the wrapped app
```python
from httpx import AsyncClient

async def test_middleware():
    app = FastAPI()
    app = RequestContextMiddleware(app)
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/")
        assert "x-request-id" in response.headers
```

**Testing Context**: Use pytest-asyncio with async fixtures
```python
async def test_context():
    adapter = ContextVarsAdapter()
    adapter.enter_context({"test": "value"})
    try:
        assert adapter.get_value("test") == "value"
    finally:
        adapter.exit_context()
```

**Testing Formatters**: Capture log records and verify format
```python
import logging
from io import StringIO

def test_formatter():
    stream = StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(JsonContextFormatter())
    # ... trigger logging, parse JSON output
```

## Common Patterns and Conventions

### Adding a New Context Field (for users)
Users should define custom fields in their applications, not in this library. The library only provides `StandardContextField` with generic fields (REQUEST_ID, CORRELATION_ID).

```python
# In user's application code:
from enum import StrEnum

class MyAppContextField(StrEnum):
    USER_ID = "user_id"
    TENANT_ID = "tenant_id"
```

### Adding a New Adapter
1. Create new file in `adapters/` directory
2. Implement `ContextAdapter` protocol
3. Add to `_get_adapter()` function in `middleware.py` if built-in
4. Add optional dependency to `pyproject.toml` if needed
5. Add comprehensive tests in `tests/adapters/`
6. Document in README.md

### Modifying Request/Response Handling
All middleware logic is in `RequestContextMiddleware.__call__()`:
1. Check scope type filtering
2. Generate IDs
3. Call `adapter.enter_context()`
4. Wrap send function if headers enabled
5. Clean up in finally block

**Critical**: Always use try/finally to ensure `exit_context()` is called, even if the app raises exceptions.

### Configuration Changes
When adding new config options:
1. Add field to `RequestContextConfig` dataclass in `config.py`
2. Provide sensible default
3. Document in docstring
4. Use in middleware
5. Add tests for the new option
6. Update README.md

## Type Checking and Linting

### Mypy Configuration
- Strict mode enabled (`strict = true`)
- Tests have relaxed rules (see `[[tool.mypy.overrides]]` for `tests.*`)
- External libraries without type stubs: `context_logging`, `pythonjsonlogger`

**When adding new code**: Always add type hints. Use `from typing import TYPE_CHECKING` to avoid circular imports.

### Ruff Configuration
- Target: Python 3.10+ (`target-version = "py310"`)
- Line length: 100 characters
- Convention: Google-style docstrings
- Comprehensive rule set enabled (see `pyproject.toml`)

**Per-file ignores**:
- `tests/**/*.py`: Allows asserts, missing docstrings, magic values, etc.
- `examples/**/*.py`: Allows print statements, missing docstrings

**When you see linting errors**: Run `make lint-fix` to auto-fix formatting and simple issues. Complex issues may need manual fixes.

## Optional Dependencies

The library has minimal required dependencies (only FastAPI/Starlette) with optional extras:

```toml
[project.optional-dependencies]
context-logging = ["context-logging>=0.7.0"]
json-formatter = ["python-json-logger>=2.0.0"]
all = ["context-logging>=0.7.0", "python-json-logger>=2.0.0"]
```

**When working with optional dependencies**:
- Use try/except imports in adapter/formatter code
- Provide helpful error messages if user hasn't installed the extra
- See `ContextLoggingAdapter` for example pattern

## CI/CD and Release Process

### GitHub Actions Workflows

**.github/workflows/ci.yaml** - Runs on every push/PR:
- Tests on Python 3.12, 3.13
- Tests across FastAPI 0.100, 0.110, 0.115
- Linting (ruff, mypy)
- Coverage reporting to codecov

**.github/workflows/release.yaml** - Runs on push to main:
- Uses python-semantic-release
- Automatically determines version bump from commit messages
- Updates pyproject.toml version
- Creates GitHub release
- Publishes to PyPI

### Commit Message Convention

This project uses **Angular commit convention** for semantic release:
- `feat:` - New feature (minor version bump)
- `fix:` - Bug fix (patch version bump)
- `docs:` - Documentation only
- `refactor:` - Code refactoring
- `test:` - Adding tests
- `chore:` - Build process, dependencies

**Breaking changes**: Add `BREAKING CHANGE:` in commit body for major version bump.

Example:
```
feat: add custom ID validator support

Allow users to provide custom ID validation functions.

BREAKING CHANGE: RequestContextConfig.id_validator signature changed
```

## Key Files to Understand

**middleware.py** - Start here to understand the request flow
- `RequestContextMiddleware.__call__()` - Main ASGI handler
- `_get_header_value()` - Header extraction helper
- `_get_adapter()` - Adapter resolution

**context.py** - Public API for users
- Global `_adapter` instance pattern
- `set_context()`, `get_context()`, `get_full_context()` - Main user-facing functions

**adapters/base.py** - Protocol definition
- Understand this to see what adapters must implement
- Only 5 methods: set_value, get_value, get_all, enter_context, exit_context

**validation.py** - Async validation
- `is_async()` - Core detection logic handles coroutines, callables, classes
- Recursive dependency inspection via `inspect.signature()`

## Working with Examples

The `examples/` directory contains runnable examples:
- `basic_usage.py` - Minimal setup
- `custom_fields.py` - Custom context fields
- `custom_adapter.py` - Custom adapter implementation
- `logging_integration.py` - Logging formatters
- `validation.py` - Validation utilities

**When adding features**: Create a corresponding example showing real-world usage.

## Package Distribution

This project uses:
- **uv** for dependency management and virtual environments
- **hatchling** as build backend
- **pyproject.toml** for all configuration (no setup.py)

To build and publish manually:
```bash
uv build
uv publish
```

(Normally done automatically by release workflow)
