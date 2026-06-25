# datEAUbase

This repo contains the reference implementation of the dat*EAU*base relational database and data model for use in water resource recovery facilities (WRRFs). The purpose of dat*EAU*base is to allow WRRF data to be stored *along with their context* to ensure that they are correctly interpreted in data mining, modelling and decision support activities. The data model is described in [Plana et al. (2019)](https://iwaponline.com/wqrj/article/54/1/1/64706/Towards-a-water-quality-database-for-raw-and).

📖 **[Read the documentation](https://modelEAU.github.io/open_dateaubase/)** — tutorials, how-to guides, API reference, and schema docs.

## Quick Start (Docker)

Run the full stack (database + API + web app) with a single command:

```bash
# 1. Copy and edit env file for Docker
cp .env.docker.example .env.docker
# Edit .env.docker: set DB_PASSWORD to a strong password

# 2. Start the database
docker-compose up -d db

# 3. Initialize the schema (first time only)
docker-compose --profile init up db-init

# 4. Start the API and web app
docker-compose up -d api app

# 5. Open the app
# Web app:  http://localhost:8501
# API docs: http://localhost:8000/docs
```

## Local Development

### Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) — fast Python package manager
- Docker (for the MSSQL database)
- ODBC Driver 18 for SQL Server ([install guide](https://learn.microsoft.com/en-us/sql/connect/odbc/linux-mac/installing-the-microsoft-odbc-driver-for-sql-server))

### Setup

```bash
# Install all dependencies (API + app + dev tools)
uv sync --extra api --extra app --extra dev

# Copy and configure your env file
cp .env.example .env.local
# Edit .env.local: set DB_HOST=localhost, DB_PORT=14330, DB_NAME=..., etc.

# Start the database container
docker-compose up -d db

# Initialize the schema (first time only)
docker-compose --profile init up db-init

# Start the API server
uv run uvicorn api.main:app --reload

# In a new terminal, start the Streamlit app
uv run streamlit run app/Home.py
```

The app will be available at <http://localhost:8501> and the API at <http://localhost:8000/docs>.

### Run Tests

```bash
uv run pytest                    # all tests
uv run pytest tests/unit/        # unit tests only (no DB required)
uv run pytest -m db              # integration tests (requires running DB)
```

### Build the Docs

```bash
uv run mkdocs serve   # local preview at http://localhost:8000
uv run mkdocs build   # build static site to site/
```

## Repository Structure

- `api/` — FastAPI REST API (endpoints, services, repositories, schemas)
- `app/` — Streamlit multipage web application
- `sql/` — Database initialization and seed SQL scripts
- `migrations/` — Schema migration scripts (v1.0.0 → v2.1.0)
- `schema_dictionary/` — YAML definitions for all tables and columns
- `src/open_dateaubase/` — Core Python library (data models, lineage, processing)
- `tests/` — Unit, API contract, and integration tests
- `docs/` — MkDocs documentation source
- `sql_generation_scripts/` — Versioned CREATE TABLE scripts

## License

dat*EAU*base is published under the CC-BY 4.0 license.
