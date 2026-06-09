# Lab Ingest Bug Fix Plan

## Scope

Issues 1–7 are isolated to `app/pages/lab_ingest.py` plus minor additions
in `api/v1/repositories/lookup_repository.py`. No schema migrations required.

Issue 8 adds two optional columns to the `LabPanel` YAML schema dictionary
(DDL is regenerated from YAML — no migration script needed for pre-release)
and propagates through the repository, API schemas, panel management page,
and ingest form.

---

## Issue 1 — "Created by" should default to the current user

### Root cause

`_SESSION_DEFAULTS["created_by_person_id"]` is `None`. The person list is
loaded as `{person_id, label}` (no email), so there is no way to match the
auth user to a Person record at page load.

### Fix

1. At page load, call `list_persons()` (the full-field endpoint that returns
   `email`) instead of only `list_persons_lookup()`.
2. Grab the current user's email from `st.session_state["user"]["email"]`.
3. Find the matching Person by email; if found, use that `person_id` as the
   initial value for `_SESSION_DEFAULTS["created_by_person_id"]`.
4. When rendering the "Created by" selectbox, compute the `index` to point at
   the matched person instead of always `0`.

```python
# At page load (replaces list_persons_lookup() call)
_persons_full = list_persons()   # [{person_id, email, first_name, last_name, ...}]
_persons = [{"person_id": p["person_id"],
             "label": f"{p['first_name'] or ''} {p['last_name'] or ''}".strip()
                      or f"Person {p['person_id']}"}
            for p in _persons_full]

# Compute default person_id
_current_user = st.session_state.get("user") or {}
_current_email = (_current_user.get("email") or "").lower()
_default_person_id = next(
    (p["person_id"] for p in _persons_full
     if (p.get("email") or "").lower() == _current_email),
    None,
)
```

5. In `_SESSION_DEFAULTS`, set `"created_by_person_id": _default_person_id`.
6. In `_render_experiment_step`, compute `index` for the selectbox:

```python
person_opts = [{"id": None, "label": "— select —"}] + [...]
default_id = sess.get("created_by_person_id")
default_idx = next(
    (i for i, o in enumerate(person_opts) if o["id"] == default_id), 0
)
sel_person = st.selectbox("Created by *", ..., index=default_idx, ...)
```

Apply the same `index` logic to "Sampled by" in `_create_new_sample`.

**Files:** `app/pages/lab_ingest.py`

---

## Issue 2 — Campaign selected twice (experiment + sample)

### Root cause

`_render_experiment_step` has a "Campaign" selectbox and `_create_new_sample`
has a second "Campaign (optional)" selectbox. They write to different session
state keys (`campaign_id` vs `sample_campaign_id`).

### Fix

1. Move the campaign selector to the **top of the page**, before the expanders,
   as a top-level shared field. Write to `sess["campaign_id"]`.
2. Remove the "Campaign" column from the experiment fields in
   `_render_experiment_step`.
3. In `_create_new_sample`, remove the "Campaign (optional)" selectbox and
   instead pass `sess["campaign_id"]` directly when calling `create_sample`.
4. Update `_do_submit` to read `sess["campaign_id"]` (already does this for
   the experiment payload; the sample creation path just needs to stop reading
   `sess["sample_campaign_id"]`).

**Files:** `app/pages/lab_ingest.py`

---

## Issue 3 — Multiple samples (one per location), measurements grouped by sample

### Root cause

Step 2 creates exactly one sample. When a panel has series from multiple
sampling points, the user has to pick one location for the sample, then re-run
the whole form for the other locations.

### Design

Replace the single-sample Step 2 with a **multi-sample list**, where each
entry corresponds to one unique sampling point that appears among the assigned
series. Data entry in Step 3 then links each measurement to the correct sample
via the series' sampling point.

### Fix

#### Session state additions

```python
# Replace single-sample fields with:
"samples": [],
# Each entry: {"sampling_point_id": int, "label": str, "sample_id": int | None,
#               "sample_mode": "new"|"existing", "sp_id": int, ...all sample fields}
```

Remove `sample_mode`, `sample_id`, `sample_sp_id`, `sample_collection_kind_id`,
`sample_equipment_id`, `sample_sampled_by_id`, `sample_start`, `sample_end`,
`sample_description` from `_SESSION_DEFAULTS`.

#### Step 2 redesign

1. After series are assigned, compute `unique_sps`: the set of
   `sampling_point_id` values across all series in `sess["series"]`.
2. For each unique SP, render a collapsible section (use `st.expander`) with:
   - Radio: "Create new sample / Use existing"
   - If new: sampling point is pre-filled (read-only label), plus
     collection kind, equipment, sampled by, start/end datetimes, description
   - If existing: a selectbox filtered to samples at that SP
   - A "Create Sample" button per SP row
3. Each created/selected sample writes its `sample_id` into
   `sess["samples"][sp_idx]["sample_id"]`.

#### Step 3 changes

In `_render_series_tab`, look up `sess["samples"]` to find the sample whose
`sampling_point_id` matches `series_item["sampling_point_id"]`. Pass that
`sample_id` when building the measurement payload in `_do_submit`.

In `_render_submit`, the gate becomes: all unique SPs must have a resolved
`sample_id` before submission is enabled.

**Files:** `app/pages/lab_ingest.py`

---

## Issue 4 — Auto-generated names never appear in the form

### Root cause

Streamlit `st.text_input(key="lab_exp_name", value=sess["name"])` does **not**
update the displayed value when `sess["name"]` changes after the widget has
already been rendered with that key. The widget's own state in
`st.session_state["lab_exp_name"]` takes precedence over `value=`.

The same issue affects the series name (`key="lab_quick_series_name"`,
`value=auto_name`): once the popover has rendered, changing parameter/SP
selections does not update the displayed name.

### Fix

Set `st.session_state["<widget_key>"] = computed_value` **before** the widget
renders, but only when the computed value has actually changed.

**Experiment name (panel mode):**

```python
# When template selection changes (already inside the if t_id != sess["template_id"] block):
sess["name"] = f"{panel_name} — {_date.today().strftime('%Y-%m-%d')}"
st.session_state["lab_exp_name"] = sess["name"]   # ← add this line
```

**Series name in the "Add Lab Series" popover:**

Compute `auto_name` before the text_input and push it to session state when
both param and SP are selected:

```python
auto_name = _auto_series_name(sel_param, sel_sp)
if auto_name:
    st.session_state["lab_quick_series_name"] = auto_name
series_name = st.text_input("Series name", key="lab_quick_series_name")
```

Remove the `value=auto_name or "Custom series"` argument (the key-based state
takes over).

**Files:** `app/pages/lab_ingest.py`

---

## Issue 5 — Data editor reverts to original contents on Enter

### Root cause

On every Streamlit rerun triggered by any widget interaction (including pressing
Enter inside the data editor), the code rebuilds `df` from
`sess["measurements"][s_key]` and passes it as `df` to `st.data_editor(df, ...)`.
Streamlit's `data_editor` with a `key` maintains its own widget state, but the
`df` argument acts as an override that **resets** the displayed data whenever
it differs from the internal state — specifically when the editor state hasn't
been flushed to `sess["measurements"]` yet in the same rerun cycle.

The sync line `sess["measurements"][s_key] = edited.to_dict("records")` happens
**after** the widget renders, so on the rerun caused by Enter, the stale
`sess["measurements"]` value is used to build `df`, which overwrites the
in-progress edit.

### Fix

Use Streamlit's session state for the data editor as the single source of
truth. Initialize the editor state once from `sess["measurements"]` and then
**do not** pass `df` from session state on subsequent renders:

```python
editor_key = f"lab_measure_editor_{idx}"

# First render: seed the editor state from session
if editor_key not in st.session_state and rows:
    st.session_state[editor_key] = pd.DataFrame(rows)

# Always pass an empty/schema-only df as the base; let the key state drive content
base_df = pd.DataFrame(columns=["value", "replicate", "quality_code_id", "notes"])

edited = st.data_editor(
    base_df,
    column_config=col_config,
    use_container_width=True,
    num_rows="dynamic",
    key=editor_key,
)
```

Then sync back as before. On initial render with existing data the seeded
state is used; on subsequent reruns the key state persists the user's edits
without being overwritten by the (stale) session dict.

**Files:** `app/pages/lab_ingest.py`

---

## Issue 6 — Replicate number defaults to 1 for all rows

### Root cause

`st.column_config.NumberColumn("Replicate", default=1, ...)` gives every new
row the same default. The data editor has no per-row default logic.

### Fix

Remove the `num_rows="dynamic"` built-in add-row mechanism for scalar series
and replace it with an explicit **"+ Add row"** button that appends a new row
with the correct replicate number to `sess["measurements"][s_key]`:

```python
next_rep = max((r.get("replicate") or 0 for r in rows), default=0) + 1
if st.button("+ Add row", key=f"lab_add_row_{idx}"):
    sess["measurements"][s_key].append(
        {"value": None, "replicate": next_rep, "quality_code_id": None, "notes": None}
    )
    st.rerun()
```

Keep `num_rows="dynamic"` only for vector/matrix value kinds where row
addition is less structured. For scalar (vk==1) use `num_rows="fixed"` so the
editor only shows committed rows.

**Files:** `app/pages/lab_ingest.py`

---

## Issue 7 — Quality code is a dumb number field

### Root cause

`"quality_code_id": st.column_config.NumberColumn(...)` renders as a plain
integer input with no vocabulary. The `QualityCode` table has `{quality_code_id,
name, description, is_usable}` but this data is never loaded on the lab ingest
page.

### Fix

1. Add `list_quality_codes` to the page-load block:

```python
from app.api_client import list_quality_codes
_quality_codes = list_quality_codes()   # [{quality_code_id, name, description, is_usable}]
_qc_label_to_id = {
    f"{qc['name']} — {qc['description'] or ''}".strip(" —"): qc["quality_code_id"]
    for qc in _quality_codes
    if qc.get("is_usable", True)
}
_qc_id_to_label = {v: k for k, v in _qc_label_to_id.items()}
_qc_labels = list(_qc_label_to_id.keys())
```

2. Replace the `NumberColumn` with `SelectboxColumn`:

```python
"quality_code_id": st.column_config.SelectboxColumn(
    "Quality Code",
    options=_qc_labels,
    default=None,
    required=False,
),
```

3. Store the label string in the editor. In `_do_submit`, convert back to ID:

```python
raw_qc = row.get("quality_code_id")   # now a label string or None
qc_id = _qc_label_to_id.get(raw_qc) if raw_qc else None
measurements.append({
    ...
    "quality_code_id": qc_id,
    ...
})
```

**Files:** `app/pages/lab_ingest.py`

---

## Issue 8 — LabPanel should store default sample-collection metadata

### Motivation

When a lab technician runs the same panel week after week, the collection kind
(e.g., "Grab") and the auto-sampler used are identical every time. Requiring
the user to re-select them on every ingest session is redundant and
error-prone. Storing them on the panel and pre-filling the sample form removes
that friction.

### Fields to add to `LabPanel`

| New column | Logical type | FK | Nullable |
|---|---|---|---|
| `DefaultSampleCollectionKind_ID` | integer | `SampleCollectionKind.SampleCollectionKind_ID` | true |
| `DefaultSampleEquipment_ID` | integer | `Equipment.Equipment_ID` | true |

`SampledByPerson_ID` is deliberately excluded — that is context-dependent
(who is physically collecting today) and is already addressed by Issue 1
(current-user default).

### Fix — layer by layer

#### 1. YAML schema dictionary (`schema_dictionary/tables/LabPanel.yaml`)

Add two nullable FK columns after `CreatedByPerson_ID`:

```yaml
- name: DefaultSampleCollectionKind_ID
  logical_type: integer
  nullable: true
  description: "Default sample collection method pre-filled when this panel is loaded (e.g. Grab)"
  foreign_key:
    table: SampleCollectionKind
    column: SampleCollectionKind_ID

- name: DefaultSampleEquipment_ID
  logical_type: integer
  nullable: true
  description: "Default equipment pre-filled when this panel is loaded (e.g. auto-sampler ID)"
  foreign_key:
    table: Equipment
    column: Equipment_ID
```

Regenerate the DDL after editing (the build tooling picks this up automatically).

#### 2. Repository (`api/v1/repositories/ingestion_repository.py`)

**`list_lab_panels`** — add the two new columns to the `SELECT` and to the
returned dict:

```python
SELECT
    t.[LabPanel_ID], t.[Name], t.[Description], t.[CreatedByPerson_ID],
    t.[DefaultSampleCollectionKind_ID],
    t.[DefaultSampleEquipment_ID],
    (SELECT COUNT(*) ...) AS [SeriesCount]
FROM [dbo].[LabPanel] t ...
```

```python
{
    ...
    "default_sample_collection_kind_id": r[4],
    "default_sample_equipment_id": r[5],
    "series_count": r[6],
}
```

**`create_lab_panel`** — accept two new keyword args and include them in the
`INSERT`:

```python
def create_lab_panel(
    conn, *, name, description=None, created_by_person_id=None,
    default_sample_collection_kind_id=None,
    default_sample_equipment_id=None,
    series_ids,
) -> int:
    cursor.execute(
        """
        INSERT INTO [dbo].[LabPanel]
            ([Name], [Description], [CreatedByPerson_ID],
             [DefaultSampleCollectionKind_ID], [DefaultSampleEquipment_ID])
        OUTPUT INSERTED.[LabPanel_ID]
        VALUES (?, ?, ?, ?, ?)
        """,
        name, description, created_by_person_id,
        default_sample_collection_kind_id, default_sample_equipment_id,
    )
```

#### 3. API schemas (`api/v1/schemas/ingestion.py`)

**`LabPanelCreateRequest`** — add two optional fields:

```python
default_sample_collection_kind_id: int | None = None
default_sample_equipment_id: int | None = None
```

**`LabPanelResponse`** and **`LabPanelDetailResponse`** — add same two fields
so the UI receives them in both the list and detail calls.

#### 4. Endpoint (`api/v1/endpoints/lab.py`)

Pass the new fields through in `create_lab_panel`:

```python
template_id = ingestion_repository.create_lab_panel(
    conn,
    name=body.name,
    description=body.description,
    created_by_person_id=body.created_by_person_id,
    default_sample_collection_kind_id=body.default_sample_collection_kind_id,
    default_sample_equipment_id=body.default_sample_equipment_id,
    series_ids=body.series_ids,
)
```

#### 5. Panel management page (`app/pages/lab_panels.py`)

Add two optional selectboxes to the "New panel" form (below name/description,
above series multiselect):

```python
from app.api_client import list_equipment_lookup, list_sample_collection_kinds

_collection_kinds = list_sample_collection_kinds()
_equipment = list_equipment_lookup()

ck_opts = [{"id": None, "label": "— none —"}] + [
    {"id": c.get("sample_collection_kind_id") or c.get("id"), "label": c.get("name", "")}
    for c in _collection_kinds
]
sel_ck = st.selectbox("Default collection kind", [o["label"] for o in ck_opts], key="new_panel_ck")
default_ck_id = next((o["id"] for o in ck_opts if o["label"] == sel_ck), None)

eq_opts = [{"id": None, "label": "— none —"}] + [
    {"id": e.get("equipment_id") or e.get("id"), "label": e.get("identifier", "")}
    for e in _equipment
]
sel_eq = st.selectbox("Default equipment", [o["label"] for o in eq_opts], key="new_panel_eq")
default_eq_id = next((o["id"] for o in eq_opts if o["label"] == sel_eq), None)
```

Pass `default_sample_collection_kind_id` and `default_sample_equipment_id`
in the `create_lab_panel(...)` call.

Also display these defaults in the existing panels list (a single caption line
per panel showing the default collection kind and equipment if set).

#### 6. Ingest form (`app/pages/lab_ingest.py`)

When a panel is loaded (inside the `if t_id and t_id != sess["template_id"]:`
block in `_render_experiment_step`), extract the defaults from the panel detail
and write them into the session:

```python
detail = get_lab_panel(t_id)
sess["series"] = list(detail.get("series", []))
# Pre-fill sample defaults from panel
sess["default_sample_collection_kind_id"] = detail.get("default_sample_collection_kind_id")
sess["default_sample_equipment_id"] = detail.get("default_sample_equipment_id")
```

In `_create_new_sample` (and the per-SP sections introduced by Issue 3), when
building the collection kind and equipment selectboxes, compute the initial
`index` from the session default exactly as done for "Created by" in Issue 1:

```python
default_ck_id = sess.get("default_sample_collection_kind_id")
default_ck_idx = next(
    (i for i, o in enumerate(ck_opts) if o["id"] == default_ck_id), 0
)
sel_ck = st.selectbox("Collection kind", [o["label"] for o in ck_opts],
                      index=default_ck_idx, key=f"lab_sample_ck_{sp_idx}")
```

The defaults act as suggestions only — the user can override them for any
individual sample. Changing the panel selection overwrites the stored defaults;
clearing the panel selection resets them to `None`.

**Files touched:**
- `schema_dictionary/tables/LabPanel.yaml`
- `api/v1/repositories/ingestion_repository.py`
- `api/v1/schemas/ingestion.py`
- `api/v1/endpoints/lab.py`
- `app/pages/lab_panels.py`
- `app/pages/lab_ingest.py`

---

## Implementation order

Fix issues in this order to avoid re-work:

1. **#4** (auto-name) — isolated, zero side-effects
2. **#1** (default user) — isolated, only touches page-load + selectbox index
3. **#7** (quality code SelectboxColumn) — isolated, only touches col_config + submit
4. **#6** (replicate auto-increment + Add row button) — pairs naturally with #5
5. **#5** (data editor revert) — must be done together with #6 since both
   touch the editor rendering logic
6. **#2** (campaign deduplication) — removes a field, straightforward
7. **#8** (LabPanel sample defaults) — schema + API + two UI pages; do before
   the multi-sample redesign so the defaults slot naturally into the new
   per-SP sample sections
8. **#3** (multi-sample) — largest change; do last after the form is stable

Each issue should be committed separately for easy bisecting.
