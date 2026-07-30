"""A near miss is a different entity, not a typo to guess at.

Fuzzy matching made ``"COD tot"`` mean ``COD`` without saying so, which is the
one failure an import must never have: data written against the wrong entity,
silently. Resolution is now exact (case aside), and a text the database does not
have is either bound to the row the user means or created.
"""

from __future__ import annotations

import datetime as dt
import zoneinfo

import pandas as pd

from app.components.column_mapping import (
    binding_for,
    build_spec,
    mapping_frame,
    spec_from_frame,
    with_binding,
    with_constant,
    without_binding,
)
from app.components.field_catalogue import catalogue
from app.components.measurement_builder import build, suggest
from app.components.sheet_block import extract_block

MONTREAL = zoneinfo.ZoneInfo("America/Montreal")

WHEN = dt.datetime(2026, 4, 3, 12, 0)

PARAMETERS = [
    {"parameter_id": 7, "parameter_name": "TSS"},
    {"parameter_id": 8, "parameter_name": "COD"},
]
LABORATORIES = [{"laboratory_id": 2, "name": "VdQ"}]


def _lookup(table: str) -> list[dict]:
    return {
        "SamplingPoint": [{"sampling_point_id": 1, "label": "Site 1"}],
        "Parameter": PARAMETERS,
        "Unit": [{"unit_id": 3, "unit": "mg/L"}],
        "Laboratory": LABORATORIES,
    }.get(table, [])


def _grid(parameter_text: str) -> pd.DataFrame:
    return pd.DataFrame(
        [
            ["date start", "parameter", "value"],
            [WHEN, parameter_text, 300.0],
        ]
    )


def _spec(parameter_text: str):
    block = extract_block(_grid(parameter_text), 0, 1)
    spec = build_spec(
        block,
        catalogue(),
        {
            0: "sample.sample_datetime_start",
            1: "measurement.parameter_id",
            2: "measurement.value",
        },
        {1: 0, 2: 0},
    )
    spec = with_constant(spec, "measurement.unit_id", "mg/L")
    spec = with_constant(spec, "sample.sampling_point_id", "Site 1")
    spec = with_constant(spec, "batch.name", "Spring 2026")
    spec = with_constant(spec, "batch.experiment_datetime", dt.datetime(2026, 4, 1, 9))
    return spec, block


def _build(spec, block):
    return build(spec, block, catalogue(), _lookup, MONTREAL, {})


def test_a_near_miss_is_refused_and_names_itself():
    result = _build(*_spec("COD tot"))
    assert len(result.errors) == 1
    assert "COD tot" in result.errors[0].message
    assert "Parameter" in result.errors[0].message


def test_a_bound_text_resolves_to_the_entity_the_user_chose():
    spec, block = _spec("COD tot")
    spec = with_binding(spec, "measurement.parameter_id", "COD tot", 8)
    result = _build(spec, block)
    assert not result.errors
    assert [m.parameter_id for r in result.rows for m in r.measurements] == [8]


def test_binding_the_wrong_field_does_not_resolve_the_column():
    spec, block = _spec("COD tot")
    spec = with_binding(spec, "measurement.unit_id", "COD tot", 8)
    assert _build(spec, block).errors


def test_case_alone_never_makes_two_entities():
    spec, block = _spec("cod")
    result = _build(spec, block)
    assert not result.errors
    assert [m.parameter_id for r in result.rows for m in r.measurements] == [8]


def test_a_constant_matches_by_case_too():
    spec, block = _spec("COD")
    spec = with_constant(spec, "measurement.laboratory_id", "vdq")
    result = _build(spec, block)
    assert not result.errors
    assert [m.laboratory_id for r in result.rows for m in r.measurements] == [2]


def test_a_binding_survives_editing_the_mapping_table():
    spec, block = _spec("COD tot")
    spec = with_binding(spec, "measurement.parameter_id", "COD tot", 8)
    cat = catalogue()
    reread = spec_from_frame(block, cat, mapping_frame(block, cat, spec), previous=spec)
    assert binding_for(reread, "measurement.parameter_id", "COD tot") == 8
    assert binding_for(without_binding(reread, "measurement.parameter_id", "COD tot"),
                       "measurement.parameter_id", "COD tot") is None


def test_rebinding_one_text_replaces_the_earlier_choice():
    spec, _ = _spec("COD tot")
    spec = with_binding(spec, "measurement.parameter_id", "COD tot", 8)
    spec = with_binding(spec, "measurement.parameter_id", "COD tot", 7)
    assert len(spec.bindings) == 1
    assert binding_for(spec, "measurement.parameter_id", "COD tot") == 7


def test_the_guess_moves_to_where_it_can_be_seen_and_accepted():
    """A close name is a suggestion for the picker, never a silent resolution."""
    assert suggest(PARAMETERS, "parameter_name", "COD tot") == "COD"
    assert suggest(PARAMETERS, "parameter_name", "chlorophyll") is None


# --- the panel that asks --------------------------------------------------------

SITES = [
    {"sampling_point_id": 1, "label": "Site 1"},
    {"sampling_point_id": 2, "label": "Outfall"},
]


def _site_grid() -> pd.DataFrame:
    return pd.DataFrame(
        [
            ["date start", "site", "value"],
            [WHEN, "Site 1", 240.0],
            [WHEN, "Chute", 300.0],  # a location the database does not hold
        ]
    )


def _site_script():  # pragma: no cover - executed inside AppTest
    from app.pages import sheet_import

    from tests.unit.test_entity_binding import _site_grid

    sheet_import._sheet_ui("E", _site_grid())


def _run_site_sheet(monkeypatch):
    from streamlit.testing.v1 import AppTest

    from app.components.column_mapping import ColumnMapping, MappingSpec
    from app.pages import sheet_import

    monkeypatch.setattr(
        sheet_import, "_api_lookup", lambda table: SITES if table == "SamplingPoint" else []
    )
    at = AppTest.from_function(_site_script, default_timeout=60)
    at.session_state["sheet_header_row::E"] = 0
    at.session_state["sheet_data_row::E"] = 1
    at.session_state["sheet_tz::E"] = "America/Montreal"
    at.session_state["sheet_mapping::E"] = MappingSpec(
        (
            ColumnMapping(0, "sample.sample_datetime_start"),
            ColumnMapping(1, "sample.sampling_point_id"),
            ColumnMapping(2, "measurement.value", group=2),
        )
    )
    at.run()
    assert not at.exception
    return at


def test_the_column_names_the_value_the_database_does_not_hold(monkeypatch):
    at = _run_site_sheet(monkeypatch)
    blob = " ".join(str(m.value) for m in at.markdown)
    assert "'Chute'** is not on record" in blob
    assert "'Site 1'" not in blob  # already on record: nothing to ask
    assert any(sb.key == "sheet_bind::E::1::Chute::pick" for sb in at.selectbox)


def test_picking_an_entity_binds_that_text_on_the_spec(monkeypatch):
    at = _run_site_sheet(monkeypatch)
    at.selectbox(key="sheet_bind::E::1::Chute::pick").set_value("Outfall")
    at.run()
    assert not at.exception
    assert binding_for(at.session_state["sheet_mapping::E"], "sample.sampling_point_id", "Chute") == 2
    blob = " ".join(str(m.value) for m in at.markdown)
    assert "'Chute' → **Outfall**" in blob


def test_an_untouched_optional_field_is_not_sent_at_all():
    """A blank text box is not a value; the server would refuse `""` as an int."""
    import datetime as dt

    from app.components.entity_picker import _payload

    sent = _payload(
        {"name": "Chute du Moulin", "process_unit_id": "", "latitude": 0, "start": dt.date(2026, 4, 3)}
    )
    assert sent == {"name": "Chute du Moulin", "latitude": 0, "start": "2026-04-03"}
