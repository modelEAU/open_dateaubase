# v2.2.0 Consistency Fix Summary

## Problem Statement
The v2.2.0 release introduced the Observation hub table and restructured all value tables
(Value, ValueVector, ValueMatrix, ValueImage) to use Observation_ID foreign keys instead of
duplicated Channel_ID and Timestamp columns.

However, the following components were not updated to match:
1. Test database initialization (init.sql, seed data)
2. Docker test data seed
3. Test infrastructure (fixtures)
4. Documentation

## Changes Made

### Database Schema & Test Data

1. **Created sql/seed_v2.2.0.sql**
   - New seed data using Observation hub pattern
   - All values inserted via Observation table first
   - Includes all lookup table data for standalone testing
   - Fixed unique constraint violations from v2.1.0 data

2. **Updated sql/init.sql**
   - Applies v2.1.0→v2.2.0 migration
   - Uses seed_v2.2.0.sql for test data
   - Archives old seed_v2.1.0.sql

3. **Updated docker/test-data-seed.sql**
   - Fixed column names (Parameter, Name) for v2.2.0 schema

4. **Fixed sql_generation_scripts/v2.2.0_create_mssql.sql**
   - Changed BIT DEFAULT True → BIT DEFAULT 1
   - Fixed Pictures column type
   - Updated views to join through Observation
   - Added proper GO batch separators

### Test Infrastructure

5. **Updated tests/integration/conftest.py**
   - Added v2.1.0_to_v2.2.0 migration to SQL_FILES
   - Added seed_v2.2.0.sql and v2.2.0_create.sql references
   - Created db_at_v220 fixture
   - Fixed archived seed file paths

6. **Updated tests/integration/test_phase_d.py**
   - Changed fixture from db_conn to db_at_v220
   - All 9 schema validation tests now pass

### Documentation

7. **Updated docs/reference/inserting_data.md**
   - Updated all SQL examples for Observation hub pattern
   - Show two-step insert: Observation → Value
   - Updated SELECT queries to join through Observation

## Test Results

```bash
# v2.2.0 schema tests
$ uv run pytest tests/integration/test_phase_d.py -v
9 passed

# API contract tests
$ uv run pytest tests/api/contract/test_schema_contracts.py::TestObservationAwareIngest -v
2 passed

# All API and unit tests
$ uv run pytest tests/api tests/unit -q
142 passed

# Documentation build
$ uv run mkdocs build
Documentation built successfully
```

## Files Modified

### New Files
- sql/seed_v2.2.0.sql

### Modified Files
- sql/init.sql
- sql_generation_scripts/v2.2.0_create_mssql.sql
- docker/test-data-seed.sql
- tests/integration/conftest.py
- tests/integration/test_phase_d.py
- docs/reference/inserting_data.md

### Moved Files
- sql/seed_v2.1.0.sql → sql/archive/seed_v2.1.0.sql

## Remaining Work

The following files need updates for full functionality but are not blocking:
- sql/seed_explore.sql (commented out in init.sql)
- sql/seed_importer_fixtures.sql (commented out in init.sql)

These are larger seed datasets that can be updated in a follow-up task.

## Verification

To verify the v2.2.0 setup:

```bash
# Start the database
docker compose up -d db

# Initialize with v2.2.0 schema
docker compose up db-init

# Run v2.2.0 tests
uv run pytest tests/integration/test_phase_d.py -v

# Build docs
uv run mkdocs build
```
