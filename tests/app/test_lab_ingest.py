"""AppTest regression suite for the Lab Analysis Ingest page's wide-grid flow.

Phase 4 of the wide-table redesign (.tasks/lab_wide_table_plan.md). This
replaces the Phase 0 safety-net suite, which pinned the old per-series
accordion (Step 2 "Sample" + Step 3 "Measurement Values" for every value
kind) that Phases 1-3 removed. Non-image series (scalar/vector/matrix) now
create their sample automatically at submit time from a populated grid row;
only image-kind series still go through the old per-sample-then-upload path
(D3).

Coverage map:
  Header — no series: Submit disabled
  Header — "Add existing series" appends to session
  Header — panel mode loads panel series + auto-names experiment
  Grid — populated row creates a sample and submits one measurement
  Grid — two populated rows create two samples (one measurement each)
  Grid — two rows sharing a sample name = one sample, auto-numbered replicates
  Grid — rows with a blank sample name each stand alone as their own sample
  Grid — row with a value but no start time blocks with an error, no ingest
  Grid — empty row is skipped, "no measurements" blocks submit
  Grid — append-to-existing-experiment minimal payload (experiment_id + measurements)
  Image — sample creation still uses the old per-sampling-point flow (D3)
  Submit — blocked until image sampling points have a resolved sample

`st.data_editor` isn't drivable via AppTest widget interactions (no
`at.data_editor` accessor), so grid rows are seeded directly into the stable
per-sampling-point seed `lab_grid_seed_{sp}` (via `_seed_grid`) — the
equivalent of "the grid already holds these rows" rather than driving
keystrokes/paste.
"""
from __future__ import annotations

from contextlib import ExitStack
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

PAGE = str(Path(__file__).parent.parent.parent / "app" / "pages" / "lab_ingest.py")
# Patch app.api_client directly: lab_ingest.py re-executes its
# `from app.api_client import ...` on every AppTest rerun (it's a page
# script, not a component called through a stable harness), so a patch on
# app.pages.lab_ingest.* would be undone by the next rerun's import.
MOD = "app.api_client"

# ---------------------------------------------------------------------------
# Stable fixture data
# ---------------------------------------------------------------------------

_PARAMETERS = [{"parameter_id": 1, "parameter_name": "COD"}]
_UNITS = [{"unit_id": 1, "unit": "mg/L"}]
_SP = [
    {"sampling_point_id": 1, "label": "Influent"},
    {"sampling_point_id": 2, "label": "Effluent"},
]
_CAMPAIGNS = [{"campaign_id": 1, "name": "Campaign A"}]
_PERSONS_FULL = [
    {"person_id": 1, "first_name": "Alice", "last_name": "Smith", "email": "alice@example.com"}
]
_COLLECTION_KINDS = [{"sample_collection_kind_id": 1, "name": "Grab"}]
_SAMPLE_KINDS = [
    {"sample_kind_id": 7, "name": "Field", "description": "Field sample"},
    {"sample_kind_id": 8, "name": "Blank", "description": "Blank"},
]
_MATERIAL_KINDS = [
    {"sample_material_kind_id": 9, "name": "mixed liquor", "description": "ML"},
    {"sample_material_kind_id": 10, "name": "tap water", "description": "Tap"},
]
_EQUIPMENT = [{"equipment_id": 1, "identifier": "Bottle-1"}]
_TEMPLATES = [{"lab_panel_id": 1, "name": "Standard Panel", "series_count": 1}]
_GRID_SERIES_ITEM = {
    "analysis_series_id": 1,
    "name": "COD@Influent",
    "parameter_id": 1,
    "parameter_name": "COD",
    "sampling_point_id": 1,
    "sampling_point_label": "Influent",
    "unit_id": 1,
    "value_kind_id": 1,
}
_IMAGE_SERIES_ITEM = {
    "analysis_series_id": 2,
    "name": "Floc@Effluent",
    "parameter_id": 1,
    "parameter_name": "COD",
    "sampling_point_id": 2,
    "sampling_point_label": "Effluent",
    "unit_id": 1,
    "value_kind_id": 4,
}
_ALL_SERIES = [_GRID_SERIES_ITEM, _IMAGE_SERIES_ITEM]
_EXPERIMENTS = [
    {"lab_experiment_id": 1, "name": "Exp 1", "experiment_datetime": "2026-01-01T00:00:00"}
]
_SAMPLES = [{"sample_id": 5, "label": "Sample #5"}]
_QUALITY_CODES = [
    {"quality_code_id": 1, "name": "Good", "description": "No issues", "is_usable": True}
]

_LOOKUP_SPECS = [
    (f"{MOD}.list_samples_lookup", _SAMPLES),
    (f"{MOD}.list_sampling_points_lookup", _SP),
    (f"{MOD}.list_campaigns_lookup", _CAMPAIGNS),
    (f"{MOD}.list_parameters_lookup", _PARAMETERS),
    (f"{MOD}.list_units_lookup", _UNITS),
    (f"{MOD}.list_persons", _PERSONS_FULL),
    (f"{MOD}.list_sample_collection_kinds", _COLLECTION_KINDS),
    (f"{MOD}.list_sample_kind_lookup", _SAMPLE_KINDS),
    (f"{MOD}.list_sample_material_kind_lookup", _MATERIAL_KINDS),
    (f"{MOD}.list_equipment_lookup", _EQUIPMENT),
    (f"{MOD}.list_lab_panels", _TEMPLATES),
    (f"{MOD}.list_analysis_series_lookup", _ALL_SERIES),
    (f"{MOD}.list_lab_experiments_lookup", _EXPERIMENTS),
    (f"{MOD}.list_quality_codes", _QUALITY_CODES),
]

_MUTATION_SPECS = [
    (f"{MOD}.create_sample", {"sample_id": 42}),
    (f"{MOD}.ingest_lab", {"lab_experiment_id": 99, "rows_written": 3}),
    (
        f"{MOD}.get_lab_panel",
        {
            "series": [_GRID_SERIES_ITEM],
            "default_sample_collection_kind_id": None,
            "default_sample_equipment_id": None,
            "default_sample_kind_id": None,
            "default_sample_material_kind_id": None,
        },
    ),
    (f"{MOD}.get_lab_experiment_series", [_GRID_SERIES_ITEM]),
]


@pytest.fixture()
def mocked_lookups():
    with ExitStack() as stack:
        for target, retval in _LOOKUP_SPECS:
            stack.enter_context(patch(target, return_value=retval))
        yield


@pytest.fixture()
def mock_apis():
    with ExitStack() as stack:
        for target, retval in _LOOKUP_SPECS:
            stack.enter_context(patch(target, return_value=retval))
        mocks = {}
        for target, retval in _MUTATION_SPECS:
            name = target.split(".")[-1]
            mocks[name] = stack.enter_context(patch(target, return_value=retval))
        yield mocks


def _at(seed: dict | None = None) -> AppTest:
    at = AppTest.from_file(PAGE, default_timeout=10)
    if seed:
        at.session_state["lab_session"] = seed
    return at


def _base_session(**overrides) -> dict:
    sess = {
        "mode": "new",
        "template_id": None,
        "experiment_id": None,
        "name": "Test Exp",
        "campaign_id": 1,
        "datetime": datetime(2026, 1, 1, tzinfo=timezone.utc),
        "description": "",
        "created_by_person_id": 1,
        "series": [],
        "samples": [],
        "measurements": {},
    }
    sess.update(overrides)
    return sess


_META_COLS = [
    "sample_label", "sample_kind", "sample_material", "start", "end",
    "collection_kind", "equipment",
]


def _seed_grid(at, sp_id, rows, val_cols=("val_1",)):
    """Seed the stable results-grid seed for a sampling point directly, the
    equivalent of "the grid already holds these rows" (``st.data_editor`` can't
    be driven through AppTest widget interactions)."""
    cols = [*_META_COLS, *val_cols, "quality_code", "notes"]
    df = pd.DataFrame(rows, columns=cols)
    df["start"] = pd.to_datetime(df["start"], errors="coerce")
    df["end"] = pd.to_datetime(df["end"], errors="coerce")
    for vc in val_cols:
        df[vc] = pd.to_numeric(df[vc], errors="coerce")
    for c in ("sample_label", "sample_kind", "sample_material", "collection_kind",
              "equipment", "quality_code", "notes"):
        df[c] = df[c].astype(object).where(df[c].notna(), None)
    at.session_state[f"lab_grid_seed_{sp_id}"] = df


def _errors(at: AppTest) -> list[str]:
    return [e.value for e in at.error]


_ROW_START = datetime(2026, 1, 1, 8, 0, tzinfo=timezone.utc)


def _row(**overrides) -> dict:
    """One results row: sample description + its measured values."""
    row = {
        "sample_label": "S1",
        "sample_kind": "Field",
        "sample_material": "mixed liquor",
        "start": _ROW_START,
        "end": None,
        "collection_kind": "Grab",
        "equipment": "Bottle-1",
        "val_1": 12.3,
        "quality_code": None,
        "notes": None,
    }
    row.update(overrides)
    return row


# ---------------------------------------------------------------------------
# Header — series assignment
# ---------------------------------------------------------------------------


def test_no_series_submit_disabled(mocked_lookups):
    at = _at(_base_session()).run()
    assert not at.exception
    submit_btn = next(b for b in at.button if b.label == "Submit")
    assert submit_btn.disabled is True


def test_add_existing_series_appends_to_session(mocked_lookups):
    at = _at(_base_session()).run()
    label = f"{_GRID_SERIES_ITEM['name']} — {_GRID_SERIES_ITEM['parameter_name']} @ {_GRID_SERIES_ITEM['sampling_point_label']}"
    at.selectbox(key="lab_add_series_sel").set_value(label).run()
    series = at.session_state.lab_session["series"]
    assert len(series) == 1
    assert series[0]["analysis_series_id"] == 1


def test_panels_scoped_to_selected_campaign(mocked_lookups):
    """The panel list is fetched scoped to the selected campaign's sampling
    locations (campaign_id passed to list_lab_panels), unless "show all" is on."""
    with patch(f"{MOD}.list_lab_panels", return_value=_TEMPLATES) as m:
        _at(_base_session(campaign_id=1)).run()
        assert any(
            c.kwargs.get("campaign_id") == 1 for c in m.call_args_list
        ), m.call_args_list

    with patch(f"{MOD}.list_lab_panels", return_value=_TEMPLATES) as m:
        at = _at(_base_session(campaign_id=1))
        at.session_state["lab_panels_show_all"] = True
        at.run()
        assert all(c.kwargs.get("campaign_id") is None for c in m.call_args_list)


def test_panel_mode_loads_series_and_autonames(mock_apis):
    at = _at(_base_session()).run()
    at.radio(key="lab_mode").set_value("From panel").run()
    panel_label = "Standard Panel (1 series)"
    at.selectbox(key="lab_template_sel").set_value(panel_label).run()

    mock_apis["get_lab_panel"].assert_called_once_with(1)
    sess = at.session_state.lab_session
    assert len(sess["series"]) == 1
    assert sess["name"].startswith("Standard Panel — ")


# ---------------------------------------------------------------------------
# Wide grid — non-image series create their sample at submit time
# ---------------------------------------------------------------------------


def test_grid_renders_with_no_rows_yet(mocked_lookups):
    """Regression test: a freshly-assigned series with zero rows in BOTH grids
    used to crash with StreamlitAPIException — `pd.DataFrame(columns=...)`
    defaults every column to `object` dtype, which `DatetimeColumn`/
    `NumberColumn` reject. This is the very first state a user sees after
    assigning a series, before adding any sample or measurement row."""
    at = _at(_base_session(series=[dict(_GRID_SERIES_ITEM)])).run()
    assert not at.exception


def test_grid_row_creates_sample_and_submits(mock_apis):
    at = _at(_base_session(series=[dict(_GRID_SERIES_ITEM)]))
    _seed_grid(at, 1, [_row()])
    at.run()
    submit_btn = next(b for b in at.button if b.label == "✅  Submit Experiment")
    submit_btn.click().run()

    assert not _errors(at)
    mock_apis["create_sample"].assert_called_once()
    sample_payload = mock_apis["create_sample"].call_args[0][0]
    assert sample_payload["sampling_point_id"] == 1
    assert sample_payload["campaign_id"] == 1
    assert sample_payload["sample_collection_kind_id"] == 1
    assert sample_payload["sample_kind_id"] == 7  # "Field"
    assert sample_payload["sample_material_kind_id"] == 9  # "mixed liquor"
    assert sample_payload["sample_equipment_id"] == 1
    assert sample_payload["sample_datetime_start"] == _ROW_START.isoformat()

    mock_apis["ingest_lab"].assert_called_once()
    ingest_payload = mock_apis["ingest_lab"].call_args[0][0]
    assert len(ingest_payload["measurements"]) == 1
    m = ingest_payload["measurements"][0]
    assert m["parameter_id"] == 1
    assert m["sampling_point_id"] == 1
    assert m["sample_id"] == 42
    assert m["value"] == 12.3
    assert m["replicate"] == 1
    assert m["quality_code_id"] is None


def test_grid_same_sample_name_is_one_sample_with_replicates(mock_apis):
    """Two rows sharing a sample name are replicates of ONE physical sample:
    a single create_sample call, and replicate numbers derived from row order
    rather than typed by the user."""
    at = _at(_base_session(series=[dict(_GRID_SERIES_ITEM)]))
    _seed_grid(
        at,
        1,
        [
            _row(sample_label="S1", val_1=12.3),
            _row(sample_label="S1", val_1=12.9),
        ],
    )
    at.run()
    submit_btn = next(b for b in at.button if b.label == "✅  Submit Experiment")
    submit_btn.click().run()

    assert not _errors(at)
    mock_apis["create_sample"].assert_called_once()
    payload = mock_apis["ingest_lab"].call_args[0][0]
    assert [m["sample_id"] for m in payload["measurements"]] == [42, 42]
    assert [m["value"] for m in payload["measurements"]] == [12.3, 12.9]
    assert [m["replicate"] for m in payload["measurements"]] == [1, 2]


def test_grid_two_samples_create_two_samples(mock_apis):
    mock_apis["create_sample"].side_effect = [{"sample_id": 42}, {"sample_id": 43}]
    at = _at(_base_session(series=[dict(_GRID_SERIES_ITEM)]))
    _seed_grid(
        at,
        1,
        [_row(sample_label="S1", val_1=12.3), _row(sample_label="S2", val_1=15.0)],
    )
    at.run()
    submit_btn = next(b for b in at.button if b.label == "✅  Submit Experiment")
    submit_btn.click().run()

    assert mock_apis["create_sample"].call_count == 2
    payload = mock_apis["ingest_lab"].call_args[0][0]
    assert [m["sample_id"] for m in payload["measurements"]] == [42, 43]
    assert [m["replicate"] for m in payload["measurements"]] == [1, 1]


def test_grid_blank_sample_names_stand_alone(mock_apis):
    """A blank sample name doesn't collapse rows together — each unnamed row is
    its own physical sample, not replicate #2 of the previous one."""
    mock_apis["create_sample"].side_effect = [{"sample_id": 42}, {"sample_id": 43}]
    at = _at(_base_session(series=[dict(_GRID_SERIES_ITEM)]))
    _seed_grid(
        at,
        1,
        [_row(sample_label=None, val_1=12.3), _row(sample_label=None, val_1=15.0)],
    )
    at.run()
    submit_btn = next(b for b in at.button if b.label == "✅  Submit Experiment")
    submit_btn.click().run()

    assert mock_apis["create_sample"].call_count == 2
    payload = mock_apis["ingest_lab"].call_args[0][0]
    assert [m["sample_id"] for m in payload["measurements"]] == [42, 43]
    assert [m["replicate"] for m in payload["measurements"]] == [1, 1]


def test_grid_row_quality_code_and_notes_pass_through(mock_apis):
    at = _at(_base_session(series=[dict(_GRID_SERIES_ITEM)]))
    _seed_grid(
        at, 1, [_row(quality_code="Good — No issues", notes="split sample")]
    )
    at.run()
    submit_btn = next(b for b in at.button if b.label == "✅  Submit Experiment")
    submit_btn.click().run()

    payload = mock_apis["ingest_lab"].call_args[0][0]
    m = payload["measurements"][0]
    assert m["quality_code_id"] == 1
    assert m["notes"] == "split sample"


def test_grid_row_quality_code_and_notes_default_when_blank(mock_apis):
    at = _at(_base_session(series=[dict(_GRID_SERIES_ITEM)]))
    _seed_grid(at, 1, [_row()])
    at.run()
    submit_btn = next(b for b in at.button if b.label == "✅  Submit Experiment")
    submit_btn.click().run()

    payload = mock_apis["ingest_lab"].call_args[0][0]
    m = payload["measurements"][0]
    assert m["replicate"] == 1
    assert m["quality_code_id"] is None
    assert m["notes"] is None


def test_sample_missing_start_blocks_with_error(mock_apis):
    at = _at(_base_session(series=[dict(_GRID_SERIES_ITEM)]))
    _seed_grid(at, 1, [_row(start=None)])
    at.run()
    submit_btn = next(b for b in at.button if b.label == "✅  Submit Experiment")
    submit_btn.click().run()

    assert any("no start time" in e for e in _errors(at))
    mock_apis["create_sample"].assert_not_called()
    mock_apis["ingest_lab"].assert_not_called()


def test_grid_empty_measurements_no_measurements_error(mock_apis):
    at = _at(_base_session(series=[dict(_GRID_SERIES_ITEM)]))
    _seed_grid(at, 1, [_row(val_1=None)])
    at.run()
    submit_btn = next(b for b in at.button if b.label == "✅  Submit Experiment")
    submit_btn.click().run()

    assert any("No measurements to submit" in e for e in _errors(at))
    mock_apis["create_sample"].assert_not_called()
    mock_apis["ingest_lab"].assert_not_called()


def test_grid_submit_append_existing_minimal_payload(mock_apis):
    at = _at(_base_session(mode="existing", series=[dict(_GRID_SERIES_ITEM)]))
    _seed_grid(at, 1, [_row()])
    at.run()
    # sess["experiment_id"] is derived from its own selectbox every render —
    # seeding the dict directly isn't enough, the picker must be driven.
    at.selectbox(key="lab_existing_exp_sel").set_value("Exp 1 (2026-01-01)").run()
    submit_btn = next(b for b in at.button if b.label == "✅  Submit Experiment")
    submit_btn.click().run()

    mock_apis["ingest_lab"].assert_called_once()
    payload = mock_apis["ingest_lab"].call_args[0][0]
    assert set(payload.keys()) == {"experiment_id", "measurements"}
    assert payload["experiment_id"] == 1


# ---------------------------------------------------------------------------
# Image series — still resolved via the old per-sampling-point flow (D3)
# ---------------------------------------------------------------------------


def test_image_sample_creation_uses_old_flow(mock_apis):
    at = _at(_base_session(series=[dict(_IMAGE_SERIES_ITEM)])).run()
    at.button(key="lab_sp_create_0").click().run()

    assert not _errors(at)
    mock_apis["create_sample"].assert_called_once()
    payload = mock_apis["create_sample"].call_args[0][0]
    assert payload["sampling_point_id"] == 2
    sess = at.session_state.lab_session
    assert sess["samples"][0]["sample_id"] == 42


def test_submit_blocked_until_image_sample_resolved(mock_apis):
    at = _at(_base_session(series=[dict(_IMAGE_SERIES_ITEM)])).run()
    submit_btn = next(b for b in at.button if b.label == "Submit")
    assert submit_btn.disabled is True
