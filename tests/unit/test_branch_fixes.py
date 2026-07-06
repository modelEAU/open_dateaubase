"""Red→green guards for the prd-get-started branch fixes.

Covers the four non-trivial changes whose logic isn't already exercised:
  1. The Equipment-Move 500 root cause — no repository still queries the dropped
     EquipmentEvent / EquipmentEventKind / EquipmentInstallation tables.
  2. Sensor-ingest cascading filters (_params_for_model / _units_for_param).
  3. The new ECharts option builders for vector/matrix views.
"""

from __future__ import annotations

from pathlib import Path

import pytest

_REPO_DIR = Path(__file__).parent.parent.parent / "api" / "v1" / "repositories"

# Tables removed by the PRD-2 unified-Event migration; any live SQL reference to
# them is a runtime 500 waiting to happen (this is exactly the Equipment-Move bug).
_DROPPED_TABLES = ["EquipmentEvent", "EquipmentEventKind", "EquipmentInstallation"]


@pytest.mark.parametrize("repo_path", sorted(_REPO_DIR.glob("*.py")), ids=lambda p: p.name)
def test_no_repository_queries_dropped_tables(repo_path):
    src = repo_path.read_text()
    for table in _DROPPED_TABLES:
        assert f"[dbo].[{table}]" not in src, (
            f"{repo_path.name} still queries dropped table [dbo].[{table}] — "
            "this raises 'Invalid object name' at runtime (500)."
        )


# ---------------------------------------------------------------------------
# Sensor-ingest cascading filters
# ---------------------------------------------------------------------------


def test_params_for_model_scopes_to_model(monkeypatch):
    import app.components.ingest_shapes as ing

    monkeypatch.setattr(ing.st, "session_state", {}, raising=False)
    monkeypatch.setattr(
        ing, "list_model_parameters", lambda mid: [{"parameter_id": 1, "parameter_name": "pH"}]
    )
    all_params = [{"parameter_id": 9, "parameter_name": "TSS"}]
    got, note = ing._params_for_model(5, all_params)
    assert [p["parameter_name"] for p in got] == ["pH"]
    assert note is None


def test_params_for_model_none_returns_all(monkeypatch):
    import app.components.ingest_shapes as ing

    monkeypatch.setattr(ing.st, "session_state", {}, raising=False)
    all_params = [{"parameter_id": 9, "parameter_name": "TSS"}]
    got, note = ing._params_for_model(None, all_params)
    assert got is all_params and note is None


def test_params_for_model_empty_falls_back_with_note(monkeypatch):
    import app.components.ingest_shapes as ing

    monkeypatch.setattr(ing.st, "session_state", {}, raising=False)
    monkeypatch.setattr(ing, "list_model_parameters", lambda mid: [])
    all_params = [{"parameter_id": 9, "parameter_name": "TSS"}]
    got, note = ing._params_for_model(5, all_params)
    assert got is all_params and note is not None


def test_units_for_param_scopes_to_parameter(monkeypatch):
    import app.components.ingest_shapes as ing

    monkeypatch.setattr(ing.st, "session_state", {}, raising=False)
    monkeypatch.setattr(
        ing, "list_parameter_units", lambda pid: [{"unit_id": 2, "unit": "mg/L"}]
    )
    all_units = [{"unit_id": 7, "unit": "NTU"}]
    got, note = ing._units_for_param(3, all_units)
    assert [u["unit"] for u in got] == ["mg/L"]
    assert note is None


# ---------------------------------------------------------------------------
# ECharts option builders (vector / matrix)
# ---------------------------------------------------------------------------

_VECTOR = {
    "parameter": "PSD",
    "unit": "-",
    "data": [
        {"timestamp": "t1", "bin_index": 0, "nominal_value": 1.0, "value": 10.0,
         "axis_name": "Particle size", "axis_unit": "nm"},
        {"timestamp": "t1", "bin_index": 1, "nominal_value": 2.0, "value": 20.0,
         "axis_name": "Particle size", "axis_unit": "nm"},
        {"timestamp": "t2", "bin_index": 0, "nominal_value": 1.0, "value": 30.0,
         "axis_name": "Particle size", "axis_unit": "nm"},
        {"timestamp": "t2", "bin_index": 1, "nominal_value": 2.0, "value": 40.0,
         "axis_name": "Particle size", "axis_unit": "nm"},
    ],
}


def test_vector_heatmap_option():
    from app.components.explore_vector import build_vector_heatmap_option

    opt = build_vector_heatmap_option(_VECTOR)
    assert opt["series"][0]["type"] == "heatmap"
    assert opt["xAxis"]["data"] == ["t1", "t2"]
    assert len(opt["series"][0]["data"]) == 4  # 2 timestamps × 2 bins
    # Bin axis labelled by its binning-axis name + unit, not a literal "Bin".
    assert opt["yAxis"]["name"] == "Particle size (nm)"


def test_vector_bin_axis_falls_back_to_bin_without_units():
    from app.components.explore_vector import build_vector_heatmap_option

    bare = {**_VECTOR, "data": [
        {"timestamp": "t1", "bin_index": 0, "nominal_value": 1.0, "value": 10.0},
    ]}
    assert build_vector_heatmap_option(bare)["yAxis"]["name"] == "Bin"


def test_vector_slice_time_option_is_line():
    from app.components.explore_vector import build_vector_slice_time_option

    opt = build_vector_slice_time_option(_VECTOR, "t1")
    assert opt["series"][0]["type"] == "line"
    assert opt["series"][0]["data"] == [10.0, 20.0]
    assert opt["xAxis"]["name"] == "Particle size (nm)"


def test_matrix_timeslice_option():
    from app.components.explore_matrix import build_matrix_timeslice_option

    data = {
        "data": [
            {"timestamp": "t1", "row_bin_index": 0, "row_nominal_value": 0.0,
             "col_bin_index": 0, "col_nominal_value": 0.0, "value": 5.0,
             "row_axis_name": "Excitation", "row_axis_unit": "nm",
             "col_axis_name": "Emission", "col_axis_unit": "nm"},
            {"timestamp": "t1", "row_bin_index": 0, "row_nominal_value": 0.0,
             "col_bin_index": 1, "col_nominal_value": 1.0, "value": 6.0,
             "row_axis_name": "Excitation", "row_axis_unit": "nm",
             "col_axis_name": "Emission", "col_axis_unit": "nm"},
        ]
    }
    opt = build_matrix_timeslice_option(data, "t1")
    assert opt["series"][0]["type"] == "heatmap"
    # Row/col axes labelled by binning-axis name + unit, not "Row bin"/"Column bin".
    assert opt["yAxis"]["name"] == "Excitation (nm)"
    assert opt["xAxis"]["name"] == "Emission (nm)"
    assert len(opt["series"][0]["data"]) == 2
