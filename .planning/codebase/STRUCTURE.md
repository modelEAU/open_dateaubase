# Codebase Structure

**Analysis Date:** 2026-03-03

## Directory Layout

```
open_dateaubase/
├── api/                        # FastAPI application
│   ├── config.py               # Settings from .env
│   ├── database.py             # get_connection(), get_db() dependency
│   ├── main.py                 # FastAPI app, mounts /api/v1
│   └── v1/
│       ├── router.py           # All sub-routers
│       ├── endpoints/          # FastAPI route handlers
│       ├── repositories/       # SQL queries (raw pyodbc)
│       ├── schemas/            # Pydantic request/response models
│       └── services/           # Business logic
├── src/open_dateaubase/        # Core library (FastAPI-agnostic)
│   ├── data_model/             # Pydantic schema dictionary models
│   ├── lineage.py              # SQL lineage queries
│   ├── meteaudata_bridge.py    # Processing provenance recording
│   └── dictionary.json         # Compiled schema dictionary
├── tests/                      # Test suite
│   ├── conftest.py             # Shared fixtures, sys.path setup
│   ├── fixtures/               # Test data fixtures
│   ├── unit/                   # Unit tests (no DB)
│   ├── integration/            # DB integration tests (requires Docker)
│   ├── api/contract/           # API contract tests (mock DB)
│   ├── schema/                 # YAML schema validation tests
│   └── legacy/                 # Pre-v2.0 tests (import errors, unmaintained)
├── schema_dictionary/          # YAML schema definitions
│   ├── tables/                 # Per-table YAML (e.g., Channel.yaml)
│   ├── views/                  # View definitions
│   ├── deprecated/             # Pre-v2.0 definitions
│   └── version.yaml            # Current schema version
├── migrations/                 # Versioned SQL migration scripts
├── sql/                        # Seed data SQL
├── sql_generation_scripts/     # SQL generation entry points
├── tools/schema_migrate/       # Custom schema validation/migration CLI
├── scripts/                    # Utility scripts (init_db.py, generate_from_yaml.py)
├── docs/                       # mkdocs documentation source
├── .github/workflows/          # GitHub Actions CI/CD
├── pyproject.toml              # Project config, dependencies
├── docker-compose.yml          # Local dev infra (MSSQL)
├── Dockerfile                  # API container image
└── conftest.py                 # Root pytest config (adds project root to sys.path)
```

## Directory Purposes

**`api/`**
- Purpose: FastAPI web application
- Contains: App factory, config, DB connection, all v1 API code
- Key files: `api/main.py`, `api/config.py`, `api/database.py`
- Subdirectories: `v1/` with endpoints/, repositories/, schemas/, services/

**`api/v1/endpoints/`**
- Purpose: HTTP route handlers (one file per domain)
- Contains: `channels.py`, `sites.py`, `timeseries.py`, `campaigns.py`, `equipment.py`, `lineage.py`, `ingest.py`, `annotations.py`, `sensor_status.py`, `health.py`, `metadata.py` (legacy)

**`api/v1/repositories/`**
- Purpose: SQL data access — all raw pyodbc queries
- Contains: `channel_repository.py`, `value_repository.py`, `ingestion_repository.py`, `annotation_repository.py`, `sensor_status_repository.py`, `site_repository.py`, `campaign_repository.py`, `equipment_repository.py`, `metadata_repository.py` (legacy)

**`api/v1/schemas/`**
- Purpose: Pydantic request/response models
- Contains: `channel.py`, `ingestion.py`, `timeseries.py`, `annotations.py`, `lineage.py`, `sensor_status.py`, `campaigns.py`, `equipment.py`, `common.py` (PaginatedResponse), `metadata.py` (legacy)

**`api/v1/services/`**
- Purpose: Business logic and orchestration
- Contains: `timeseries_service.py`, `lineage_service.py`, `sensor_status_service.py`, `annotation_service.py`

**`src/open_dateaubase/`**
- Purpose: Reusable domain library (no FastAPI dependency)
- Contains: `data_model/models.py` (Pydantic schema dict models), `data_model/helpers.py` (DictionaryManager), `lineage.py` (SQL lineage), `meteaudata_bridge.py` (processing bridge), `dictionary.json`

**`tests/`**
- Purpose: All test code
- Contains: Unit, integration, contract, schema tests
- Key files: `conftest.py` (root fixtures), `integration/conftest.py` (DB fixtures)
- Note: `tests/api/` must NOT have `__init__.py` (conflicts with `api/` package)

**`schema_dictionary/tables/`**
- Purpose: YAML source of truth for DB schema (one file per table)
- Contains: `Channel.yaml`, `Site.yaml`, `Sample.yaml`, etc.
- Key files: `version.yaml` (schema version)

**`migrations/`**
- Purpose: Versioned forward + rollback SQL migration scripts
- Key files: `v1.0.0_to_v2.1.0_mssql.sql`, `v1.0.0_to_v2.1.0_mssql_rollback.sql`

## Key File Locations

**Entry Points:**
- `api/main.py` - FastAPI app factory, `/docs`, `/redoc`
- `api/v1/router.py` - All API routes wiring
- `conftest.py` - Root pytest config (sys.path)

**Configuration:**
- `pyproject.toml` - Dependencies, pytest markers, project metadata
- `api/config.py` - Settings class, .env loading
- `api/database.py` - MSSQL connection, `get_db()` FastAPI dependency
- `docker-compose.yml` - Local MSSQL setup
- `mkdocs.yml` - Docs site config

**Core Logic:**
- `api/v1/repositories/` - All SQL queries
- `api/v1/services/` - Business logic
- `src/open_dateaubase/lineage.py` - Lineage SQL queries
- `src/open_dateaubase/meteaudata_bridge.py` - Processing provenance

**Testing:**
- `tests/unit/` - Fast unit tests (no DB)
- `tests/api/contract/` - API schema tests (mock DB via `dependency_overrides`)
- `tests/integration/` - Full DB tests (`@pytest.mark.db`)
- `tests/fixtures/sample_dictionary.py` - Shared test data

**Documentation:**
- `docs/` - mkdocs source
- `schema_dictionary/tables/` - YAML schema reference
- `docs/reference/tables.md` - Auto-generated table reference

## Naming Conventions

**Files:**
- `snake_case.py` for all Python modules
- `{entity}_repository.py` for repositories (e.g., `channel_repository.py`)
- `{entity}_service.py` for services (e.g., `sensor_status_service.py`)
- `test_{module}.py` for test files
- `{TableName}.yaml` (PascalCase) for schema YAML (e.g., `Channel.yaml`)
- `v{from}_to_v{to}_mssql.sql` for migration scripts

**Directories:**
- `snake_case` for Python directories
- Plural for collections: `endpoints/`, `repositories/`, `schemas/`, `services/`

**Special Patterns:**
- No `__init__.py` in `tests/api/` (conflicts with `api/` root package)
- `conftest.py` at root adds project root to `sys.path` (for `api/` imports)

## Where to Add New Code

**New API endpoint (domain):**
- Route handler: `api/v1/endpoints/{entity}.py`
- Pydantic schemas: `api/v1/schemas/{entity}.py`
- Repository: `api/v1/repositories/{entity}_repository.py`
- Service (if needed): `api/v1/services/{entity}_service.py`
- Wire up in: `api/v1/router.py`
- Contract tests: `tests/api/contract/test_{entity}_endpoints.py`
- Integration tests: `tests/integration/test_{entity}.py`

**New DB table:**
- YAML definition: `schema_dictionary/tables/{TableName}.yaml`
- Migration SQL: `migrations/v{from}_to_v{to}_mssql.sql`
- Rollback SQL: `migrations/v{from}_to_v{to}_mssql_rollback.sql`
- Seed data (if lookup table): `sql/seed_v{version}.sql`

**New schema feature:**
- Core model: `src/open_dateaubase/data_model/models.py`
- Dictionary validation: `src/open_dateaubase/data_model/helpers.py`

## Special Directories

**`tests/legacy/`**
- Purpose: Pre-v2.0 tests from earlier schema versions
- Source: Not maintained; import errors present
- Committed: Yes — do not delete; do not fix unless explicitly asked

**`schema_dictionary/deprecated/`**
- Purpose: YAML definitions for pre-v2.0 tables
- Source: Archived during schema migration phases
- Committed: Yes (history reference)

**`sql_generation_scripts/`**
- Purpose: Legacy SQL generation entry points
- Source: Manually updated; latest is `v2.1.0_create_mssql.sql`
- Committed: Yes

---

*Structure analysis: 2026-03-03*
*Update when directory structure changes*
