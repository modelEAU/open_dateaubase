---
phase: "07-observation-migration"
plan: "05"
subsystem: "api-repositories"
tags: ["observation", "ingestion", "value-repository", "sql", "two-step-insert"]
dependency_graph:
  requires: ["07-03-PLAN.md", "07-04-PLAN.md"]
  provides: ["updated value_repository.py", "updated ingestion_repository.py"]
  affects: ["api/v1/repositories/value_repository.py", "api/v1/repositories/ingestion_repository.py"]
tech_stack:
  added: []
  patterns: ["OUTPUT INSERTED.[Observation_ID] for identity retrieval", "two-step Observation+payload insert"]
key_files:
  created: []
  modified:
    - "api/v1/repositories/value_repository.py"
    - "api/v1/repositories/ingestion_repository.py"
decisions:
  - "Two-step insert pattern: INSERT Observation (OUTPUT INSERTED.Observation_ID) then INSERT payload — consistent with existing LabAnalysis pattern in ingestion_repository.py"
  - "insert_image_value now returns Observation_ID (was ValueImage_ID via SELECT @@IDENTITY) — semantics unchanged since callers only use the returned ID for confirmation"
  - "get_last_timestamp_for_channel: switched from dbo.Value join to dbo.Observation join — Value no longer holds Timestamp after schema migration"
metrics:
  duration: "~3m 20s"
  completed_date: "2026-03-16"
  tasks_completed: 2
  files_modified: 2
---

# Phase 07 Plan 05: API Ingestion Path — Observation Two-Step Insert Pattern

All four insert functions and the last-timestamp query updated to use Observation hub table: `insert_scalar_values`, `insert_vector_values`, `insert_matrix_values`, and `insert_image_value` now create an Observation row first (capturing Channel_ID + Timestamp + DataType) and then insert the payload row keyed only by Observation_ID.

## Accomplishments

- `insert_scalar_values`: two-step insert — Observation then Value(Observation_ID, Value)
- `insert_vector_values`: Observation created per observation in outer loop; ValueVector uses (Observation_ID, ValueBin_ID, Value, QualityCode)
- `insert_matrix_values`: same pattern; ValueMatrix uses (Observation_ID, RowValueBin_ID, ColValueBin_ID, Value, QualityCode)
- `insert_image_value`: Observation then ValueImage(Observation_ID, ...); returns Observation_ID instead of ValueImage_ID via SELECT @@IDENTITY
- `get_last_timestamp_for_channel`: queries `dbo.Observation` joined to `dbo.Channel` — Value no longer holds Timestamp

## Files Created/Modified

| File | Change |
|------|--------|
| `api/v1/repositories/value_repository.py` | Updated 4 insert functions to two-step Observation pattern |
| `api/v1/repositories/ingestion_repository.py` | Updated get_last_timestamp_for_channel to query via Observation |

## Decisions Made

1. **OUTPUT INSERTED.[Observation_ID] pattern** — used consistently, matching the existing LabAnalysis pattern in ingestion_repository.py. The `SELECT @@IDENTITY` approach used by insert_image_value was replaced to be consistent.
2. **insert_image_value return value** — now returns Observation_ID (was returning ValueImage identity via SELECT @@IDENTITY). Semantics for callers remain unchanged.
3. **timestamp local var in insert_matrix_values** — assigned at loop start but obs["timestamp"] also used directly in the Observation INSERT (both are equivalent; consistency improved).

## Issues Encountered

- Pre-existing test failures in `tests/schema/test_sensor_status_yaml.py` (SensorStatusCode YAML missing) — confirmed pre-existing, out of scope, not fixed.
- No issues with the plan's target functions.

## Deviations from Plan

None — plan executed exactly as written.

## Self-Check

- [x] `insert_scalar_values` — INSERT Observation first, then INSERT Value(Observation_ID, Value)
- [x] `insert_vector_values` — INSERT Observation per observation, then INSERT ValueVector(Observation_ID, ...)
- [x] `insert_matrix_values` — INSERT Observation per observation, then INSERT ValueMatrix(Observation_ID, ...)
- [x] `insert_image_value` — INSERT Observation first, then INSERT ValueImage(Observation_ID, ...)
- [x] `get_last_timestamp_for_channel` — queries dbo.Observation, not dbo.Value
- [x] All OUTPUT INSERTED.[Observation_ID] patterns use cursor.fetchone()[0]
- [x] 153 unit/contract tests pass (integration tests excluded — no DB)

## Next Step

Ready for 07-06-PLAN.md (integration + contract test updates for the new Observation-based schema)
