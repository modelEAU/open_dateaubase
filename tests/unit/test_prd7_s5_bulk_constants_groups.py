"""PRD-7 S5 — bulk apply, constants, and per-group identity.

A span of columns takes one bulk action, index-based. Any field can take a
typed constant applied across its scope; the field replicate defaults to the
constant 1. Measurement groups carry their own full identity — parameter,
unit, laboratory, location — sourced independently per group, which is what
lets the acceptance workbook's ``TSS (VdQ data)`` and ``TSS (ULaval data)``
columns become two measurements differing only by laboratory.

The workbook holds real data and stays out of git, so the fixture tests skip
when it is absent; synthetic miniatures cover the same shapes unconditionally.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

from app.components.column_mapping import (
    BULK_IGNORE,
    BULK_SET_FIELD,
    BULK_VALUE_EACH,
    BULK_VALUE_SAME,
    ConstantMapping,
    GroupConstant,
    MappingSpec,
    apply_bulk,
    build_spec,
    constant_for,
    empty_spec,
    group_series,
    groups_lacking,
    groups_of,
    identity_for_group,
    mapping_frame,
    missing_required,
    row_series,
    source_for,
    spec_from_frame,
    validate,
    with_constant,
    with_group_constant,
)
from app.components.field_catalogue import catalogue
from app.components.sheet_block import extract_block

REPO = Path(__file__).resolve().parents[2]
FIXTURE = REPO / "data" / "sample_data" / "CentrEau-COVID_Resultats_Quebec_2022.xlsx"
WQ_SHEET = "QC_Water_Quality"
WQ_HEADER_ROW = 4
WQ_DATA_ROW = 5

needs_fixture = pytest.mark.skipif(
    not FIXTURE.exists(), reason=f"acceptance workbook not present at {FIXTURE}"
)


def _ct_grid() -> pd.DataFrame:
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


def _tss_grid() -> pd.DataFrame:
    """One parameter reported by two laboratories, per-site banner context."""
    return pd.DataFrame(
        [
            ["SAMPLING DATA", "Site 1", "Site 1"],
            [None, "VdQ", "ULaval"],
            ["date\nstart", "TSS (mg/L) (VdQ data)", "TSS (mg/L) (ULaval data)"],
            ["when it started", "lab value", "lab value"],
            [datetime(2022, 3, 21, 22), 240.0, 235.0],
            [datetime(2022, 3, 22, 22), 300.0, 295.0],
        ]
    )


@pytest.fixture
def ct_block():
    return extract_block(_ct_grid(), 2, 4)


@pytest.fixture
def tss_block():
    return extract_block(_tss_grid(), 2, 4)


@pytest.fixture(scope="module")
def wq_block():
    if not FIXTURE.exists():
        pytest.skip(f"acceptance workbook not present at {FIXTURE}")
    grid = pd.read_excel(FIXTURE, sheet_name=WQ_SHEET, header=None)
    return extract_block(grid, WQ_HEADER_ROW, WQ_DATA_ROW)


# --- the field replicate defaults to the constant 1 ---------------------------


def test_empty_spec_defaults_field_replicate_to_constant_1(ct_block):
    spec = empty_spec(ct_block)
    assert constant_for(spec, "sample.replicate") == 1
    # …and it satisfies the model with no user action and no incoherence
    assert validate(spec, ct_block, catalogue()) == []
    missing = {f.key for f in missing_required(spec, catalogue())}
    assert "sample.replicate" not in missing


# --- bulk actions, index-based -------------------------------------------------


def test_bulk_ignore_all_clears_selected_columns_only(ct_block):
    spec = build_spec(
        ct_block,
        catalogue(),
        {0: "sample.sample_datetime_start", 1: "measurement.value", 2: "measurement.value"},
    )
    cleared = apply_bulk(spec, ct_block, catalogue(), [1, 2], BULK_IGNORE)
    assert cleared.for_column(1).field is None
    assert cleared.for_column(2).field is None
    assert cleared.for_column(0).field == "sample.sample_datetime_start"


def test_bulk_value_one_group_each(ct_block):
    spec = apply_bulk(empty_spec(ct_block), ct_block, catalogue(), [1, 2, 3], BULK_VALUE_EACH)
    for col in (1, 2, 3):
        m = spec.for_column(col)
        assert m.field == "measurement.value"
        assert m.group == col  # one measurement per value column
    assert groups_of(spec, catalogue()) == (1, 2, 3)


def test_bulk_value_same_group_is_shared_and_deterministic(ct_block):
    spec = apply_bulk(empty_spec(ct_block), ct_block, catalogue(), [2, 3, 4], BULK_VALUE_SAME)
    assert {spec.for_column(c).group for c in (2, 3, 4)} == {2}  # smallest column
    reapplied = apply_bulk(spec, ct_block, catalogue(), [2, 3, 4], BULK_VALUE_SAME)
    assert reapplied == spec  # re-applying the same selection is a no-op


def test_bulk_value_same_group_grows_the_existing_group(ct_block):
    spec = build_spec(ct_block, catalogue(), {2: "measurement.value"}, groups={2: 9})
    spec = apply_bulk(spec, ct_block, catalogue(), [1, 2, 3], BULK_VALUE_SAME)
    assert {spec.for_column(c).group for c in (1, 2, 3)} == {9}


def test_bulk_set_field_to_x(ct_block):
    spec = apply_bulk(
        empty_spec(ct_block), ct_block, catalogue(), [0], BULK_SET_FIELD,
        field="sample.sample_datetime_start",
    )
    assert spec.for_column(0).field == "sample.sample_datetime_start"
    assert spec.for_column(0).group is None  # row scope carries no group


def test_bulk_set_field_keeps_a_measurement_columns_group(ct_block):
    spec = build_spec(ct_block, catalogue(), {1: "measurement.value"}, groups={1: 7})
    spec = apply_bulk(
        spec, ct_block, catalogue(), [1], BULK_SET_FIELD,
        field="measurement.quality_code_id",
    )
    assert spec.for_column(1).field == "measurement.quality_code_id"
    assert spec.for_column(1).group == 7


def test_bulk_apply_is_index_based_and_leaves_the_rest_untouched(ct_block):
    """All four columns are named ``Ct`` — only the selected indices change."""
    spec = build_spec(ct_block, catalogue(), {1: "measurement.value"})
    spec = with_constant(spec, "sample.sample_kind_id", "Field")
    spec = apply_bulk(spec, ct_block, catalogue(), [3, 4], BULK_VALUE_EACH)
    assert spec.for_column(1).field == "measurement.value"
    assert spec.for_column(2).field is None
    assert spec.for_column(3).field == "measurement.value"
    assert spec.for_column(4).field == "measurement.value"
    # constants ride through a bulk apply untouched
    assert constant_for(spec, "sample.sample_kind_id") == "Field"


# --- constants apply at their inferred scope -----------------------------------


def test_file_scope_constant_applies_to_every_row(ct_block):
    spec = with_constant(empty_spec(ct_block), "batch.name", "Spring 2022 campaign")
    values = row_series(spec, ct_block, catalogue(), "batch.name")
    assert len(values) == len(ct_block.data)
    assert (values == "Spring 2022 campaign").all()


def test_row_scope_constant_applies_to_every_row(ct_block):
    spec = with_constant(empty_spec(ct_block), "sample.sample_kind_id", "Field")
    values = row_series(spec, ct_block, catalogue(), "sample.sample_kind_id")
    assert len(values) == len(ct_block.data)
    assert (values == "Field").all()


def test_column_source_yields_the_columns_values(ct_block):
    spec = build_spec(ct_block, catalogue(), {0: "sample.sample_datetime_start"})
    values = row_series(spec, ct_block, catalogue(), "sample.sample_datetime_start")
    assert list(values) == list(ct_block.data[0])


def test_measurement_scope_constant_applies_to_every_group_every_row(ct_block):
    spec = build_spec(ct_block, catalogue(), {1: "measurement.value", 2: "measurement.value"})
    spec = with_constant(spec, "measurement.unit_id", "mg/L")
    for group in (1, 2):
        values = group_series(spec, ct_block, catalogue(), "measurement.unit_id", group)
        assert len(values) == len(ct_block.data)
        assert (values == "mg/L").all()


def test_a_group_constant_overrides_the_scope_wide_one(ct_block):
    spec = build_spec(ct_block, catalogue(), {1: "measurement.value", 2: "measurement.value"})
    spec = with_constant(spec, "measurement.unit_id", "mg/L")
    spec = with_group_constant(spec, 1, "measurement.unit_id", "NTU")
    assert (group_series(spec, ct_block, catalogue(), "measurement.unit_id", 1) == "NTU").all()
    assert (group_series(spec, ct_block, catalogue(), "measurement.unit_id", 2) == "mg/L").all()


def test_unsourced_fields_resolve_to_nothing(ct_block):
    spec = empty_spec(ct_block)
    assert row_series(spec, ct_block, catalogue(), "batch.name") is None
    assert group_series(spec, ct_block, catalogue(), "measurement.unit_id", 1) is None


def test_constants_satisfy_missing_required(ct_block):
    spec = empty_spec(ct_block)
    spec = with_constant(spec, "batch.name", "Spring 2022 campaign")
    spec = with_constant(spec, "batch.experiment_datetime", datetime(2022, 4, 1, 9))
    spec = with_constant(spec, "sample.sampling_point_id", "Site 1")
    missing = {f.key for f in missing_required(spec, catalogue())}
    assert "batch.name" not in missing
    assert "batch.experiment_datetime" not in missing
    assert "sample.sampling_point_id" not in missing
    # the measurement's location inherits the sample's
    assert "measurement.sampling_point_id" not in missing


# --- per-group identity ----------------------------------------------------------


def test_group_identity_is_settable_independently_per_group(ct_block):
    spec = build_spec(ct_block, catalogue(), {1: "measurement.value", 2: "measurement.value"})
    spec = with_constant(spec, "measurement.parameter_id", "SARS-CoV-2")
    spec = with_group_constant(spec, 1, "measurement.unit_id", "Ct")
    spec = with_group_constant(spec, 2, "measurement.unit_id", "gc/rxn")
    spec = with_group_constant(spec, 2, "measurement.laboratory_id", "McGill")
    one = identity_for_group(spec, catalogue(), 1)
    two = identity_for_group(spec, catalogue(), 2)
    assert one["measurement.parameter_id"] == ("constant", "SARS-CoV-2")
    assert two["measurement.parameter_id"] == ("constant", "SARS-CoV-2")
    assert one["measurement.unit_id"] == ("group_constant", "Ct")
    assert two["measurement.unit_id"] == ("group_constant", "gc/rxn")
    assert one["measurement.laboratory_id"] is None
    assert two["measurement.laboratory_id"] == ("group_constant", "McGill")


def test_two_groups_differing_only_by_laboratory(tss_block):
    """The model's decisive case: one parameter, two laboratories, one row."""
    spec = build_spec(tss_block, catalogue(), {1: "measurement.value", 2: "measurement.value"})
    spec = with_constant(spec, "measurement.parameter_id", "TSS")
    spec = with_constant(spec, "measurement.unit_id", "mg/L")
    spec = with_constant(spec, "sample.sampling_point_id", "Site 1")
    spec = with_group_constant(spec, 1, "measurement.laboratory_id", "Ville de Québec")
    spec = with_group_constant(spec, 2, "measurement.laboratory_id", "Université Laval")
    assert validate(spec, tss_block, catalogue()) == []
    one = identity_for_group(spec, catalogue(), 1)
    two = identity_for_group(spec, catalogue(), 2)
    differing = {k for k in one if one[k] != two[k]}
    assert differing == {"measurement.laboratory_id"}
    assert one["measurement.laboratory_id"] == ("group_constant", "Ville de Québec")
    assert two["measurement.laboratory_id"] == ("group_constant", "Université Laval")
    # required measurement fields are covered for both groups
    missing = {f.key for f in missing_required(spec, catalogue())}
    assert "measurement.parameter_id" not in missing
    assert "measurement.unit_id" not in missing
    assert "measurement.sampling_point_id" not in missing


@needs_fixture
def test_tss_two_laboratories_on_the_real_fixture(wq_block):
    """``TSS (VdQ data)`` and ``TSS (ULaval data)`` side by side in one sheet."""
    headers = dict(zip(wq_block.columns, wq_block.headers))
    assert headers[5] == "TSS (mg/L) (VdQ data)"
    assert headers[6] == "TSS (mg/L) (ULaval data)"
    spec = build_spec(wq_block, catalogue(), {5: "measurement.value", 6: "measurement.value"})
    spec = with_constant(spec, "measurement.parameter_id", "TSS")
    spec = with_constant(spec, "measurement.unit_id", "mg/L")
    spec = with_constant(spec, "sample.sampling_point_id", "Fin du Réseau - Intercepteur Est (Site 1)")
    spec = with_group_constant(spec, 5, "measurement.laboratory_id", "Ville de Québec")
    spec = with_group_constant(spec, 6, "measurement.laboratory_id", "Université Laval")
    assert validate(spec, wq_block, catalogue()) == []
    one = identity_for_group(spec, catalogue(), 5)
    two = identity_for_group(spec, catalogue(), 6)
    assert {k for k in one if one[k] != two[k]} == {"measurement.laboratory_id"}
    # the value columns really carry data row by row
    assert group_series(spec, wq_block, catalogue(), "measurement.value", 5).notna().sum() > 300
    assert group_series(spec, wq_block, catalogue(), "measurement.value", 6).notna().sum() > 300


# --- the editor frame carries groups and preserves constants ---------------------


def test_group_column_round_trips_through_the_editor_frame(ct_block):
    spec = build_spec(
        ct_block,
        catalogue(),
        {1: "measurement.value", 2: "measurement.value"},
        groups={1: 7, 2: 7},
    )
    frame = mapping_frame(ct_block, catalogue(), spec)
    assert frame.loc[1, "Group"] == 7
    assert frame.loc[2, "Group"] == 7
    assert pd.isna(frame.loc[0, "Group"])  # ignored columns show no group
    back = spec_from_frame(ct_block, catalogue(), frame, previous=spec)
    assert back.for_column(1).group == 7
    assert back.for_column(2).group == 7
    # editing the frame moves a column to another group
    frame.loc[2, "Group"] = 8
    moved = spec_from_frame(ct_block, catalogue(), frame, previous=spec)
    assert moved.for_column(2).group == 8
    assert moved.for_column(1).group == 7


def test_spec_from_frame_preserves_constants_and_group_constants(ct_block):
    spec = empty_spec(ct_block)
    spec = with_constant(spec, "sample.sample_kind_id", "Field")
    spec = with_group_constant(spec, 1, "measurement.laboratory_id", "McGill")
    frame = mapping_frame(ct_block, catalogue(), spec)
    back = spec_from_frame(ct_block, catalogue(), frame, previous=spec)
    assert constant_for(back, "sample.sample_kind_id") == "Field"
    assert ("group_constant", "McGill") == source_for(
        back, catalogue(), 1, "measurement.laboratory_id"
    )


# --- validation and live completeness ---------------------------------------------


def test_validate_flags_a_constant_and_column_for_one_row_field(ct_block):
    spec = build_spec(ct_block, catalogue(), {0: "sample.sample_datetime_start"})
    spec = with_constant(spec, "sample.sample_datetime_start", datetime(2022, 3, 21, 22))
    (error,) = validate(spec, ct_block, catalogue())
    assert "one source" in error.message
    assert set(error.columns) == {0}


def test_validate_flags_a_group_constant_on_a_non_measurement_field(ct_block):
    spec = with_group_constant(empty_spec(ct_block), 1, "sample.sample_kind_id", "Field")
    (error,) = validate(spec, ct_block, catalogue())
    assert "row-scoped" in error.message


def test_validate_flags_a_group_constant_clashing_with_a_column(ct_block):
    spec = build_spec(ct_block, catalogue(), {1: "measurement.laboratory_id"})
    spec = with_group_constant(spec, 1, "measurement.laboratory_id", "McGill")
    (error,) = validate(spec, ct_block, catalogue())
    assert "one source" in error.message
    assert set(error.columns) == {1}


def test_validate_flags_a_constant_on_a_field_the_import_rejects(ct_block):
    spec = with_constant(empty_spec(ct_block), "sample.no_such_field", 1)
    (error,) = validate(spec, ct_block, catalogue())
    assert "no_such_field" in error.message


def test_validate_flags_duplicate_constants(ct_block):
    spec = MappingSpec(
        tuple(),
        constants=(
            ConstantMapping("batch.name", "one"),
            ConstantMapping("batch.name", "two"),
        ),
    )
    (error,) = validate(spec, ct_block, catalogue())
    assert "two constants" in error.message


def test_missing_required_covers_every_group_and_names_the_gap(ct_block):
    spec = build_spec(ct_block, catalogue(), {1: "measurement.value", 2: "measurement.value"})
    spec = with_constant(spec, "measurement.parameter_id", "SARS-CoV-2")
    spec = with_group_constant(spec, 1, "measurement.unit_id", "Ct")
    missing = {f.key for f in missing_required(spec, catalogue())}
    # unit is covered for group 1 only — the field is still missing
    assert "measurement.unit_id" in missing
    assert groups_lacking(spec, catalogue(), "measurement.unit_id") == (2,)
    # parameter is covered scope-wide — no group is left out
    assert "measurement.parameter_id" not in missing
    assert groups_lacking(spec, catalogue(), "measurement.parameter_id") == ()


# --- the page ---------------------------------------------------------------------

_SHEET = "Synthetic"


def _page_grid() -> pd.DataFrame:
    return pd.DataFrame(
        [
            ["SAMPLING DATA", "PCR", "PCR"],
            [None, "SARS-CoV-2 (N1)", "PMMV"],
            ["date\nstart", "Ct", "Ct"],
            ["when it started", "cycles", "cycles"],
            [datetime(2022, 3, 21, 22), 1.0, 2.0],
            [datetime(2022, 3, 22, 22), 3.0, 4.0],
        ]
    )


def _synthetic_sheet_script():  # pragma: no cover - executed inside AppTest
    from app.pages import sheet_import
    from tests.unit.test_prd7_s5_bulk_constants_groups import _page_grid

    sheet_import._sheet_ui("Synthetic", _page_grid())


def _run_synthetic_sheet():
    at = AppTest.from_function(_synthetic_sheet_script, default_timeout=60)
    at.session_state[f"sheet_header_row::{_SHEET}"] = 2
    at.session_state[f"sheet_data_row::{_SHEET}"] = 4
    at.run()
    return at


def _by_key(at, kind: str, key: str):
    """The one widget of ``kind`` carrying ``key`` (AppTest has no key lookup)."""
    return next(el for el in getattr(at, kind) if el.key == key)


def test_bulk_bar_renders_and_guides_when_nothing_is_selected():
    at = _run_synthetic_sheet()
    assert not at.exception
    captions = " ".join(el.value for el in at.caption)
    assert "Select columns in the raw sheet above" in captions
    action = _by_key(at, "selectbox", f"sheet_bulk_action::{_SHEET}")
    assert set(action.options) == {
        "Ignore all",
        "All Value — one group each",
        "All Value — same group",
        "Set field to…",
    }


def test_constants_editor_sets_a_constant_on_the_spec():
    at = _run_synthetic_sheet()
    assert not at.exception
    _by_key(at, "selectbox", f"sheet_const_field::{_SHEET}").set_value(
        "The sample · Sample kind"
    )
    at.run()
    _by_key(at, "text_input", f"sheet_const_value::{_SHEET}::sample.sample_kind_id").set_value(
        "Field"
    )
    at.run()
    _by_key(at, "button", f"sheet_const_add::{_SHEET}").click()
    at.run()
    assert not at.exception
    spec = at.session_state[f"sheet_mapping::{_SHEET}"]
    assert constant_for(spec, "sample.sample_kind_id") == "Field"
    # the seeded field replicate is still there, untouched
    assert constant_for(spec, "sample.replicate") == 1


def test_groups_panel_renders_each_groups_identity_and_accepts_input():
    block = extract_block(_page_grid(), 2, 4)
    spec = build_spec(block, catalogue(), {1: "measurement.value", 2: "measurement.value"})
    at = _run_synthetic_sheet()
    at.session_state[f"sheet_mapping::{_SHEET}"] = spec
    at.run()
    assert not at.exception
    text = " ".join(str(getattr(el, "value", "")) for el in at.markdown)
    assert "Group 1" in text and "Group 2" in text
    # typing a laboratory for group 1 lands on that group only
    _by_key(at, "text_input", f"sheet_gconst::{_SHEET}::1::measurement.laboratory_id").set_value(
        "McGill"
    )
    at.run()
    assert not at.exception
    spec = at.session_state[f"sheet_mapping::{_SHEET}"]
    assert source_for(spec, catalogue(), 1, "measurement.laboratory_id") == (
        "group_constant",
        "McGill",
    )
    assert source_for(spec, catalogue(), 2, "measurement.laboratory_id") is None


def test_missing_required_fields_are_listed_live_in_plain_language():
    block = extract_block(_page_grid(), 2, 4)
    spec = build_spec(
        block,
        catalogue(),
        {0: "sample.sample_datetime_start", 1: "measurement.value"},
    )
    at = _run_synthetic_sheet()
    at.session_state[f"sheet_mapping::{_SHEET}"] = spec
    at.run()
    assert not at.exception
    captions = " ".join(el.value for el in at.caption)
    assert "Still needed before this can import:" in captions
    assert "Parameter" in captions and "Unit" in captions
    assert "Sampling location" in captions  # plain language, not sampling_point_id
    # completing the spec flips the indicator
    for key, value in {
        "batch.name": "Spring 2022 campaign",
        "batch.experiment_datetime": datetime(2022, 4, 1, 9),
        "sample.sampling_point_id": "Site 1",
        "measurement.parameter_id": "SARS-CoV-2 (N1)",
        "measurement.unit_id": "Ct",
    }.items():
        spec = with_constant(spec, key, value)
    at.session_state[f"sheet_mapping::{_SHEET}"] = spec
    at.run()
    assert not at.exception
    captions = " ".join(el.value for el in at.caption)
    assert "Every required field has a source." in captions
