# Codebase Concerns

**Analysis Date:** 2026-03-03

## Tech Debt

**~~Schema drift in core lineage library~~ [FIXED 2026-03-03]:**
- ~~Issue: `src/open_dateaubase/lineage.py` references `[dbo].[DataLineage]` and `[Role]` column; v2.1.0 renamed these to `ProcessingLineage` and `RoleInProcessingStep`~~
- ~~Also: `src/open_dateaubase/meteaudata_bridge.py:56` references `c.[ProcessingDegree]` as a string column, but v2.1.0 changed it to `ProcessingDegree_ID` (integer FK)~~
- Fixed in commits `a71793c` (lineage.py) and `2b5e8e4` (meteaudata_bridge.py): all SQL updated to v2.1.0 table/column names; `ProcessingDegree` now resolved via JOIN to `ProcessingDegree` lookup table

**~~Migration SQL and seed data out of sync with v2.1.0 spec~~ [FIXED 2026-03-03]:**
- ~~Issue: `migrations/v1.0.0_to_v2.1.0_mssql.sql` contains v1-era column names and missing tables; `sql/seed_v2.1.0.sql` references removed columns (`Unit_ID`, `ProcessingDegree` as string, `StartDate`/`EndDate`)~~
- Fixed in commits `9fe903b` (migration SQL) and `b517a93` (seed SQL): all PascalCase column renames applied; `SamplingPoints`→`SamplingPoint` rename added as STEP 11; lookup table columns and FK constraints corrected; `AnalyzedAt`→`AnalysisDateTime` in LabAnalysis

**~~Schema version mismatch in config~~ [FIXED 2026-03-03]:**
- ~~Issue: `api/config.py:34` — `schema_version: str = "1.6.0"` but current schema is v2.1.0~~
- Fixed in commit `22d38c3`: updated to `"2.1.0"`

**Dynamic SQL construction via f-strings:**
- Issue: WHERE clauses in paginated list queries built with f-string interpolation
- Files: `api/v1/repositories/channel_repository.py:79`, `api/v1/repositories/metadata_repository.py:87`, `api/v1/repositories/annotation_repository.py:361`
- Why: Dynamic filtering without ORM requires conditional clause building
- Impact: Brittle; could become SQL injection vector if modified carelessly
- Fix approach: Use an explicit clause-builder helper or stored procedures

**No connection pooling:**
- Issue: `api/database.py` opens a new pyodbc connection per HTTP request; no pool
- Impact: Under load, connection overhead adds latency; may hit MSSQL connection limits
- Fix approach: Add `pyodbc` connection pool or move to `aioodbc` / SQLAlchemy pool

## Known Bugs

**Incomplete annotation author field:**
- Symptoms: `author_person_id` in `api/v1/schemas/annotations.py:54` accepts manual input with `# TODO: replace with auth context`
- Trigger: Any POST to `/annotations`
- Workaround: Clients manually pass the author's person ID
- Root cause: No authentication layer exists yet to derive user identity
- Blocked by: Auth implementation

## Security Considerations

**No API authentication:**
- Risk: All API endpoints are open; no JWT, API key, or session validation
- Current mitigation: None (assumed internal/private deployment)
- Recommendations: Add authentication middleware before any external exposure

**Unsafe `cursor.fetchone()[0]` index access:**
- Risk: Direct index access on query results without None-check
- Files: `api/v1/repositories/ingestion_repository.py:55, 125, 156`, `api/v1/repositories/channel_repository.py:82`
- Current mitigation: COUNT query always returns a row; INSERT RETURNING usually works
- Recommendations: Add explicit `if row is None: raise` checks or use `(row or (None,))[0]` pattern

**SA credentials in docker-compose.yml:**
- Risk: Dev SA password visible in version-controlled config file
- Files: `docker-compose.yml`
- Current mitigation: Clearly example/dev-only (`StrongPwd123!`)
- Recommendations: Use `.env` reference in docker-compose instead of inline value

## Performance Bottlenecks

**No caching layer:**
- Problem: All reads hit MSSQL directly; no Redis or in-memory cache
- Cause: Architecture decision (simplicity)
- Improvement path: Add read cache for lookup tables (ProcessingDegree, QualityCode, etc.) that change rarely

**No connection pooling:**
- Problem: New pyodbc connection opened per request
- Measurement: Not measured; becomes relevant under concurrent load
- Improvement path: Implement connection pool in `api/database.py`

## Fragile Areas

**`src/open_dateaubase/lineage.py` and `meteaudata_bridge.py`:**
- Why fragile: SQL references to schema-specific column/table names not validated at startup
- Common failures: Silent wrong-column errors or SQL exceptions at runtime after schema migration
- Safe modification: Always run integration tests (`pytest -m db`) after schema changes
- Test coverage: Integration tests in `tests/integration/` but not specifically for lineage SQL names
- Note [2026-03-03]: SQL updated to v2.1.0 names (commits `a71793c`, `2b5e8e4`); fragility concern remains for future schema changes

**`api/v1/repositories/annotation_repository.py` (400+ lines):**
- Why fragile: Complex dynamic SQL construction with multiple UPDATE paths; large file
- Common failures: Dynamic SET clause building (`', '.join(set_parts)`) is hard to test exhaustively
- Safe modification: Add contract tests for each update variant before changing
- Test coverage: `tests/api/contract/test_annotation_endpoints.py` (partial)

**`tests/legacy/` directory:**
- Why fragile: Pre-v2.0 import errors; running `pytest` without marker filtering may include them
- Common failures: Import errors on unrelated test runs
- Safe modification: Always filter with `uv run pytest --ignore=tests/legacy/` or `uv run pytest -m "not legacy"`
- Test coverage: Not maintained

## Scaling Limits

**MSSQL on Docker (dev):**
- Current capacity: Single container, no replication
- Limit: Development only — not a production concern
- Scaling path: Use managed Azure SQL / SQL Server for production

## Dependencies at Risk

**Legacy `tests/legacy/` imports:**
- Risk: Python path and import errors block full suite without filtering
- Impact: CI currently passes because test runner likely ignores errors or uses markers
- Migration plan: Either fix imports or add `pytest.ini` exclude for legacy/

## Missing Critical Features

**Authentication / Authorization:**
- Problem: No user identity in API; `author_person_id` in annotations is caller-supplied
- Current workaround: Manual `person_id` parameter; internal/trusted clients only
- Blocks: Multi-user deployments, data provenance integrity
- Implementation complexity: Medium (add FastAPI middleware + token validation)

**`.env.example` for development setup:**
- Problem: No template for required environment variables for non-Docker setups
- Current workaround: Only `.env.docker.example` exists; developers must infer vars from `api/config.py`
- Blocks: Developer onboarding
- Implementation complexity: Low (create `.env.example` with placeholder values)

## Test Coverage Gaps

**Lineage SQL correctness:**
- What's not tested: That `src/open_dateaubase/lineage.py` SQL matches v2.1.0 schema
- Risk: Lineage endpoints silently broken after schema migration
- Priority: Medium (SQL has been updated to v2.1.0 names as of 2026-03-03; known drift is resolved)
- Difficulty to test: Requires integration DB; run `pytest -m db` targeting lineage endpoint

**`find_or_create_sensor_metadata()` idempotency:**
- What's not tested: DB-level UNIQUE constraint behavior — only mock-level contract tests exist
- Risk: Could create duplicate Channel rows or fail silently if UNIQUE constraint changes
- Priority: Medium
- Difficulty to test: Requires integration DB with real schema

**Migration rollback:**
- What's not tested: Whether rollback script correctly reverses v2.1.0 forward migration
- Risk: Data loss or schema corruption if rollback needed in production
- Priority: High (per project CLAUDE.md: every schema change must have rollback)
- Difficulty to test: Requires integration DB with v2.1.0 schema

---

*Concerns audit: 2026-03-03*
*Update as issues are fixed or new ones discovered*
