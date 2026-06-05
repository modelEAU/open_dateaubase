---
name: dateaubase-app-map
description: "Orientation map for the open_datEAUbase Streamlit web app (app/). Use FIRST when an agent needs to understand the app before editing or testing it: page structure, navigation, the api_client backend boundary, the form/dialog/CRUD component patterns, the cascading series_picker, and the session-state keys. Triggers: understand the streamlit app, where is X page, how does the app talk to the backend, what to mock, lab ingest, series picker, before writing a test for the app."
---

# open_datEAUbase app map

A fast orientation index for the Streamlit web app under `app/`. Read this before
editing or testing a page. For Streamlit framework mechanics (rerun model, session
state, widget styling), defer to the installed `developing-with-streamlit` skill — run
its discovery script first:

```bash
python ~/.agents/skills/developing-with-streamlit/scripts/discover.py \
  --project-dir /Users/jeandavidt/Developer/modelEAU/open_dateaubase
```

## Structure

- **Entry point:** `app/Home.py`. Multipage app built with `st.navigation`; auth
  (`get_current_user()`) is enforced *before* navigation renders.
- **Pages:** `app/pages/` — grouped in `Home.py` as Operations (Sensor Ingest, Lab
  Ingest, Lab Panels, Visualize, Equipment Move), Workflows (Site / Field System /
  Campaign wizards), Entities (Campaigns, Sites, Equipment, …), Associations, Signal
  Sources, Vocabulary.
- **Components:** `app/components/` — reusable widgets (details below).
- **Config:** `app/config.py` — `settings.API_BASE_URL` (default
  `http://localhost:8000/api/v1`), `APP_TITLE`, `APP_VERSION`; loads `.env.local` if present.

## Backend boundary — the one place to mock

`app/api_client.py` is the *only* path from the app to the backend.

- One **synchronous** `httpx` function per API route (e.g. `list_sites_lookup`,
  `create_site`, `ingest_lab`). No async, no streaming.
- `_get_client()` injects `Authorization: Bearer <st.session_state["access_token"]>`.
- Non-2xx → raises `APIError(status_code, message)`; a 401 with a token clears the session.

When testing, **patch these functions where they are imported into the page/component
module under test** (e.g. `app.components.campaign_wizard.list_campaign_kinds`), *not*
on `app.api_client`. See the `write-streamlit-tests` skill.

## Component patterns

- `series_picker.py` — the most complex widget. Cascading filter
  campaign → parameter → sampling-point that lists matching `AnalysisSeries` (up to 20)
  with `+ Add` chips, plus a collapsible "create new series" form (auto-names
  `{parameter} at {location}`). Used in lab ingest and the campaign wizard.
- `form_dialog.py` / `crud_form.py` — `st.dialog`-based create/edit forms; `crud_form`
  renders typed fields (text, number, select, multiselect, date, datetime, textarea,
  checkbox) with validation. Supports a `render_fn` callback for custom widgets
  (series_picker plugs in here).
- `generic_crud.py` — generic select-row → edit/delete table; the pattern behind the
  simple Entity/Vocabulary pages (e.g. `equipment.py`).
- `campaign_wizard.py` — large multi-step wizard; the reference for multi-step flows.

## Session-state keys (what tests pre-seed / assert)

- `access_token` — bearer token for every api_client call.
- `lab_session` — dict driving `lab_ingest.py` (mode, name, datetime, description,
  `series`, `samples`, measurements). Defaults from `_SESSION_DEFAULTS`.
- `series_picker` keys are namespaced per field: `spkr_{field}_selected` (list of
  selected ids), `spkr_{field}_creating` (bool), plus per-widget keys
  `spkr_{field}_camp_sel`, `_param_sel`, `_sp_sel`, `_nc_*` (new-series form).
- `selected_{entity}_id` — row selection on CRUD pages (e.g. `selected_equipment_id`).

## Lookups

Each page loads its dropdown lookups once at top-of-script via `api_client.list_*`
inside a try/except — an `APIError` on any lookup halts the page. Tests must mock every
lookup a page calls, or the page errors before the flow under test runs.

## Key flows worth testing

1. **Lab ingest** (`pages/lab_ingest.py`): choose mode (New / From Panel / Add to
   Existing) → experiment context → add `AnalysisSeries` (via series_picker) → enter
   measurements (scalar/vector/matrix/image) → submit (`ingest_lab` / `ingest_lab_image`).
2. **series_picker cascade**: filter narrows series; `+ Add`/`×` mutate
   `spkr_{field}_selected`; "create new" posts a new series.
3. **CRUD** (e.g. `equipment.py`): New → dialog → submit (POST) → refresh; select row →
   Edit → dialog (PATCH); Delete.
4. **Campaign wizard**: multi-step validation + all-new / all-existing execution paths.

## Related skills

- `write-streamlit-tests` — protocol for writing AppTest + Playwright tests for these flows.
- `verify-app-in-browser` — protocol for running the stack and verifying in a real browser.
