---
phase: 07-observation-migration
plan: "04"
subsystem: schema-dictionary
tags: [yaml, schema-dictionary, observation, v2.2.0]
dependency_graph:
  requires: [07-01, 07-02, 07-03]
  provides: [schema-dictionary-v2.2.0]
  affects: [tooling, documentation]
tech_stack:
  added: []
  patterns: [YAML schema dictionary, format_version 1.0]
key_files:
  created:
    - schema_dictionary/tables/Observation.yaml
  modified:
    - schema_dictionary/tables/Value.yaml
    - schema_dictionary/tables/ValueVector.yaml
    - schema_dictionary/tables/ValueMatrix.yaml
    - schema_dictionary/tables/ValueImage.yaml
    - schema_dictionary/tables/Annotation.yaml
decisions:
  - "max_length:10 added to Observation.DataType column to satisfy schema validator (VARCHAR(10) per plan spec)"
metrics:
  duration: "~10 minutes"
  completed: "2026-03-16"
  tasks_completed: 2
  tasks_total: 2
  files_created: 1
  files_modified: 5
---

# Phase 07 Plan 04: Schema Dictionary YAMLs — Summary

Schema dictionary updated to v2.2.0: Observation.yaml created and all five payload/annotation YAMLs rewritten to reflect the Observation-centric design.

## Accomplishments

- Created `schema_dictionary/tables/Observation.yaml` — new hub table with 4 columns (Observation_ID IDENTITY PK, Channel_ID FK, Timestamp, DataType), UNIQUE on (Channel_ID, Timestamp, DataType)
- Rewrote `Value.yaml` — 2 columns only: Observation_ID (PK+FK) and Value (float); removed Value_ID, Channel_ID, Timestamp
- Rewrote `ValueVector.yaml` — composite PK (Observation_ID, ValueBin_ID); replaced Channel_ID+Timestamp with Observation_ID FK
- Rewrote `ValueMatrix.yaml` — composite PK (Observation_ID, RowValueBin_ID, ColValueBin_ID); replaced Channel_ID+Timestamp with Observation_ID FK
- Rewrote `ValueImage.yaml` — Observation_ID is now sole PK+FK; removed ValueImage_ID, Channel_ID, Timestamp, and the UQ_ValueImage_ChannelTimestamp constraint
- Updated `Annotation.yaml` — added nullable Observation_ID FK to Observation; all original columns (Channel_ID, StartTime, EndTime, etc.) preserved intact
- ProcessingLineage.yaml NOT modified (correct — channel-level lineage semantics unchanged)

## Files Created/Modified

| File | Action | Key Change |
|------|--------|-----------|
| schema_dictionary/tables/Observation.yaml | Created | New hub table |
| schema_dictionary/tables/Value.yaml | Rewritten | Observation_ID PK; removed Value_ID/Channel_ID/Timestamp |
| schema_dictionary/tables/ValueVector.yaml | Rewritten | PK=(Observation_ID, ValueBin_ID) |
| schema_dictionary/tables/ValueMatrix.yaml | Rewritten | PK=(Observation_ID, RowValueBin_ID, ColValueBin_ID) |
| schema_dictionary/tables/ValueImage.yaml | Rewritten | Observation_ID as sole PK; removed 3 old columns |
| schema_dictionary/tables/Annotation.yaml | Updated | Added nullable Observation_ID FK |

## Decisions Made

- `DataType` column in Observation.yaml given `max_length: 10` to satisfy the schema validator's requirement that all `logical_type: string` columns declare `max_length`. This matches the `VARCHAR(10)` spec in the DDL plan.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Added max_length:10 to Observation.DataType**
- **Found during:** Task 1 verification (test_yaml_schema_validates_cleanly failed)
- **Issue:** Schema validator requires max_length for all string-type columns; Observation.DataType was missing it
- **Fix:** Added `max_length: 10` to the DataType column definition (consistent with VARCHAR(10) in DDL plan)
- **Files modified:** schema_dictionary/tables/Observation.yaml
- **Commit:** 9ac3985

## Issues Encountered

- Pre-existing test failures (not introduced by this plan):
  - `tests/schema/test_sensor_status_yaml.py` — SensorStatusCode YAML missing (unrelated to this work)
  - `tools/schema_migrate/tests/test_render.py::test_default_current_timestamp` — pre-existing render assertion
  - These failures existed before this plan and were confirmed via git stash test

## Next Step

Ready for 07-05-PLAN.md (API repository updates)

## Self-Check: PASSED

- schema_dictionary/tables/Observation.yaml: FOUND
- schema_dictionary/tables/Value.yaml: updated (no Value_ID/Channel_ID/Timestamp)
- schema_dictionary/tables/ValueVector.yaml: PK=[Observation_ID, ValueBin_ID]
- schema_dictionary/tables/ValueMatrix.yaml: PK=[Observation_ID, RowValueBin_ID, ColValueBin_ID]
- schema_dictionary/tables/ValueImage.yaml: PK=[Observation_ID], no ValueImage_ID
- schema_dictionary/tables/Annotation.yaml: Observation_ID added, Channel_ID/StartTime/EndTime intact
- Commit 9ac3985: FOUND
- Commit 0393d08: FOUND
- test_yaml_schema_validates_cleanly: PASSES
