# External Integrations

**Analysis Date:** 2026-03-03

## APIs & External Services

**Payment Processing:**
- Not detected

**Email/SMS:**
- Not detected

**External APIs:**
- Not detected — fully self-contained system

## Data Storage

**Databases:**
- Microsoft SQL Server / Azure SQL Edge - Primary data store
  - Connection: via `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD` env vars (`api/config.py`)
  - Client: pyodbc 5.3.0 (`api/database.py`) — raw ODBC, no ORM
  - Driver: ODBC Driver 18 for SQL Server (hardcoded default in `api/config.py`)
  - Port: 14330:1433 (Docker mapping in `docker-compose.yml`)
  - Migrations: versioned SQL scripts in `migrations/` (v1.0.0 → v2.1.0)
  - Seed data: `sql/seed_v2.1.0.sql`

**File Storage:**
- Not detected

**Caching:**
- None (all queries hit database directly, no Redis or in-memory cache)

## Authentication & Identity

**Auth Provider:**
- None currently — SQL Server SA credentials for dev/CI
  - Dev SA password in `docker-compose.yml` (example/dev only: `StrongPwd123!`)
  - API has no user authentication layer

**OAuth Integrations:**
- Not detected

## Monitoring & Observability

**Error Tracking:**
- Not detected (no Sentry, Datadog, etc.)

**Analytics:**
- Not detected

**Health Check:**
- `GET /api/v1/health` — `api/v1/endpoints/health.py`
  - Queries `dbo.SchemaVersion` table to verify DB connectivity
  - Returns API version, DB status, schema version

**Logs:**
- stdout/stderr only — no structured logging service

## CI/CD & Deployment

**Hosting:**
- Docker container — `Dockerfile` (Python 3.11-slim base)
- No cloud hosting detected for API (local/self-hosted)

**CI Pipeline:**
- GitHub Actions — `.github/workflows/ci.yml`
  - Triggers: all branches and PRs
  - Steps: pytest suite, YAML schema validation, SQL generation smoke test
  - Run command: `uv run pytest --tb=short -q`

**Documentation Deployment:**
- GitHub Pages — `.github/workflows/deploy-docs.yml`
  - Triggers: main branch push
  - Builds mkdocs site, deploys to `https://modeleau.github.io/open_dateaubase/`

## Environment Configuration

**Development:**
- Required env vars: `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`
- Secrets location: `.env.local` (gitignored)
- Docker template: `.env.docker.example`
- ⚠️ Missing: general `.env.example` for non-Docker setups
- Database: Docker Compose (`docker-compose.yml` → Azure SQL Edge)

**Staging:**
- Not applicable (no staging environment detected)

**Production:**
- Secrets management: not defined in codebase (self-hosted assumed)

## Webhooks & Callbacks

**Incoming:**
- None detected

**Outgoing:**
- None detected

## OpenAPI / Built-in API Docs

- Swagger UI: `/docs`
- ReDoc: `/redoc`
- OpenAPI spec: `/openapi.json`
- All served by FastAPI automatically via `api/main.py`

---

*Integration audit: 2026-03-03*
*Update when adding/removing external services*
