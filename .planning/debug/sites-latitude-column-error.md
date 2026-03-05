---
status: investigating
trigger: "SQL error 'Invalid column name LatitudeWGS84' when accessing /api/v1/sites endpoint"
created: "2026-03-05T00:00:00Z"
updated: "2026-03-05T00:00:00Z"
---

## Current Focus

hypothesis: The code references 'LatitudeWGS84' column but the database table has a different column name

next_action: Read the repository file to see the SQL query and compare with actual database schema

## Symptoms

expected: Sites API endpoint should return list of sites successfully
actual: 500 Internal Server Error when accessing /api/v1/sites?page=1&page_size=100
errors: pyodbc.ProgrammingError: ('42S22', "[42S22] [Microsoft][ODBC Driver 18 for SQL Server][SQL Server]Invalid column name 'LatitudeWGS84'. (207) (SQLExecDirectW)")
reproduction: GET request to /api/v1/sites?page=1&page_size=100 triggers the error
timeline: Error occurs in Phase 2-3 development, happening consistently on sites page access
location:
  - api/v1/repositories/site_repository.py, line 10
  - api/v1/endpoints/sites.py, line 17

## Eliminated

## Evidence

## Resolution

root_cause:
fix:
verification:
files_changed: []
