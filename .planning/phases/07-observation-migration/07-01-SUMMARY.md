---
phase: 07-observation-migration
plan: "01"
subsystem: schema-migration
tags: [sql, migration, observation, value, mssql]
dependency_graph:
  requires: [v2.1.0 schema baseline]
  provides: [Observation table DDL, Value restructure DDL (Steps 1-2 of 5), rollback script]
  affects: [migrations/, schema_dictionary/version.yaml]
tech_stack:
  added: []
  patterns: [single-transaction migration, schema guards, backfill-before-drop]
key_files:
  created:
    - migrations/v2.1.0_to_v2.2.0_mssql.sql
    - migrations/v2.1.0_to_v2.2.0_mssql_rollback.sql
  modified:
    - schema_dictionary/version.yaml
decisions:
  - "Observation(Observation_ID BIGINT IDENTITY PK, Channel_ID INT FK, Timestamp DATETIME2(7), DataType VARCHAR(10)) with UNIQUE on (Channel_ID, Timestamp, DataType) and CHECK on DataType IN ('Scalar','Vector','Matrix','Image')"
  - "Value table restructured: drop Value_ID+Channel_ID+Timestamp; Observation_ID becomes sole PK with FK→Observation"
  - "Added rollback script per CLAUDE.md requirement; bumped version.yaml to 2.2.0 to satisfy CI test"
  - "Transaction intentionally left open — COMMIT only in 07-03 after all steps complete"
metrics:
  duration_seconds: 124
  completed_date: "2026-03-16"
  tasks_completed: 2
  files_created: 2
  files_modified: 1
---

# Phase 07 Plan 01: Observation Table + Value Restructure — Summary

Partial forward migration (Steps 1-2 of 5) creating the Observation hub table and restructuring the scalar Value table as a lean payload keyed by Observation_ID, with a duplicate-check guard and safe backfill-before-drop ordering.

## Accomplishments

- Created `migrations/v2.1.0_to_v2.2.0_mssql.sql` with:
  - STEP 1: Observation table (4 columns, PK, UNIQUE, FK→Channel, CHECK constraint, covering index)
  - STEP 2: Value table restructure (duplicate check, Observation backfill, add/populate/NOT NULL Observation_ID, drop old FK/PK/columns, new PK+FK)
- Created `migrations/v2.1.0_to_v2.2.0_mssql_rollback.sql` (reversal of Steps 1-2)
- Bumped `schema_dictionary/version.yaml` to 2.2.0
- All 140 tests pass

## Files Created/Modified

| File | Action |
|------|--------|
| `migrations/v2.1.0_to_v2.2.0_mssql.sql` | Created (120 lines, Steps 1-2, transaction open) |
| `migrations/v2.1.0_to_v2.2.0_mssql_rollback.sql` | Created (81 lines, reverses Steps 1-2) |
| `schema_dictionary/version.yaml` | Updated 2.1.0 → 2.2.0 |

## Decisions Made

- Transaction stays open across 07-01 through 07-03; COMMIT only in 07-03
- Dynamic PK name lookup via `sys.key_constraints` for safety (plan spec requirement)
- Duplicate (Channel_ID, Timestamp) check added before INSERT INTO Observation to prevent UQ violation

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical File] Added rollback script and version.yaml update**
- **Found during:** Task 2 (test run)
- **Issue:** `test_every_migration_has_a_rollback` failed (no rollback script exists); `test_version_yaml_matches_latest_migration_target` failed (version.yaml still at 2.1.0)
- **Fix:** Created `v2.1.0_to_v2.2.0_mssql_rollback.sql` (reverses Steps 1-2 of migration); updated `schema_dictionary/version.yaml` to 2.2.0
- **Files modified:** migrations/v2.1.0_to_v2.2.0_mssql_rollback.sql (created), schema_dictionary/version.yaml
- **Commit:** d7816c7

## Issues Encountered

None blocking. The CI schema tests caught the missing rollback file and version mismatch, which were resolved immediately (both required by CLAUDE.md).

## Next Step

Ready for 07-02-PLAN.md — ValueVector, ValueMatrix, ValueImage restructure (Steps 3-4 of 5).

## Self-Check: PASSED

- [x] `migrations/v2.1.0_to_v2.2.0_mssql.sql` — FOUND
- [x] `migrations/v2.1.0_to_v2.2.0_mssql_rollback.sql` — FOUND
- [x] `schema_dictionary/version.yaml` — FOUND (2.2.0)
- [x] Commit 3bf961f — FOUND
- [x] Commit d7816c7 — FOUND
- [x] 140 tests pass
