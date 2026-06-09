# Plan: Plot lab AnalysisSeries in the Data Explorer

## Goal

Let the Data Explorer plot lab data (**AnalysisSeries**) alongside sensor data
(**Channels**), overlaid on the same charts. Two foldable pickers — Sensor and
Lab — share one top-level Campaign filter. Umbrella concept = **Trace**
(see [CONTEXT.md](../CONTEXT.md)).

## Resolved decisions (from grilling)

| # | Decision | Choice |
|---|----------|--------|
| 1 | Lab x-axis | **Sample collection time**. Per [ADR 0002](../docs/adr/0002-lab-observation-timestamp-sample-time.md), lab ingest now stores collection time *directly* in `Observation.Timestamp` (supersedes ADR 0001). No read-time `Sample` join needed. |
| 2 | Replicates | Plot **every replicate as its own point** (hover shows replicate #) |
| 3 | Value kinds | **All four** (scalar/vector/matrix/image) |
| 4 | Overlay | Sensor + lab on **one chart** (shared per-type tabs) |
| 5 | Umbrella term | **Trace** (= Channel or AnalysisSeries) |
| 6 | Campaign | **One top-level selector** filtering both pickers |
| 7 | Lab filter logic | **Cross-filter** (campaign→parameter→sampling-location), computed in-memory from `list_analysis_series_lookup` — no new lookup endpoint |
| 8 | Read path | **Shared SQL helper + thin per-source wrappers** (REVISED per ADR 0002). Since the lab/sensor reads now differ only by source filter, extract each value-kind body into a private helper; keep `get_*_values(channel_id)` signatures unchanged and add `get_analysis_series_*_values(series_id)` wrappers. Convergent + low blast radius. |
| 9 | Quality coloring | Freebie: lab writes `Value.QualityCode` in sync with `LabAnalysis.QualityCode_ID` at ingest — read via existing payload join |
| 10 | Lab actions | **Plot + CSV extract only** (read-only). No lab annotations / quality-flag / equipment events this pass |
| 11 | State shape | **Two parallel lists** (`explore_active_channels` + new `explore_active_series`), merged at render |

## Backend

### Repository — `api/v1/repositories/value_repository.py`
The lab read differs from the sensor read **only** by the source filter
(`o.[Channel_ID] = ?` vs `JOIN LabAnalysis la ON la.[LabAnalysis_ID] =
o.[LabAnalysis_ID] WHERE la.[AnalysisSeries_ID] = ?`). Timestamp
(`o.[Timestamp]`, now = sample time per ADR 0002), payload joins, return shape,
and stats are identical. So:
- Extract each value-kind query body into a private helper taking
  `(source_join, source_where, params, …)`.
- Keep `get_scalar_values(channel_id)` / `get_vector_values` / `get_matrix_values`
  / `get_image_values` / `get_channel_stats` as thin wrappers (unchanged
  signatures → no caller/test churn).
- Add `get_analysis_series_scalar_values` / `_vector_` / `_matrix_` / `_image_`
  and `get_analysis_series_stats` wrappers + a
  `get_analysis_series_values_for_metadata` dispatcher.
- Replicates plot as individual points automatically (each LabAnalysis is its
  own Observation/Value row at the same timestamp). Replicate-number-on-hover is
  a deferred nicety (would need a lab-only `la.[Replicate]` column, breaking the
  shared return shape).
- `operational_only` stays sensor-only (lab has no status channels).

### Endpoints — new `api/v1/endpoints/analysis_series_timeseries.py`
Parallel to `/timeseries/{channel_id}`, reusing the `TimeseriesOut` schema so
the frontend renderers work unchanged:
- `GET /analysis-series/{id}` → timeseries
- `GET /analysis-series/{id}/stats`
- `GET /analysis-series/{id}/image` + `/thumbnail` (for image kind)
Register router in the API app.

### api_client — `app/api_client.py`
Add `get_analysis_series_timeseries`, `get_analysis_series_stats`,
`get_analysis_series_image`, `get_analysis_series_thumbnail` mirroring the
`get_channel_*` helpers.

## Frontend — `app/pages/explore.py`

### Layout
```
Top bar (title + date range + mode toggle)
Campaign selector            ← hoisted to top-level, drives both pickers
[▼ Sensor data]   expander   → equipment / parameter / value-type cross-filter + Add
[▼ Lab / analysis series] expander → parameter / sampling-location cross-filter + Add
Active traces (chips, sensor + lab merged)
Visualization area (tabs by value kind present across BOTH lists; overlaid)
```

### State
- Keep `explore_active_channels`; add `explore_active_series: list[int]`,
  `explore_series_meta: dict[int,dict]`, `explore_series_stats`,
  and lab entries in the data cache (key by `("series", id, start, end)`).
- Top-level campaign uses the existing `picker_campaign_id`.

### Lab picker (new `_render_series_picker` in explore.py)
- Mirror `_render_channel_picker`'s interaction (filter row → select one → Add).
- Cross-filter parameter & sampling-location in-memory from
  `list_analysis_series_lookup()`, scoped by top-level campaign.
- Do **not** reuse `series_picker.py` (different model: multi-select-into-form +
  has a create-new-series form inappropriate for exploration).

### Rendering (merge at render)
- A small helper builds a unified trace descriptor list
  `[{source, id, meta}]` from both active lists; figure/chips/CSV consume it.
- **Scalar overlay:** sensor = `lines+markers`; lab = **markers-only** scatter
  (visually distinct discrete samples), colored by `Value.QualityCode` via the
  existing `QUALITY_COLORS`. No LTTB on lab (sparse).
- **Selection actions** (annotate / event / flag) filter to **sensor** traces
  only; if a selection touches only lab points, show "actions available for
  sensor channels only."
- Vector/matrix/image per-type views: their channel selectbox also lists lab
  series of that kind.
- Chips: lab chips get the same min/max + "Plot all" / "Last 7d" via lab stats;
  no equipment-event overlay for lab.

## Tests (unit only — `tests/unit/`, per project convention)
- Repository: lab read functions return sample-time-ordered rows; replicates
  preserved; stats correct. (Mock DB rows.)
- Endpoint: `/analysis-series/{id}` shape matches `TimeseriesOut`.
- AppTest: lab picker cross-filtering; adding a lab series creates a chip;
  overlay figure contains both a sensor and a lab trace.

## Implementation order (bisectable commits)
1. Repo lab read + stats functions (+ unit tests)
2. Endpoints + router registration (+ unit tests)
3. api_client helpers
4. Explore: hoist campaign to top-level (no behavior change for sensor)
5. Explore: lab picker + `explore_active_series` state + chips
6. Explore: merged-render overlay (scalar first, then vector/matrix/image)
7. AppTest coverage

## Out of scope (future issues)
Lab annotations, lab quality-flagging, lab equipment events, analysis-time
x-axis toggle.
