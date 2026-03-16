---
phase: "07-observation-migration"
plan: "06"
subsystem: "api-repositories, sql-baseline"
tags: ["observation", "read-path", "value-repository", "sql-baseline", "v2.2.0"]
dependency_graph:
  requires: ["07-05-PLAN.md"]
  provides: ["updated value_repository.py read path", "v2.2.0 baseline CREATE script"]
  affects:
    - "api/v1/repositories/value_repository.py"
    - "sql_generation_scripts/v2.2.0_create_mssql.sql"
tech_stack:
  added: []
  patterns: ["JOIN Observation for all read queries", "o.[Channel_ID]/o.[Timestamp] as filter anchors"]
key_files:
  created:
    - "sql_generation_scripts/v2.2.0_create_mssql.sql"
  modified:
    - "api/v1/repositories/value_repository.py"
decisions:
  - "All read filters route through o.[Channel_ID] and o.[Timestamp] — payload tables have no Channel_ID or Timestamp to filter on after migration"
  - "operational_only subquery aliases: so=status Observation, sv=status Value, o=outer main Observation — avoids name collision with v (scalar Value)"
  - "v2.2.0 baseline positions Observation CREATE before all four payload tables to satisfy FK dependency order"
metrics:
  duration: "~5m 10s"
  completed_date: "2026-03-16"
  tasks_completed: 2
  files_modified: 1
  files_created: 1
---

# Phase 07 Plan 06: API Query Read Path + v2.2.0 Baseline Script — Summary

All six get_* read functions in value_repository.py now join through the Observation hub table, and a clean v2.2.0 baseline CREATE script is ready for fresh DB initialization.

## Accomplishments

- `get_scalar_values`: WHERE and ORDER BY now reference `o.[Channel_ID]` / `o.[Timestamp]`; JOIN Observation on `Observation_ID` added; `operational_only` subquery rewritten with `so`/`sv` aliases through Observation
- `get_vector_values`: JOIN Observation added; `vv.[Channel_ID]` / `vv.[Timestamp]` refs removed
- `get_matrix_values`: JOIN Observation added; `vm.[Channel_ID]` / `vm.[Timestamp]` refs removed
- `get_image_values`: JOIN Observation added; `vi.[Channel_ID]` / `vi.[Timestamp]` refs removed
- `get_image_thumbnail`: now SELECT via ValueImage JOIN Observation WHERE o.[Channel_ID]/o.[Timestamp]
- `get_image_metadata_by_timestamp`: same Observation join pattern
- `get_values_for_metadata`: dispatcher unchanged — still delegates to the above updated functions
- `sql_generation_scripts/v2.2.0_create_mssql.sql`: complete fresh-install script with Observation hub, restructured Value/ValueVector/ValueMatrix/ValueImage, Annotation.Observation_ID nullable FK, and updated views

## Files Created/Modified

| File | Change |
|------|--------|
| `api/v1/repositories/value_repository.py` | Updated 6 get_* functions — read path fully routes through Observation |
| `sql_generation_scripts/v2.2.0_create_mssql.sql` | New clean baseline CREATE script for schema v2.2.0 |

## Decisions Made

1. **Observation join order** — Observation table placed after Channel and before all payload tables in the baseline script to satisfy FK dependency order.
2. **operational_only alias naming** — `so` (status Observation) and `sv` (status Value) chosen to avoid collision with outer query aliases `v` (Value) and `o` (Observation).
3. **ValueMatrix/ValueVector FKs inlined** — in the baseline script, ValueMatrix and ValueVector FKs to ValueBin are defined inline with the CREATE TABLE (no separate ALTER TABLE needed for a fresh install).

## Issues Encountered

- None — plan executed exactly as written.

## Deviations from Plan

None — plan executed exactly as written.

## Self-Check

- [x] `v2.2.0_create_mssql.sql` file header says v2.2.0
- [x] Observation table defined before Value, ValueVector, ValueMatrix, ValueImage (line 295 vs 400+)
- [x] Value table: only Observation_ID + Value columns (no Value_ID, Channel_ID, Timestamp)
- [x] ValueImage table: no ValueImage_ID IDENTITY column
- [x] Annotation table includes nullable Observation_ID column + FK
- [x] Views use Observation join pattern (2 occurrences confirmed)
- [x] No `v.[Channel_ID]`, `vv.[Channel_ID]`, `vm.[Channel_ID]`, `vi.[Channel_ID]` in value_repository.py
- [x] All WHERE clauses in get_* functions reference `o.[Channel_ID]` and `o.[Timestamp]`
- [x] operational_only subquery uses so/sv aliases
- [x] 140 unit/contract tests pass

## Self-Check: PASSED

## Next Step

Ready for 07-07-PLAN.md (integration + contract test updates for the new Observation-based schema)
