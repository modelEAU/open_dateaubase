# Task Plan: Lab Ingest Bug Fixes & UX Improvements

## Goal
Fix 7 reported usability problems and bugs in the lab ingest form (`app/pages/lab_ingest.py`), eliminating redundancy, broken auto-naming, data-editor revert issues, and dumb field behaviors.

## Phases
- [x] Phase 1: Codebase exploration and diagnosis
- [x] Phase 2: Implement fixes (by issue)
- [x] Phase 3: Smoke-test and commit

## Issues & Status

| # | Issue | Complexity | Files |
|---|-------|-----------|-------|
| 1 | "Created by" should default to current user | Low | `lab_ingest.py`, `lookup_repository.py` |
| 2 | Campaign redundancy — select once, filter panels | Medium | `lab_ingest.py` |
| 3 | Multiple samples per form, grouped by location | High | `lab_ingest.py` |
| 4 | Auto-generated names don't appear in form | Low | `lab_ingest.py` |
| 5 | Data editor reverts on Enter | Medium | `lab_ingest.py` |
| 6 | Replicate doesn't auto-increment | Low | `lab_ingest.py` |
| 7 | Quality code is a dumb number field | Low | `lab_ingest.py`, `api_client.py` |

## Key Questions
1. Is there a direct link between auth `User` and `Person`? → Answered: yes, via `Email` field in `Person` table — but `list_persons_lookup` doesn't return email; need `list_persons()` full list.
2. Does `LabPanel` have a `campaign_id`? → Need to check schema/db
3. How does Streamlit `data_editor` state interact with `value=df`? → Confirmed race condition

## Decisions Made
- Issue 1: Use `list_persons()` (full list with email) to match current user's email against Person records; fall back to `None` if no match
- Issue 2: Add a top-level campaign selector; remove the duplicate from sample form; no panel filtering (panels are campaign-agnostic in the current schema)
- Issue 3: Redesign Step 2 to support a list of samples (one per unique sampling point in the panel), each with its own location+metadata; Step 3 tables are already per-series so this mainly affects the sample creation UI and the measurement submission payload
- Issue 4: Fix Streamlit widget-state vs programmatic value conflict by setting `st.session_state["key"] = value` before the widget renders
- Issue 5: Fix data_editor revert by initializing `df` from the data_editor's own session state key when it exists, NOT from `sess["measurements"]` (which is one render behind)
- Issue 6: Auto-increment by scanning current rows' max replicate before the editor renders and injecting a new row with replicate+1 via a dedicated "Add row" button
- Issue 7: Load `list_quality_codes()` at page load; use `SelectboxColumn` with labels `"{name} ({description})"` and maintain `qc_name_to_id` map; resolve at submit time

## Errors Encountered
(none yet)

## Status
**Currently in Phase 2** — ready to implement fixes
