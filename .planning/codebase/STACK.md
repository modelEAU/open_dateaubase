# Technology Stack

**Analysis Date:** 2026-03-03

## Languages

**Primary:**
- Python 3.12 - All application code (`pyproject.toml`, `.python-version`)

**Secondary:**
- SQL (MSSQL/T-SQL) - Schema definitions, migrations, seed data (`migrations/`, `sql/`, `sql_generation_scripts/`)
- YAML - Schema dictionary definitions (`schema_dictionary/tables/`)

## Runtime

**Environment:**
- Python 3.12+ (requires-python = ">=3.12" in `pyproject.toml`)
- MSSQL / Azure SQL Edge (ARM64) - `docker-compose.yml`
- Docker - local dev database container

**Package Manager:**
- uv - `pyproject.toml`, `.github/workflows/ci.yml`
- Lockfile: `uv.lock` present (165 KB)

## Frameworks

**Core:**
- FastAPI 0.129.0 - Web API framework (`api/main.py`, `api/v1/router.py`)
- Uvicorn 0.41.0 - ASGI server (`Dockerfile`, CI)
- Pydantic 2.12.5 - Data validation and serialization (`api/v1/schemas/`)

**Testing:**
- pytest 9.0.2 - All test types (`pyproject.toml` [dev])
- httpx 0.28.1 - HTTP client for API contract tests (`pyproject.toml` [dev])

**Build/Dev:**
- mkdocs 1.6.1 + mkdocs-material 9.6.22 - Documentation site (`mkdocs.yml`)
- mkdocs-gen-files 0.5.0 - Auto-generate documentation files
- markdown-exec 1.12.1 - Execute code blocks in markdown

## Key Dependencies

**Critical:**
- pyodbc 5.3.0 - MSSQL connection driver, sync (`api/database.py`)
- python-dotenv 1.2.1 - Environment variable loading (`api/config.py`)
- PyYAML 6.0.3 - Schema dictionary YAML parsing (`schema_dictionary/`)

**Infrastructure:**
- Starlette 0.52.1 - HTTP toolkit (FastAPI dependency)
- pydantic-core - Type validation engine (Pydantic dependency)

## Configuration

**Environment:**
- `.env.local` (priority) or `.env` — loaded by `api/config.py`
- Key vars: `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`
- Docker-specific: `.env.docker.example` (template exists)
- ⚠️ No `.env.example` for general development setup

**Build:**
- `pyproject.toml` - Project metadata, dependencies, pytest config
- `mkdocs.yml` - Documentation site configuration
- `docker-compose.yml` - Local dev infrastructure (db + db-init services)
- `Dockerfile` - Python 3.11-slim base with MSSQL ODBC driver

## Platform Requirements

**Development:**
- macOS/Linux with Python 3.12+
- Docker for local MSSQL database (Azure SQL Edge ARM64)
- ODBC Driver 18 for SQL Server

**Production:**
- Docker container deployment
- CI via GitHub Actions (`.github/workflows/ci.yml`)
- Docs via GitHub Pages (`.github/workflows/deploy-docs.yml`)

---

*Stack analysis: 2026-03-03*
*Update after major dependency changes*
