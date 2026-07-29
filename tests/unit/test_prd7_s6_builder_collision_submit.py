"""Composing measurements from a mapping spec, and refusing to collide.

A source row expands into one measurement per group; row- and file-scoped
values are shared across the measurements they cover. Foreign-key names are
resolved against a lookup pool at build time — an unmatched name aborts the
whole build and names itself and its column. Two measurements that would
land on the same sample, series and analytical replicate are refused before
anything is built for submission, naming where they collided.
"""

from __future__ import annotations

import datetime as dt
import zoneinfo
from pathlib import Path

import pandas as pd
import pytest

from app.components.column_mapping import build_spec, with_constant, with_group_constant
from app.components.field_catalogue import catalogue
from app.components.measurement_builder import build
from app.components.sheet_block import extract_block

UTC = zoneinfo.ZoneInfo("UTC")

REPO = Path(__file__).resolve().parents[2]
FIXTURE = REPO / "data" / "sample_data" / "CentrEau-COVID_Resultats_Quebec_2022.xlsx"
WQ_SHEET = "QC_Water_Quality"
WQ_HEADER_ROW = 4
WQ_DATA_ROW = 5

needs_fixture = pytest.mark.skipif(
    not FIXTURE.exists(), reason=f"acceptance workbook not present at {FIXTURE}"
)

_SAMPLING_POINTS = [{"sampling_point_id": 1, "label": "Site 1"}]
_PARAMETERS = [{"parameter_id": 7, "parameter_name": "TSS"}]
_UNITS = [{"unit_id": 3, "unit": "mg/L"}]
_LABORATORIES = [
    {"laboratory_id": 10, "name": "Ville de Quebec"},
    {"laboratory_id": 11, "name": "Universite Laval"},
]


def _lookup(table: str) -> list[dict]:
    return {
        "SamplingPoint": _SAMPLING_POINTS,
        "Parameter": _PARAMETERS,
        "Unit": _UNITS,
        "Laboratory": _LABORATORIES,
    }.get(table, [])


def _tss_grid() -> pd.DataFrame:
    """One parameter, two laboratories, side by side."""
    return pd.DataFrame(
        [
            ["date start", "TSS (VdQ data)", "TSS (ULaval data)"],
            [dt.datetime(2022, 3, 21, 22), 240.0, 235.0],
            [dt.datetime(2022, 3, 22, 22), 300.0, 295.0],
        ]
    )


@pytest.fixture
def tss_block():
    return extract_block(_tss_grid(), 0, 1)


def _base_spec(block, assignments, groups=None):
    spec = build_spec(block, catalogue(), assignments, groups)
    spec = with_constant(spec, "measurement.parameter_id", "TSS")
    spec = with_constant(spec, "measurement.unit_id", "mg/L")
    spec = with_constant(spec, "sample.sampling_point_id", "Site 1")
    spec = with_constant(spec, "batch.name", "Spring 2022 campaign")
    spec = with_constant(spec, "batch.experiment_datetime", dt.datetime(2022, 4, 1, 9))
    return spec


# --- one row, several value columns → several measurements -------------------


def test_one_row_two_value_columns_yields_two_measurements(tss_block):
    """Two value columns compose two measurements — differing labs, so no collision."""
    spec = _base_spec(tss_block, {0: "sample.sample_datetime_start", 1: "measurement.value", 2: "measurement.value"})
    spec = with_group_constant(spec, 1, "measurement.laboratory_id", "Ville de Quebec")
    spec = with_group_constant(spec, 2, "measurement.laboratory_id", "Universite Laval")
    result = build(spec, tss_block, catalogue(), _lookup, UTC, column_formats={})
    assert result.errors == () and result.collisions == ()
    assert len(result.rows) == 2  # two data rows
    for row in result.rows:
        assert len(row.measurements) == 2  # two groups per row
    assert result.counts() == {"experiments": 1, "samples": 2, "series": 2, "measurements": 4}


# --- the decisive case: two laboratories, one row ----------------------------


def test_two_laboratories_produce_two_series_no_collision(tss_block):
    spec = _base_spec(tss_block, {0: "sample.sample_datetime_start", 1: "measurement.value", 2: "measurement.value"})
    spec = with_group_constant(spec, 1, "measurement.laboratory_id", "Ville de Quebec")
    spec = with_group_constant(spec, 2, "measurement.laboratory_id", "Universite Laval")
    result = build(spec, tss_block, catalogue(), _lookup, UTC, column_formats={})
    assert result.ok
    assert result.counts()["series"] == 2  # laboratory differentiates the series
    assert result.counts()["measurements"] == 4
    first_row = result.rows[0]
    labs = {m.laboratory_id for m in first_row.measurements}
    assert labs == {10, 11}
    names = {m.series_name for m in first_row.measurements}
    assert names == {"TSS @ Site 1 (Ville de Quebec)", "TSS @ Site 1 (Universite Laval)"}


# --- constant scoping: file / row / measurement -------------------------------


def test_file_scope_constant_lands_on_the_experiment(tss_block):
    spec = _base_spec(tss_block, {0: "sample.sample_datetime_start", 1: "measurement.value"})
    result = build(spec, tss_block, catalogue(), _lookup, UTC, column_formats={})
    assert result.experiment["name"] == "Spring 2022 campaign"
    assert result.experiment["experiment_datetime"] == dt.datetime(2022, 4, 1, 9, tzinfo=dt.timezone.utc)


def test_row_scope_constant_lands_on_every_sample(tss_block):
    spec = _base_spec(tss_block, {0: "sample.sample_datetime_start", 1: "measurement.value"})
    result = build(spec, tss_block, catalogue(), _lookup, UTC, column_formats={})
    assert all(r.sample["sampling_point_id"] == 1 for r in result.rows)


def test_group_constant_only_reaches_its_own_measurement(tss_block):
    spec = _base_spec(tss_block, {0: "sample.sample_datetime_start", 1: "measurement.value", 2: "measurement.value"})
    spec = with_group_constant(spec, 1, "measurement.laboratory_id", "Ville de Quebec")
    result = build(spec, tss_block, catalogue(), _lookup, UTC, column_formats={})
    assert result.ok
    for row in result.rows:
        by_group = {m.group: m.laboratory_id for m in row.measurements}
        assert by_group[1] == 10
        assert by_group[2] is None  # group 2 never set a laboratory


# --- collision refusal --------------------------------------------------------


def test_two_groups_without_a_differentiator_collide():
    """Same parameter, same location, same replicate, no laboratory — a real collision."""
    grid = pd.DataFrame(
        [["date start", "value 1", "value 2"], [dt.datetime(2022, 3, 21, 22), 240.0, 235.0]]
    )
    block = extract_block(grid, 0, 1)
    spec = _base_spec(block, {0: "sample.sample_datetime_start", 1: "measurement.value", 2: "measurement.value"})
    result = build(spec, block, catalogue(), _lookup, UTC, column_formats={})
    assert result.errors == ()
    assert len(result.collisions) == 1
    assert "collapse onto the same sample, series and replicate" in result.collisions[0].message
    assert not result.ok


def test_differing_laboratories_are_not_a_collision(tss_block):
    spec = _base_spec(tss_block, {0: "sample.sample_datetime_start", 1: "measurement.value", 2: "measurement.value"})
    spec = with_group_constant(spec, 1, "measurement.laboratory_id", "Ville de Quebec")
    spec = with_group_constant(spec, 2, "measurement.laboratory_id", "Universite Laval")
    result = build(spec, tss_block, catalogue(), _lookup, UTC, column_formats={})
    assert result.collisions == ()


def test_differing_replicates_are_not_a_collision(tss_block):
    spec = _base_spec(tss_block, {0: "sample.sample_datetime_start", 1: "measurement.value", 2: "measurement.value"})
    spec = with_group_constant(spec, 1, "measurement.replicate", 1)
    spec = with_group_constant(spec, 2, "measurement.replicate", 2)
    result = build(spec, tss_block, catalogue(), _lookup, UTC, column_formats={})
    assert result.collisions == ()


# --- unmatched names fail loudly and name themselves --------------------------


def test_unmatched_constant_name_names_the_field(tss_block):
    spec = _base_spec(tss_block, {0: "sample.sample_datetime_start", 1: "measurement.value"})
    spec = with_constant(spec, "measurement.parameter_id", "Not A Real Parameter")
    result = build(spec, tss_block, catalogue(), _lookup, UTC, column_formats={})
    assert len(result.errors) == 1
    assert "'Not A Real Parameter'" in result.errors[0].message
    assert result.rows == ()


def test_unmatched_column_name_names_the_column():
    grid = pd.DataFrame(
        [
            ["date start", "value", "site"],
            [dt.datetime(2022, 3, 21, 22), 240.0, "Nowhere"],
        ]
    )
    block = extract_block(grid, 0, 1)
    spec = build_spec(
        block,
        catalogue(),
        {0: "sample.sample_datetime_start", 1: "measurement.value", 2: "sample.sampling_point_id"},
    )
    spec = with_constant(spec, "measurement.parameter_id", "TSS")
    spec = with_constant(spec, "measurement.unit_id", "mg/L")
    spec = with_constant(spec, "batch.name", "Spring 2022 campaign")
    spec = with_constant(spec, "batch.experiment_datetime", dt.datetime(2022, 4, 1, 9))
    result = build(spec, block, catalogue(), _lookup, UTC, column_formats={})
    assert len(result.errors) == 1
    message = result.errors[0].message
    assert "'Nowhere'" in message
    assert "'site'" in message and "column 2" in message


def test_missing_required_field_aborts_before_resolving_names(tss_block):
    spec = build_spec(tss_block, catalogue(), {0: "sample.sample_datetime_start", 1: "measurement.value"})
    # no parameter, unit, sampling point, batch name/datetime set at all
    result = build(spec, tss_block, catalogue(), _lookup, UTC, column_formats={})
    assert result.errors
    assert result.rows == ()


# --- sparse sheets: an empty measurement cell is skipped, not an error --------


def test_empty_value_cell_is_skipped_silently():
    grid = _tss_grid()
    grid.iloc[2, 2] = None  # second row's second value column is blank
    block = extract_block(grid, 0, 1)
    spec = _base_spec(block, {0: "sample.sample_datetime_start", 1: "measurement.value", 2: "measurement.value"})
    result = build(spec, block, catalogue(), _lookup, UTC, column_formats={})
    assert result.errors == ()
    counts_by_row = {r.row: len(r.measurements) for r in result.rows}
    assert counts_by_row[1] == 2
    assert counts_by_row[2] == 1  # the blank cell contributed no measurement


# --- unresolved date formats abort loudly, naming the column -----------------


def test_unresolved_date_format_aborts_and_names_the_column():
    grid = pd.DataFrame(
        [
            ["date start", "value"],
            ["21/03/2022", 240.0],
            ["22/03/2022", 300.0],
        ]
    )
    block = extract_block(grid, 0, 1)
    spec = _base_spec(block, {0: "sample.sample_datetime_start", 1: "measurement.value"})
    result = build(spec, block, catalogue(), _lookup, UTC, column_formats={})
    assert len(result.errors) == 1
    assert "date format" in result.errors[0].message
    assert "column 0" in result.errors[0].message


def test_a_chosen_date_format_resolves_the_column():
    grid = pd.DataFrame(
        [
            ["date start", "value"],
            ["21/03/2022", 240.0],
        ]
    )
    block = extract_block(grid, 0, 1)
    spec = _base_spec(block, {0: "sample.sample_datetime_start", 1: "measurement.value"})
    result = build(spec, block, catalogue(), _lookup, UTC, column_formats={0: "%d/%m/%Y"})
    assert result.ok
    assert result.rows[0].sample["sample_datetime_start"] == dt.datetime(2022, 3, 21, tzinfo=dt.timezone.utc)


# --- the real fixture: two laboratories, side by side, hundreds of rows ------


@needs_fixture
def test_tss_two_laboratories_build_cleanly_on_the_real_fixture():
    grid = pd.read_excel(FIXTURE, sheet_name=WQ_SHEET, header=None)
    block = extract_block(grid, WQ_HEADER_ROW, WQ_DATA_ROW)
    headers = dict(zip(block.columns, block.headers))
    assert headers[5] == "TSS (mg/L) (VdQ data)"
    assert headers[6] == "TSS (mg/L) (ULaval data)"
    spec = build_spec(
        block,
        catalogue(),
        {0: "sample.sample_datetime_start", 5: "measurement.value", 6: "measurement.value"},
    )
    spec = with_constant(spec, "measurement.parameter_id", "TSS")
    spec = with_constant(spec, "measurement.unit_id", "mg/L")
    spec = with_constant(spec, "sample.sampling_point_id", "Fin du Réseau - Intercepteur Est (Site 1)")
    spec = with_group_constant(spec, 5, "measurement.laboratory_id", "Ville de Québec")
    spec = with_group_constant(spec, 6, "measurement.laboratory_id", "Université Laval")
    spec = with_constant(spec, "batch.name", "Spring 2022 campaign")
    spec = with_constant(spec, "batch.experiment_datetime", dt.datetime(2022, 4, 1, 9))

    def lookup(table: str) -> list[dict]:
        return {
            "SamplingPoint": [{"sampling_point_id": 1, "label": "Fin du Réseau - Intercepteur Est (Site 1)"}],
            "Parameter": [{"parameter_id": 7, "parameter_name": "TSS"}],
            "Unit": [{"unit_id": 3, "unit": "mg/L"}],
            "Laboratory": [
                {"laboratory_id": 10, "name": "Ville de Québec"},
                {"laboratory_id": 11, "name": "Université Laval"},
            ],
        }.get(table, [])

    result = build(spec, block, catalogue(), lookup, UTC, column_formats={})
    assert result.errors == ()
    assert result.collisions == ()  # differing laboratories keep every row's pair apart
    counts = result.counts()
    assert counts["series"] == 2
    assert counts["measurements"] > 600  # hundreds of rows, two measurements each


# --- the page: pre-submit summary, collision gate, per-row reporting ---------

_SHEET = "Synthetic"


def _page_grid() -> pd.DataFrame:
    return pd.DataFrame(
        [
            ["date start", "value"],
            [dt.datetime(2022, 3, 21, 22), 240.0],
            [dt.datetime(2022, 3, 22, 22), 300.0],
        ]
    )


def _synthetic_sheet_script():  # pragma: no cover - executed inside AppTest
    from app.pages import sheet_import
    from tests.unit.test_prd7_s6_builder_collision_submit import _page_grid

    sheet_import._sheet_ui("Synthetic", _page_grid())


def _run_synthetic_sheet():
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_function(_synthetic_sheet_script, default_timeout=60)
    at.session_state[f"sheet_header_row::{_SHEET}"] = 0
    at.session_state[f"sheet_data_row::{_SHEET}"] = 1
    at.session_state[f"sheet_tz::{_SHEET}"] = "UTC"
    at.run()
    return at


def _collision_grid() -> pd.DataFrame:
    return pd.DataFrame(
        [["date start", "value 1", "value 2"], [dt.datetime(2022, 3, 21, 22), 240.0, 235.0]]
    )


def _synthetic_collision_script():  # pragma: no cover - executed inside AppTest
    from app.pages import sheet_import
    from tests.unit.test_prd7_s6_builder_collision_submit import _collision_grid

    sheet_import._sheet_ui("Synthetic", _collision_grid())


def _run_synthetic_collision_sheet():
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_function(_synthetic_collision_script, default_timeout=60)
    at.session_state[f"sheet_header_row::{_SHEET}"] = 0
    at.session_state[f"sheet_data_row::{_SHEET}"] = 1
    at.session_state[f"sheet_tz::{_SHEET}"] = "UTC"
    at.run()
    return at


def _by_key(at, kind: str, key: str):
    return next(el for el in getattr(at, kind) if el.key == key)


def _resolvable_spec(block):
    spec = build_spec(block, catalogue(), {0: "sample.sample_datetime_start", 1: "measurement.value"})
    spec = with_constant(spec, "measurement.parameter_id", "TSS")
    spec = with_constant(spec, "measurement.unit_id", "mg/L")
    spec = with_constant(spec, "sample.sampling_point_id", "Site 1")
    spec = with_constant(spec, "batch.name", "Spring 2022 campaign")
    spec = with_constant(spec, "batch.experiment_datetime", dt.datetime(2022, 4, 1, 9))
    return spec


def test_submit_section_shows_the_presubmit_summary(monkeypatch):
    from app import api_client as api

    monkeypatch.setattr(api, "list_sampling_point_lookup", lambda: _SAMPLING_POINTS)
    monkeypatch.setattr(api, "list_parameter_lookup", lambda: _PARAMETERS)
    monkeypatch.setattr(api, "list_unit_lookup", lambda: _UNITS)
    block = extract_block(_page_grid(), 0, 1)
    at = _run_synthetic_sheet()
    at.session_state[f"sheet_mapping::{_SHEET}"] = _resolvable_spec(block)
    at.run()
    assert not at.exception
    info = " ".join(el.value for el in at.info)
    assert "Ready to write" in info and "2" in info  # two data rows, two samples
    submit = _by_key(at, "button", f"sheet_submit::{_SHEET}")
    assert not submit.disabled


def test_submit_section_disables_the_button_on_a_collision(monkeypatch):
    from app import api_client as api

    monkeypatch.setattr(api, "list_sampling_point_lookup", lambda: _SAMPLING_POINTS)
    monkeypatch.setattr(api, "list_parameter_lookup", lambda: _PARAMETERS)
    monkeypatch.setattr(api, "list_unit_lookup", lambda: _UNITS)
    block = extract_block(_collision_grid(), 0, 1)
    spec = build_spec(
        block, catalogue(), {0: "sample.sample_datetime_start", 1: "measurement.value", 2: "measurement.value"}
    )
    spec = with_constant(spec, "measurement.parameter_id", "TSS")
    spec = with_constant(spec, "measurement.unit_id", "mg/L")
    spec = with_constant(spec, "sample.sampling_point_id", "Site 1")
    spec = with_constant(spec, "batch.name", "Spring 2022 campaign")
    spec = with_constant(spec, "batch.experiment_datetime", dt.datetime(2022, 4, 1, 9))

    at = _run_synthetic_collision_sheet()
    at.session_state[f"sheet_mapping::{_SHEET}"] = spec
    at.run()
    assert not at.exception
    errors = " ".join(el.value for el in at.error)
    assert "collapse onto the same sample, series and replicate" in errors
    submit = _by_key(at, "button", f"sheet_submit::{_SHEET}")
    assert submit.disabled


def test_submit_button_sends_one_request_for_samples_and_one_for_measurements(monkeypatch):
    from app import api_client as api

    monkeypatch.setattr(api, "list_sampling_point_lookup", lambda: _SAMPLING_POINTS)
    monkeypatch.setattr(api, "list_parameter_lookup", lambda: _PARAMETERS)
    monkeypatch.setattr(api, "list_unit_lookup", lambda: _UNITS)
    calls = {"create_samples": 0, "ingest_lab": 0}
    sent: dict = {}

    def fake_create_samples(samples):
        calls["create_samples"] += 1
        sent["samples"] = samples
        return {"sample_ids": [100 + i for i in range(len(samples))]}

    def fake_ingest_lab(data):
        calls["ingest_lab"] += 1
        sent["measurements"] = data["measurements"]
        return {"lab_experiment_id": 42, "rows_written": len(data["measurements"])}

    monkeypatch.setattr(api, "create_samples", fake_create_samples)
    monkeypatch.setattr(api, "ingest_lab", fake_ingest_lab)

    block = extract_block(_page_grid(), 0, 1)
    at = _run_synthetic_sheet()
    at.session_state[f"sheet_mapping::{_SHEET}"] = _resolvable_spec(block)
    at.run()
    assert not at.exception
    _by_key(at, "button", f"sheet_submit::{_SHEET}").click()
    at.run()
    assert not at.exception
    assert calls == {"create_samples": 1, "ingest_lab": 1}
    assert len(sent["samples"]) == 2  # two data rows, two distinct samples
    assert len(sent["measurements"]) == 2
    success = " ".join(el.value for el in at.success)
    assert "Wrote 2 measurement(s) across 2 sample(s)" in success
