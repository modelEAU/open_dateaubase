# Coding Conventions

**Analysis Date:** 2026-03-03

## Naming Patterns

**Files:**
- `snake_case.py` for all Python modules (`channel_repository.py`, `timeseries_service.py`)
- `{entity}_repository.py` for data access files
- `{entity}_service.py` for service files
- `test_{module}.py` for test files
- `{TableName}.yaml` (PascalCase) for schema YAML files

**Functions:**
- `snake_case` for all functions (`get_all_sites()`, `list_channels()`, `find_or_create_sensor_metadata()`)
- No special prefix for async functions (none used — sync API)
- Repository functions named after the operation: `list_*`, `get_*_by_id`, `insert_*`, `find_or_create_*`

**Variables:**
- `snake_case` for variables (`channel_id`, `rows_written`, `where_clause`)
- `UPPER_SNAKE_CASE` for module-level constants (`MIGRATIONS_DIR`, `PROJECT_ROOT`, `SQL_FILES`)
- Dict keys from DB rows: `snake_case` (e.g., `channel_id`, `parameter_name`)

**Types:**
- `PascalCase` for classes — no `I` prefix (`ChannelOut`, `SensorStatusService`, `DictionaryManager`)
- `PascalCase` for type aliases and Pydantic models
- No enums observed; `int` IDs for value types

**Database Identifiers (SQL):**
- Column names: PascalCase with `_ID` suffix for foreign keys (`Channel_ID`, `Equipment_ID`, `Parameter_ID`)
- Table names: PascalCase (`Channel`, `LabAnalysis`, `ProcessingDegree`)
- SQL aliases: PascalCase to match column names (`p.[Parameter] AS ParameterName`)

## Code Style

**Formatting:**
- 4-space indentation throughout
- `from __future__ import annotations` at top of most files
- No semicolons (Python convention)
- Single and double quotes used interchangeably (no strict enforcement observed)
- Line length: standard Python (no Ruff/Prettier config found in `pyproject.toml`)

**Linting:**
- Ruff cache present (`.ruff_cache/`) indicating usage, but no config in `pyproject.toml`
- No pre-commit hooks configured

## Import Organization

**Order:**
1. `from __future__ import annotations`
2. Standard library imports
3. Third-party imports (fastapi, pydantic, pyodbc)
4. Local imports (api.v1.repositories, open_dateaubase)

**Path Handling:**
- Always use `from pathlib import Path` for filesystem paths
- Example from `tests/conftest.py`: `project_root = Path(__file__).parent.parent`

**Aliases:**
- None defined (no `@/` or similar path aliases)

## Error Handling

**Patterns:**
- Pydantic validators for request validation (automatic 422 on failure)
- `HTTPException` for HTTP-level errors at endpoint/service layer
- `ValueError` with descriptive messages for domain validation in core library
- Repositories return `None` for not-found (endpoints raise 404)
- Services sometimes catch broad `Exception` and raise `HTTPException(500)` (a known concern)

**Error Types:**
- `HTTPException(404)` — resource not found
- `HTTPException(422)` — automatic from Pydantic validation
- `HTTPException(503)` — database connection failure (`api/database.py`)
- `ValueError` — domain constraint violations in `src/open_dateaubase/`

**Async:**
- Not used — all endpoints are synchronous `def` (not `async def`)

## Logging

**Framework:**
- None — stdout/stderr only via `print()` or Python default
- No structured logger (pino, loguru, etc.)

**Patterns:**
- No consistent logging pattern; rely on FastAPI/uvicorn request logging

## Comments

**When to Comment:**
- SQL queries stored as module-level string constants (e.g., `_CHANNEL_SELECT = """...."""`)
- Docstrings on all public classes and functions

**Docstrings:**
- Module: Short triple-quoted string at file start (`"""Data access for Channel with all FK joins resolved."""`)
- Class: One-liner describing responsibility (`"""Service for sensor status operations."""`)
- Function: Short one-liner, no @param/@returns for internal code
- Integration tests: Multi-line with section headers describing what's tested

**TODO Comments:**
- Format: `# TODO: description` (no username)
- Examples: `# TODO: replace with auth context` in `api/v1/schemas/annotations.py`

## Function Design

**Size:**
- Repository functions generally 15-40 lines
- Service methods 20-60 lines
- `annotation_repository.py` is 400+ lines (known concern)

**Parameters:**
- DB functions: `(conn: pyodbc.Connection, ...)` — connection always first
- Endpoint functions: `(conn=Depends(get_db), ...)` — injected by FastAPI
- Pydantic models used for complex request bodies

**Return Values:**
- Repositories return `list[dict]`, `dict | None`, or scalar values
- Endpoints return Pydantic models (serialized by FastAPI)
- Explicit `return` statements

## Module Design

**Exports:**
- No `__init__.py` barrel files for most modules
- `src/open_dateaubase/__init__.py` likely exists but not used as barrel
- Direct imports from specific files preferred

**SQL Constants:**
- Long SQL queries stored as module-level string constants with leading underscore
- Example: `_CHANNEL_SELECT = """SELECT ..."""` in `api/v1/repositories/channel_repository.py`

**Type Hints:**
- Required on all function signatures
- Python 3.10+ union syntax: `dict | None`, `int | None` (not `Optional[T]`)
- `Optional[T]` from typing used in some older code (`Optional[datetime]`)
- Generic collections: `list[dict]`, `list[str]`

---

*Convention analysis: 2026-03-03*
*Update when patterns change*
