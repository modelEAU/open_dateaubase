---
phase: 07-observation-migration
plan: "03"
subsystem: schema-migration
tags: [sql, migration, rollback, observation, annotation, views, mssql]
dependency_graph:
  requires: [07-02 ValueVector/ValueMatrix/ValueImage restructure (Steps 3-5)]
  provides: [Complete forward migration (Steps 6-8), complete rollback script (9 steps)]
  affects: [migrations/v2.1.0_to_v2.2.0_mssql.sql, migrations/v2.1.0_to_v2.2.0_mssql_rollback.sql]
tech_stack:
  added: []
  patterns: [ROW_NUMBER synthetic surrogate pattern for IDENTITY column restoration, DROP-views-before-Value / recreate-after-Value rollback ordering]
key_files:
  created: []
  modified:
    - migrations/v2.1.0_to_v2.2.0_mssql.sql (Steps 6-8 appended, 70 lines added, transaction committed)
    - migrations/v2.1.0_to_v2.2.0_mssql_rollback.sql (complete rewrite, all 9 rollback steps, 232 lines net added)
decisions:
  - "Rollback naming: use mssql_rollback.sql suffix (not rollback_mssql.sql) to satisfy CI test test_every_migration_has_a_rollback which derives rollback name as {forward_stem}_rollback.sql"
  - "Annotation.Observation_ID: nullable BIGINT FK to Observation, no other Annotation columns changed"
  - "vw_ChannelStatus and vw_DeviceStatus: updated to join Value->Observation->Channel (via o.Timestamp, not v.Timestamp)"
  - "Rollback views: dropped before Value is touched (Step 1), recreated with v2.1.0 Channel_ID join path after Value is restored (Step 8)"
  - "Rollback Value_ID/ValueImage_ID: synthetic surrogates via ROW_NUMBER (SQL Server cannot ADD IDENTITY to existing columns)"
metrics:
  duration_seconds: 420
  completed_date: "2026-03-16"
  tasks_completed: 2
  files_created: 0
  files_modified: 2
---

# Phase 07 Plan 03: Migration Finalization + Rollback Script — Summary

Complete forward migration (Steps 1-8, COMMIT) and full 9-step rollback script for the v2.2.0 Observation hub migration, including Annotation nullable FK, updated status views joined through Observation, and synthetic surrogate ID restoration for Value and ValueImage.

## Accomplishments

- Appended STEP 6, STEP 7, STEP 8 to `migrations/v2.1.0_to_v2.2.0_mssql.sql`:
  - STEP 6: `ALTER TABLE Annotation ADD Observation_ID BIGINT NULL` + `FK_Annotation_Observation`
  - STEP 7: `CREATE OR ALTER VIEW vw_ChannelStatus` and `vw_DeviceStatus` — both now join `Value -> Observation -> Channel` using `o.[Timestamp]`
  - STEP 8: `INSERT INTO SchemaVersion` ('2.2.0') + `COMMIT TRANSACTION` + PRINT
- Rewrote `migrations/v2.1.0_to_v2.2.0_mssql_rollback.sql` with complete 9-step rollback:
  - Step 1: Drop views (before Value is touched)
  - Step 2: Drop `Annotation.Observation_ID` FK + column
  - Steps 3-5: Restore ValueImage/ValueMatrix/ValueVector (backfill Channel_ID+Timestamp from Observation, restore PKs/FKs)
  - Step 6: Restore Value (backfill Channel_ID+Timestamp, synthetic Value_ID via ROW_NUMBER)
  - Step 7: Drop Observation table (all FKs removed)
  - Step 8: Recreate views with v2.1.0 `Value.Channel_ID` join path
  - Step 9: Insert SchemaVersion '2.1.0' + COMMIT
- All 140 non-integration tests pass

## Files Created/Modified

| File | Action |
|------|--------|
| `migrations/v2.1.0_to_v2.2.0_mssql.sql` | Modified (70 lines appended, Steps 6-8, transaction COMMITTED) |
| `migrations/v2.1.0_to_v2.2.0_mssql_rollback.sql` | Modified (complete rewrite, 232 net lines added, 9 rollback steps) |

## Decisions Made

- **Rollback filename**: Kept `mssql_rollback.sql` suffix (not `rollback_mssql.sql` as stated in plan) because `test_every_migration_has_a_rollback` derives the rollback filename as `{forward_stem}_rollback.sql`. Creating `rollback_mssql.sql` would be misidentified as a forward migration and itself require a rollback file.
- **View ordering in rollback**: Views dropped in Step 1 (before Value), recreated in Step 8 (after Value restored). This avoids broken object references during the rollback window.
- **Observation_ID column sequence in rollback**: FK dropped, then PK dropped, then IDENTITY column dropped — must drop PK before IDENTITY (SQL Server requirement, established in 07-02 for ValueImage forward direction).
- **ROW_NUMBER for Value_ID/ValueImage_ID**: SQL Server cannot `ALTER TABLE ... ADD col BIGINT IDENTITY` on an existing table without recreating it. ROW_NUMBER generates sequential surrogates; original IDENTITY values are unrecoverable. Documented clearly in rollback header comment.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Rollback filename corrected to match CI test expectation**
- **Found during:** Task 2 (examining `test_schema_ci.py::test_every_migration_has_a_rollback`)
- **Issue:** Plan specified canonical name `v2.1.0_to_v2.2.0_rollback_mssql.sql`, but CI test derives rollback name as `{forward_stem}_rollback.sql` = `v2.1.0_to_v2.2.0_mssql_rollback.sql`. The plan-specified name would also be treated as a forward migration (matches `v*_to_v*.sql` glob, no `_rollback` substring) and require its own rollback file.
- **Fix:** Created complete rollback content in `v2.1.0_to_v2.2.0_mssql_rollback.sql`; deleted the misnamed `v2.1.0_to_v2.2.0_rollback_mssql.sql`. The `mssql_rollback.sql` file already existed (partial, from 07-01) and was rewritten with the complete 9-step content.
- **Files modified:** `migrations/v2.1.0_to_v2.2.0_mssql_rollback.sql` (rewritten), `migrations/v2.1.0_to_v2.2.0_rollback_mssql.sql` (deleted, never committed)

## Issues Encountered

None blocking. CI test constraint on rollback naming was caught before committing, resolved by auto-fix.

## Next Step

Ready for 07-05-PLAN.md — API repository updates (value_repository.py + ingestion_repository.py to use Observation_ID).

## Self-Check: PASSED

- [x] `migrations/v2.1.0_to_v2.2.0_mssql.sql` ends with COMMIT TRANSACTION + PRINT — CONFIRMED (lines 360-363)
- [x] `vw_ChannelStatus` joins via `o.[Timestamp]` not `v.[Timestamp]` — CONFIRMED (lines 322)
- [x] `vw_DeviceStatus` joins via `o.[Timestamp]` not `v.[Timestamp]` — CONFIRMED (line 338)
- [x] Both views join Value -> Observation -> Channel — CONFIRMED
- [x] Annotation block has only ADD column + ADD CONSTRAINT — CONFIRMED (lines 300-307)
- [x] SchemaVersion INSERT uses '2.2.0' — CONFIRMED (line 353)
- [x] `migrations/v2.1.0_to_v2.2.0_mssql_rollback.sql` exists — CONFIRMED
- [x] Rollback drops views (Step 1) before altering Value (Step 6) — CONFIRMED
- [x] Rollback drops Observation (Step 7) after all FK references removed (Steps 3-6) — CONFIRMED
- [x] WARNING note about synthetic surrogate IDs present — CONFIRMED
- [x] 140 non-integration tests pass — CONFIRMED
- [x] Commit 2a605af (Task 1) — CONFIRMED
- [x] Commit a2f794e (Task 2) — CONFIRMED
