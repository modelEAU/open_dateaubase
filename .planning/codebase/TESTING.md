# Testing Patterns

**Analysis Date:** 2026-03-03

## Test Framework

**Runner:**
- pytest 9.0.2
- Config: `pyproject.toml` `[tool.pytest.ini_options]`

**Assertion Library:**
- pytest built-in `assert`
- `pytest.raises(ExceptionType, match="pattern")` for exception testing

**Run Commands:**
```bash
uv run pytest                                           # Run all tests
uv run pytest --tb=short -q                             # CI mode
uv run pytest tests/unit/                               # Unit tests only
uv run pytest tests/api/contract/                       # Contract tests (no DB)
uv run pytest -m db                                     # Integration tests (requires Docker MSSQL)
uv run pytest tests/test_models.py::TestKeyPart::test_valid_key  # Single test
```

## Test File Organization

**Location:**
- Separate `tests/` tree (not co-located with source)
- Organized by test type in subdirectories

**Naming:**
- Unit tests: `test_{module}.py` (e.g., `test_models.py`, `test_helpers.py`)
- Contract tests: `test_{entity}_endpoints.py`
- Integration tests: `test_{phase_or_feature}.py`
- CI validation tests: `test_schema_ci.py`, `test_yaml_generation_ci.py`

**Structure:**
```
tests/
  conftest.py                           # Shared fixtures, sys.path
  fixtures/
    __init__.py
    sample_dictionary.py                # Test data generators
  unit/
    test_models.py                      # Pydantic model validation
    test_helpers.py                     # DictionaryManager tests
    test_schema_ci.py                   # YAML schema CI validation
    test_yaml_generation_ci.py          # SQL/YAML generation smoke tests
  api/
    contract/
      test_schema_contracts.py          # API endpoint/schema contracts (mock DB)
      test_annotation_endpoints.py
      test_sensor_status_endpoints.py
  integration/
    conftest.py                         # MSSQL connection fixtures
    test_migrations.py                  # Full migration path verification
    test_phase2a.py ... test_phase3.py  # Schema phase integration tests
    test_business_queries.py
  schema/
    test_sensor_status_yaml.py          # YAML definition validation
  legacy/                               # ⚠️ Pre-v2.0, import errors, unmaintained
```

## Test Structure

**Class-based (unit tests):**
```python
class TestKeyPart:
    def test_valid_key(self):
        key = KeyPart(Part_ID="Site_ID", ...)
        assert key.part_id == "Site_ID"

    def test_key_without_id_suffix(self):
        with pytest.raises(ValueError, match="should end with '_ID'"):
            KeyPart(Part_ID="Site", ...)
```

**Function-based (CI/integration tests):**
```python
def test_yaml_schema_validates_cleanly() -> None:
    from tools.schema_migrate.loader import load_schema
    result = load_schema("schema_dictionary/tables")
    assert result.is_valid
```

**Patterns:**
- Class-based for grouped unit tests on a single model/component
- Function-based for integration and CI smoke tests
- Explicit arrange/act/assert in complex tests

## Mocking

**Framework:**
- `unittest.mock.MagicMock` for mocking pyodbc connections/cursors
- FastAPI `dependency_overrides` for injecting mock DB connections

**API Contract Test Pattern:**
```python
@pytest.fixture
def mock_conn():
    conn = MagicMock()
    cursor = MagicMock()
    conn.cursor.return_value = cursor
    cursor.fetchall.return_value = [...]
    cursor.fetchone.return_value = (1,)
    def _override():
        yield conn
    app.dependency_overrides[get_db] = _override
    yield conn, cursor
    app.dependency_overrides.clear()
```

**What to Mock:**
- `pyodbc.Connection` — via `MagicMock()` in contract tests
- `app.dependency_overrides[get_db]` — replaces DB injection for API tests
- `cursor.fetchall()`, `cursor.fetchone()` return values

**What NOT to Mock:**
- Internal pure functions (Pydantic validators, helper functions)
- The actual database in integration tests (use real Docker MSSQL)

## Fixtures and Factories

**Root conftest.py** (`tests/conftest.py`):
```python
@pytest.fixture
def sample_json_dict():
    """Return sample dictionary data as Python dict."""
    return sample_dictionary_data()

@pytest.fixture
def output_dirs(tmp_path):
    return {"output": tmp_path / "output", ...}
```

**Integration conftest.py** (`tests/integration/conftest.py`):
- MSSQL connection setup/teardown
- Helper functions: `column_exists()`, `get_table_names()`, `run_sql_file()`
- Fixtures for database state at specific schema versions

**Shared test data:**
- `tests/fixtures/sample_dictionary.py` — in-memory schema dict data

## Coverage

**Requirements:**
- No enforced coverage target
- Coverage tracked for awareness (CI does not block on coverage %)

**Configuration:**
- No explicit coverage config in `pyproject.toml`
- Run with `uv run pytest --cov` if needed

**Focus areas:**
- Pydantic model validation (unit tests cover exhaustively)
- Migration integrity (integration tests verify forward + rollback)
- API contract stability (contract tests verify schema shape)

## Test Types

**Unit Tests** (`tests/unit/`):
- Scope: Single Pydantic model, helper function, or validator
- Mocking: None needed (pure Python)
- Speed: Fast (<1s per test)
- Examples: `test_models.py` (KeyPart, TablePart, etc.), `test_helpers.py` (DictionaryManager)

**Contract Tests** (`tests/api/contract/`):
- Scope: API endpoint exists, returns correct HTTP status, response matches schema
- Mocking: `dependency_overrides[get_db]` with `MagicMock` cursor
- Speed: Fast (no real DB)
- Examples: `test_schema_contracts.py`, `test_annotation_endpoints.py`

**Integration Tests** (`tests/integration/`):
- Scope: Full schema migration, FK constraints, real SQL queries
- Mocking: None — real Docker MSSQL connection
- Marked: `@pytest.mark.db` (skipped without Docker)
- Examples: `test_migrations.py`, `test_phase2c.py`

**Schema/CI Tests** (`tests/unit/`, `tests/schema/`):
- Scope: YAML validation, migration rollback existence, version matching
- Mocking: None (file system only)
- Speed: Fast
- Examples: `test_schema_ci.py`, `test_sensor_status_yaml.py`

## Common Patterns

**Exception Testing:**
```python
with pytest.raises(ValueError, match="should end with '_ID'"):
    KeyPart(Part_ID="Site", ...)
```

**Conditional Skip:**
```python
if not migration_files:
    pytest.skip("No migration scripts found — skipping rollback check.")
```

**pytest Markers:**
```python
# Entire module requires DB:
pytestmark = pytest.mark.db

# Single test:
@pytest.mark.slow
def test_heavy_migration():
    ...
```

**Available markers** (from `pyproject.toml`):
- `db` — requires running MSSQL Docker container
- `integration` — integration test (slower)
- `unit` — unit test (fast)
- `slow` — slow running test

---

*Testing analysis: 2026-03-03*
*Update when test patterns change*
