---
phase: 07-observation-migration
plan: "02"
subsystem: schema-migration
tags: [sql, migration, observation, valuevector, valuematrix, valueimage, mssql]
dependency_graph:
  requires: [07-01 Observation table + Value restructure (Steps 1-2)]
  provides: [ValueVector restructure DDL (Step 3), ValueMatrix restructure DDL (Step 4), ValueImage restructure DDL (Step 5)]
  affects: [migrations/v2.1.0_to_v2.2.0_mssql.sql]
tech_stack:
  added: []
  patterns: [backfill-before-drop, DISTINCT INSERT for multi-row-per-observation tables, identity-column drop via PK-first ordering]
key_files:
  created: []
  modified:
    - migrations/v2.1.0_to_v2.2.0_mssql.sql (Steps 3-5 appended, 173 lines added)
decisions:
  - "ValueVector/ValueMatrix use SELECT DISTINCT on (Channel_ID, Timestamp) for backfill — one Observation row per unique observation event, not per bin row"
  - "ValueImage skips DISTINCT — UQ_ValueImage_ChannelTimestamp already enforces one row per Channel/Timestamp pair"
  - "ValueImage constraint drop order: UQ_ChannelTimestamp -> FK_Channel -> PK_ValueImage -> DROP IDENTITY column (PK must precede IDENTITY drop)"
  - "FK_ValueVector_ValueBin, FK_ValueMatrix_RowValueBin, FK_ValueMatrix_ColValueBin preserved — bin columns are payload, not navigation"
  - "Transaction remains open — COMMIT deferred to 07-03 after all five steps complete"
metrics:
  duration_seconds: 1219
  completed_date: "2026-03-16"
  tasks_completed: 2
  files_created: 0
  files_modified: 1
---

# Phase 07 Plan 02: ValueVector + ValueMatrix + ValueImage Restructure — Summary

SQL migration Steps 3–5 appended: ValueVector/ValueMatrix restructured as composite-keyed payloads via DISTINCT backfill; ValueImage swaps IDENTITY PK for Observation_ID with correct UQ→FK→PK drop ordering.

## Accomplishments

- Appended STEP 3 to `migrations/v2.1.0_to_v2.2.0_mssql.sql`:
  - Backfills Observation from ValueVector (SELECT DISTINCT — bins share a single Observation row)
  - Drops composite PK `(Channel_ID, Timestamp, ValueBin_ID)` and `FK_ValueVector_Channel`
  - Drops Channel_ID + Timestamp columns
  - Adds new composite PK `(Observation_ID, ValueBin_ID)` and `FK_ValueVector_Observation`
  - `FK_ValueVector_ValueBin` preserved
- Appended STEP 4 for ValueMatrix (identical pattern, 3-column composite PK):
  - New PK: `(Observation_ID, RowValueBin_ID, ColValueBin_ID)`
  - `FK_ValueMatrix_RowValueBin` and `FK_ValueMatrix_ColValueBin` preserved
- Appended STEP 5 for ValueImage:
  - No DISTINCT needed (uniqueness enforced by pre-existing `UQ_ValueImage_ChannelTimestamp`)
  - Correct constraint drop order: UQ → FK_Channel → PK → DROP IDENTITY column → DROP Channel_ID/Timestamp
  - New sole PK: `Observation_ID`; new `FK_ValueImage_Observation`
- All 251 non-integration tests pass (same 6 pre-existing failures, same 4 pyodbc connection errors as baseline)

## Files Created/Modified

| File | Action |
|------|--------|
| `migrations/v2.1.0_to_v2.2.0_mssql.sql` | Modified (173 lines appended, Steps 3-5, transaction still open) |

## Decisions Made

- `SELECT DISTINCT` for ValueVector/ValueMatrix backfill: the source tables have N rows per observation (one per bin), but Observation needs exactly one row per (Channel_ID, Timestamp, DataType).
- ValueImage skips `DISTINCT` because its `UQ_ValueImage_ChannelTimestamp` guarantees uniqueness.
- Constraint drop order for ValueImage follows MSSQL requirements: UNIQUE constraint dropped before the FK constraint, then the PK constraint must be dropped before the IDENTITY column can be removed.
- Bin-level FK constraints preserved — ValueBin_ID / RowValueBin_ID / ColValueBin_ID are structural payload columns, not redundant navigation columns.

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None blocking.

## Next Step

Ready for 07-03-PLAN.md — Annotation Observation_ID FK addition (Step 6) and COMMIT.

## Self-Check

- [x] `migrations/v2.1.0_to_v2.2.0_mssql.sql` — FOUND (294 lines)
- [x] STEP 3 block present (ValueVector, lines 122–175)
- [x] STEP 4 block present (ValueMatrix, lines 177–231)
- [x] STEP 5 block present (ValueImage, lines 233–293)
- [x] No COMMIT in file — confirmed via grep
- [x] Commit 01571b0 — Task 1 (Steps 3-4)
- [x] Commit e88b673 — Task 2 (Step 5)
- [x] 251 tests pass (baseline unchanged)
