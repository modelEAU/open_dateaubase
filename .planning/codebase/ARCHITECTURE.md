# Architecture

**Analysis Date:** 2026-03-03

## Pattern Overview

**Overall:** Layered REST API (3-tier)

**Key Characteristics:**
- Synchronous (no async/await — plain `def` endpoints, pyodbc)
- Dependency injection via FastAPI's `Depends()` for DB connections
- Repository pattern encapsulating all SQL
- Pydantic schemas at API boundary for validation and serialization
- Core library (`src/open_dateaubase/`) is FastAPI-agnostic

## Layers

**Endpoint Layer:**
- Purpose: Parse HTTP requests, inject dependencies, return HTTP responses
- Contains: Route handlers, FastAPI `APIRouter` definitions
- Location: `api/v1/endpoints/*.py`
- Depends on: Service layer and Repository layer
- Used by: FastAPI router (`api/v1/router.py`)

**Service Layer:**
- Purpose: Business logic, orchestration, error translation
- Contains: `TimeseriesService`, `LineageService`, `SensorStatusService`, `AnnotationService`
- Location: `api/v1/services/*.py`
- Depends on: Repository layer, core library (`open_dateaubase`)
- Used by: Endpoint layer

**Repository Layer:**
- Purpose: Encapsulate all SQL queries; return plain dicts
- Contains: `channel_repository`, `value_repository`, `ingestion_repository`, `annotation_repository`, `sensor_status_repository`, `site_repository`, `campaign_repository`, `equipment_repository`
- Location: `api/v1/repositories/*.py`
- Depends on: pyodbc connection (injected)
- Used by: Endpoints and services

**Schema Layer (Pydantic):**
- Purpose: Request/response contracts, validation
- Contains: `ChannelOut`, `SensorIngestRequest`, `LabIngestRequest`, `TimeseriesOut`, `AnnotationIn/Out`, `LineageOut`
- Location: `api/v1/schemas/*.py`
- Depends on: Pydantic
- Used by: Endpoint layer for parsing and serialization

**Core Library:**
- Purpose: Reusable domain logic independent of the API
- Contains: `lineage.py` (SQL lineage queries), `meteaudata_bridge.py` (processing provenance), `data_model/models.py` (Pydantic schema dict models), `data_model/helpers.py` (DictionaryManager)
- Location: `src/open_dateaubase/`
- Depends on: pyodbc, Pydantic only
- Used by: Service layer, schema tooling

## Data Flow

**HTTP Request (e.g., GET /channels/{id}):**

1. Client → `GET /api/v1/channels/{channel_id}`
2. FastAPI router → `api/v1/endpoints/channels.py:get_channel()`
3. `Depends(get_db)` → `api/database.py:get_db()` opens pyodbc connection
4. Endpoint calls `channel_repository.get_channel_by_id(conn, channel_id)`
5. Repository executes parameterized SQL with FK joins → returns `dict`
6. `ChannelOut.model_validate(row)` validates and serializes
7. FastAPI returns JSON; `get_db()` closes connection in `finally` block

**Data Ingestion (POST /ingest/sensor):**

1. Client → `POST /api/v1/ingest/sensor` with `SensorIngestRequest` body
2. `api/v1/endpoints/ingest.py:ingest_sensor()` validates request
3. `ingestion_repository.find_or_create_sensor_metadata(conn, ...)` — uses UNIQUE constraint `(Equipment_ID, Parameter_ID, DataProvenance_ID, ProcessingDegree_ID)` to auto-provision Channel row
4. `value_repository.insert_scalar_values(channel_id, values)` — bulk INSERT into `Value` table
5. Returns `IngestResponse(channel_id, rows_written)`

**Lineage Tracing (GET /lineage/{channel_id}/forward):**

1. Client → `GET /api/v1/lineage/{channel_id}/forward`
2. `api/v1/services/lineage_service.py:forward_lineage()` wraps `open_dateaubase.lineage.get_lineage_forward()`
3. Low-level SQL queries `DataLineage → ProcessingStep → DataLineage` joins
4. Returns list of processing steps with output channel IDs

**State Management:**
- Stateless — no in-memory state; every request opens/closes a DB connection
- All state in MSSQL database

## Key Abstractions

**Repository:**
- Purpose: Encapsulate SQL for a domain entity; return `list[dict]` or `dict | None`
- Examples: `api/v1/repositories/channel_repository.py`, `api/v1/repositories/value_repository.py`
- Pattern: Stateless functions accepting `conn: pyodbc.Connection`

**Pydantic Schema:**
- Purpose: Type-safe request/response boundary
- Examples: `ChannelOut` (`api/v1/schemas/channel.py`), `SensorIngestRequest` (`api/v1/schemas/ingestion.py`)
- Pattern: BaseModel with snake_case fields; `PaginatedResponse[T]` for lists

**Value Type Dispatch:**
- Purpose: Route timeseries queries to correct table based on `ValueType_ID`
- Location: `api/v1/services/timeseries_service.py`
- Pattern: Dispatch dict `{1: scalar_fn, 2: vector_fn, 3: matrix_fn, 4: image_fn}`

**Auto-Provision Sensor Stream:**
- Purpose: Idempotent Channel row creation on first ingest
- Location: `api/v1/repositories/ingestion_repository.py:find_or_create_sensor_metadata()`
- Pattern: UNIQUE constraint on `(Equipment_ID, Parameter_ID, DataProvenance_ID, ProcessingDegree_ID)` — INSERT IF NOT EXISTS

**Lineage Bridge:**
- Purpose: Record processing provenance from ingestion to DB
- Location: `src/open_dateaubase/meteaudata_bridge.py:record_processing()`
- Pattern: Inserts `ProcessingStep` + `DataLineage` rows to enable forward/backward lineage tracing

## Entry Points

**API Server:**
- Location: `api/main.py`
- Triggers: `uv run uvicorn api.main:app --reload`
- Responsibilities: FastAPI app factory, mount v1 router, configure OpenAPI docs

**v1 Router:**
- Location: `api/v1/router.py`
- Triggers: FastAPI include_router
- Responsibilities: Mount all feature routers under `/api/v1`

## Error Handling

**Strategy:** Raise `HTTPException` at endpoint/service level; repositories return None for not-found

**Patterns:**
- Repositories return `None` for missing rows; endpoints raise `HTTPException(404)`
- Services catch domain exceptions and re-raise as `HTTPException(500)` (sometimes too broad)
- `api/database.py` raises `HTTPException(503)` on connection failure
- Pydantic validation errors automatically return `422 Unprocessable Entity`

## Cross-Cutting Concerns

**Logging:**
- None configured — stdout/stderr only; no structured logger

**Validation:**
- Pydantic schemas at API boundary (request parsing, response serialization)
- Pydantic discriminated union models in `src/open_dateaubase/data_model/models.py` for schema dictionary

**Authentication:**
- None — no auth middleware; API is open

**Database Connection:**
- `Depends(get_db)` injects pyodbc connection per request
- Connection closed in `finally` block of `get_db()` generator
- Tests override via `app.dependency_overrides[get_db]`

---

*Architecture analysis: 2026-03-03*
*Update when major patterns change*
