---
status: investigating
trigger: "KeyError: 'name' when accessing Channels page"
created: 2026-03-05T00:00:00Z
updated: 2026-03-05T00:00:00Z
---

## Current Focus

hypothesis: CONFIRMED - Field name mismatch between frontend and API. Frontend expects `name` but API returns `parameter_name`
test: Fix line 54 in 4_Channels.py to use `p["parameter_name"]` instead of `p["name"]`
expecting: Channels page will load without KeyError
next_action: Apply the fix

## Symptoms

expected: Channels page should load and display parameter dropdown options successfully
actual: KeyError: 'name' exception is raised when page loads
errors: KeyError: 'name' at File "/Users/jeandavidt/Developer/modelEAU/open_dateaubase/app/pages/4_Channels.py", line 54: {"id": p["parameter_id"], "label": p["name"]} for p in parameters_lookup
reproduction: Navigate to the Channels page (4_Channels.py) - error occurs during page load when building parameter_options from parameters_lookup
started: Issue is happening consistently on page load
timeline: Issue is happening consistently on page load
location:
  - app/pages/4_Channels.py, line 54
  - The error occurs in list comprehension: parameter_options = [{"id": p["parameter_id"], "label": p["name"]} for p in parameters_lookup]

## Eliminated

## Evidence

- timestamp: 2026-03-05T00:00:00Z
  checked: app/pages/4_Channels.py lines 39-58
  found: parameters_lookup is populated by list_parameters_lookup() API call. On line 54, code expects each item p to have "parameter_id" and "name" keys
  implication: Need to check what list_parameters_lookup() actually returns

- timestamp: 2026-03-05T00:00:00Z
  checked: api/v1/schemas/channel.py - ParameterLookupOut schema
  found: Schema defines fields as `parameter_id: int` and `parameter_name: str` (not `name`)
  implication: API returns `parameter_name`, not `name`

- timestamp: 2026-03-05T00:00:00Z
  checked: api/v1/repositories/metadata_repository.py - get_parameters_lookup function
  found: Returns dictionaries with keys `{"parameter_id": row[0], "parameter_name": row[1]}`
  implication: Confirms API returns `parameter_name` key

- timestamp: 2026-03-05T00:00:00Z
  checked: Comparison with other lookups
  found: Equipment uses `identifier`, ProcessingDegree uses `name`, Parameter uses `parameter_name`
  implication: Each lookup has its own field naming - Parameter is inconsistent with ProcessingDegree

## Resolution

root_cause: Field name mismatch between frontend and API. The `ParameterLookupOut` schema and `get_parameters_lookup` repository return dictionaries with `parameter_name` key, but the frontend code in `4_Channels.py` line 54 was trying to access `p["name"]` which doesn't exist.

fix: Changed line 54 in `4_Channels.py` from `p["name"]` to `p["parameter_name"]` to match the API response structure.

verification: Python syntax check passed. The fix aligns the frontend code with the API schema definition.

files_changed:
  - app/pages/4_Channels.py: Line 54 - Changed p["name"] to p["parameter_name"]
