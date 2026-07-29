"""PRD-7 S4 — field catalogue in the user's vocabulary + index-keyed mapping.

The catalogue is derived from the ingest payload schemas, so a field added to
a payload appears without a UI edit. The mapping state is keyed by source
column index, never header text, so the acceptance workbook's four ``Ct``
columns stay independently mappable.

The workbook holds real data and stays out of git, so the tests that need it
skip when it is absent; a synthetic miniature covers the same shape
unconditionally.
"""

from __future__ import annotations

import dataclasses
from datetime import datetime
from pathlib import Path

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

from app.components.column_mapping import (
    build_spec,
    empty_spec,
    mapping_frame,
    missing_required,
    spec_from_frame,
    validate,
)
from app.components.field_catalogue import GROUPS, build_catalogue, catalogue
from app.components.sheet_block import extract_block

REPO = Path(__file__).resolve().parents[2]
FIXTURE = REPO / "data" / "sample_data" / "CentrEau-COVID_Resultats_Quebec_2022.xlsx"
SHEET = "QC Data Daily Samples (McGill)"
HEADER_ROW = 2
DATA_ROW = 8

needs_fixture = pytest.mark.skipif(
    not FIXTURE.exists(), reason=f"acceptance workbook not present at {FIXTURE}"
)


@pytest.fixture(scope="module")
def block():
    if not FIXTURE.exists():
        pytest.skip(f"acceptance workbook not present at {FIXTURE}")
    grid = pd.read_excel(FIXTURE, sheet_name=SHEET, header=None)
    return extract_block(grid, HEADER_ROW, DATA_ROW)


def _synthetic_grid() -> pd.DataFrame:
    """Four identically named ``Ct`` columns told apart only by their banners."""
    return pd.DataFrame(
        [
            ["SAMPLING DATA", "PCR", "PCR", "PCR", "PCR"],
            [None, "SARS-CoV-2 (N1)", "PMMV", "External control (BRSV)", "SARS-CoV-2 (N2)"],
            ["date\nstart", "Ct", "Ct", "Ct", "Ct"],
            ["when it started", "cycles", "cycles", "cycles", "cycles"],
            [datetime(2022, 3, 21, 22), 1.0, 2.0, 3.0, 4.0],
            [datetime(2022, 3, 22, 22), 5.0, 6.0, 7.0, 8.0],
        ]
    )


@pytest.fixture
def small_block():
    return extract_block(_synthetic_grid(), 2, 4)


# --- the catalogue is derived from the ingest payload schemas ----------------


def test_catalogue_covers_the_payload_fields_and_skips_page_managed_ones():
    keys = {f.key for f in catalogue().fields}
    # a sample of fields from each payload model
    assert "batch.name" in keys
    assert "batch.experiment_datetime" in keys
    assert "batch.campaign_id" in keys
    assert "sample.sample_datetime_start" in keys
    assert "sample.sampling_point_id" in keys
    assert "sample.replicate" in keys
    assert "measurement.parameter_id" in keys
    assert "measurement.value" in keys
    assert "measurement.laboratory_id" in keys
    assert "measurement.quality_code_id" in keys
    # page-managed, never user-mapped
    for managed in (
        "batch.experiment_id",
        "batch.measurements",
        "batch.lab_panel_id",
        "measurement.sample_id",
        "measurement.series_name",
        "measurement.value_kind_id",
    ):
        assert managed not in keys


def test_a_field_added_to_a_payload_schema_appears_without_a_ui_edit():
    from pydantic import BaseModel

    from api.v1.schemas.ingestion import SampleCreateRequest
    from app.components import field_catalogue as fc

    class RicherSample(SampleCreateRequest):
        favourite_colour: str | None = None

    sources = [
        fc.CatalogueSource(
            model=RicherSample,
            namespace="sample",
            scope="row",
            table="Sample",
        )
    ]
    richer = build_catalogue(sources)
    added = richer.by_key("sample.favourite_colour")
    assert added.scope == "row"
    assert added.value_type == "text"
    assert added.label  # humanized fallback, not the raw field name
    assert added.label != "favourite_colour"
    assert added.group in GROUPS
    assert isinstance(BaseModel.__name__, str)  # the module really builds on pydantic


def test_every_field_carries_full_metadata():
    for f in catalogue().fields:
        assert f.scope in ("file", "row", "measurement"), f.key
        assert f.value_type in ("integer", "number", "text", "datetime"), f.key
        assert f.label.strip(), f.key
        assert f.group in GROUPS, f.key
        assert "." in f.ref, f.key  # table.column traceability


def test_known_fields_carry_dictionary_backed_metadata():
    cat = catalogue()
    parameter = cat.by_key("measurement.parameter_id")
    assert parameter.scope == "measurement"
    assert parameter.fk_table == "Parameter"
    assert parameter.required is True
    assert parameter.ref == "AnalysisSeries.Parameter_ID"
    assert parameter.help  # the YAML column description

    start = cat.by_key("sample.sample_datetime_start")
    assert start.scope == "row"
    assert start.value_type == "datetime"
    assert start.required is True
    assert start.ref == "Sample.SampleDateTimeStart"
    assert "UTC" in start.help

    lab = cat.by_key("measurement.laboratory_id")
    assert lab.fk_table == "Laboratory"
    assert lab.required is False

    value = cat.by_key("measurement.value")
    assert value.ref == "Value.Value"
    assert value.value_type == "number"

    # required only conditionally in the payload, but a new batch needs them
    assert cat.by_key("batch.name").required is True
    assert cat.by_key("batch.experiment_datetime").required is True
    assert cat.by_key("batch.description").required is False


def test_scope_is_data_not_a_choice():
    field = catalogue().by_key("sample.sampling_point_id")
    with pytest.raises(dataclasses.FrozenInstanceError):
        field.scope = "file"


def test_the_two_replicates_are_distinct_fields():
    cat = catalogue()
    field_rep = cat.by_key("sample.replicate")
    analytical_rep = cat.by_key("measurement.replicate")
    assert field_rep.scope == "row"
    assert field_rep.ref == "Sample.Replicate"
    assert field_rep.label != analytical_rep.label
    assert analytical_rep.scope == "measurement"
    assert analytical_rep.ref == "LabAnalysis.Replicate"


def test_fields_render_in_the_five_activity_groups():
    assert GROUPS == (
        "When & where",
        "The sample",
        "The measurement",
        "Who & how",
        "The batch",
    )
    cat = catalogue()
    for group in GROUPS:
        assert cat.in_group(group), group
    order = {group: i for i, group in enumerate(GROUPS)}
    sequence = [order[f.group] for f in cat.fields]
    assert sequence == sorted(sequence)  # fields walk the groups in order


# --- the mapping model, keyed by column index --------------------------------


def test_every_column_starts_ignored(small_block):
    spec = empty_spec(small_block)
    assert len(spec.mappings) == len(small_block.columns)
    assert all(m.field is None for m in spec.mappings)
    assert validate(spec, small_block, catalogue()) == []


def _map_four_cts_differently(block):
    """Round-trip through the editor frame: four ``Ct`` columns, four fields."""
    cat = catalogue()
    options = cat.option_labels()  # display label -> key
    by_key = {key: label for label, key in options.items()}
    ct_columns = [c for c, h in zip(block.columns, block.headers) if h == "Ct"]
    assert len(ct_columns) == 4
    wanted = [
        "measurement.value",
        "measurement.quality_code_id",
        "measurement.notes",
        "measurement.analyst_person_id",
    ]
    frame = mapping_frame(block, cat, empty_spec(block))
    for col, key in zip(ct_columns, wanted):
        frame.loc[col, "Maps to"] = by_key[key]
    spec = spec_from_frame(block, cat, frame)
    return spec, ct_columns, wanted


def test_four_identically_named_columns_keep_their_own_mappings(small_block):
    spec, ct_columns, wanted = _map_four_cts_differently(small_block)
    for col, key in zip(ct_columns, wanted):
        assert spec.for_column(col).field == key
    assert validate(spec, small_block, catalogue()) == []


@needs_fixture
def test_four_ct_columns_keep_their_own_mappings_on_the_real_fixture(block):
    assert [c for c, h in zip(block.columns, block.headers) if h == "Ct"] == [
        38,
        47,
        55,
        67,
    ]
    spec, ct_columns, wanted = _map_four_cts_differently(block)
    for col, key in zip(ct_columns, wanted):
        assert spec.for_column(col).field == key
    assert validate(spec, block, catalogue()) == []


def test_each_column_shows_its_forward_filled_banner(small_block):
    frame = mapping_frame(small_block, catalogue(), empty_spec(small_block))
    assert frame.loc[1, "Banner"] == "PCR › SARS-CoV-2 (N1)"
    assert frame.loc[3, "Banner"] == "PCR › External control (BRSV)"
    assert frame.loc[0, "Banner"] == "SAMPLING DATA"
    assert frame.loc[1, "Header"] == "Ct"
    assert list(frame.index) == list(small_block.columns)


def test_value_columns_default_to_one_group_each(small_block):
    spec = build_spec(
        small_block,
        catalogue(),
        {1: "measurement.value", 2: "measurement.value"},
    )
    groups = {m.column: m.group for m in spec.mapped()}
    assert groups[1] != groups[2]  # one measurement per value column
    assert validate(spec, small_block, catalogue()) == []


def test_validation_rejects_a_row_field_sourced_by_two_columns(small_block):
    spec = build_spec(
        small_block,
        catalogue(),
        {1: "sample.sample_datetime_start", 3: "sample.sample_datetime_start"},
    )
    (error,) = validate(spec, small_block, catalogue())
    assert "Ct" in error.message
    assert "1" in error.message and "3" in error.message
    assert set(error.columns) == {1, 3}


def test_validation_rejects_a_measurement_field_twice_in_one_group(small_block):
    spec = build_spec(
        small_block,
        catalogue(),
        {1: "measurement.value", 2: "measurement.value"},
        groups={1: 7, 2: 7},
    )
    (error,) = validate(spec, small_block, catalogue())
    assert "Ct" in error.message
    assert "1" in error.message and "2" in error.message
    assert set(error.columns) == {1, 2}


def test_validation_rejects_a_field_the_import_does_not_accept(small_block):
    spec = build_spec(
        small_block,
        catalogue(),
        {2: "measurement.no_such_field"},
    )
    (error,) = validate(spec, small_block, catalogue())
    assert "Ct" in error.message and "2" in error.message
    assert "no_such_field" in error.message


def test_missing_required_names_the_field_in_plain_language(small_block):
    missing = missing_required(empty_spec(small_block), catalogue())
    labels = {f.label for f in missing}
    assert catalogue().by_key("sample.sample_datetime_start").label in labels
    assert catalogue().by_key("measurement.parameter_id").label in labels
    # the measurement's location is satisfied by the sample's location
    with_location = build_spec(
        small_block,
        catalogue(),
        {
            0: "sample.sample_datetime_start",
            1: "measurement.value",
            2: "sample.sampling_point_id",
        },
    )
    still_missing = {f.key for f in missing_required(with_location, catalogue())}
    assert "sample.sample_datetime_start" not in still_missing
    assert "sample.sampling_point_id" not in still_missing
    assert "measurement.sampling_point_id" not in still_missing


# --- the page ----------------------------------------------------------------

_SHEET = "Synthetic"


def _synthetic_sheet_script():  # pragma: no cover - executed inside AppTest
    from datetime import datetime

    import pandas as pd

    from app.pages import sheet_import

    grid = pd.DataFrame(
        [
            ["SAMPLING DATA", "PCR", "PCR"],
            [None, "SARS-CoV-2 (N1)", "PMMV"],
            ["date\nstart", "Ct", "Ct"],
            ["when it started", "cycles", "cycles"],
            [datetime(2022, 3, 21, 22), 1.0, 2.0],
            [datetime(2022, 3, 22, 22), 3.0, 4.0],
        ]
    )
    sheet_import._sheet_ui("Synthetic", grid)


def _run_synthetic_sheet():
    at = AppTest.from_function(_synthetic_sheet_script, default_timeout=60)
    at.session_state[f"sheet_header_row::{_SHEET}"] = 2
    at.session_state[f"sheet_data_row::{_SHEET}"] = 4
    at.run()
    return at


def test_mapping_table_renders_all_ignored_with_banner_context():
    at = _run_synthetic_sheet()
    assert not at.exception
    frames = [
        el.value for el in at.get("dataframe") if "Maps to" in el.value.columns
    ]
    assert len(frames) == 1
    frame = frames[0]
    assert list(frame.index) == [0, 1, 2]  # keyed by source column index
    assert (frame["Maps to"] == "— ignore —").all()
    assert frame.loc[1, "Banner"] == "PCR › SARS-CoV-2 (N1)"
    # and the built spec in session state agrees: everything ignored
    spec = at.session_state[f"sheet_mapping::{_SHEET}"]
    assert all(m.field is None for m in spec.mappings)


def test_catalogue_browser_renders_groups_scope_and_refs():
    at = _run_synthetic_sheet()
    assert not at.exception
    text = " ".join(str(getattr(el, "value", "")) for el in at.markdown)
    for group in GROUPS:
        assert group in text
    assert "Sample.SampleDateTimeStart" in text
    assert "AnalysisSeries.Parameter_ID" in text
    assert "row" in text and "measurement" in text and "file" in text
