"""A sensor sheet is describable in the same page as a lab sheet.

Sensor ingest takes one channel and a list of points, so a wide sheet of tag
columns is one request per column. The vocabulary changes with the kind of data;
the way a column is mapped does not.
"""

from __future__ import annotations

import zoneinfo

import pandas as pd

from app.components.column_mapping import build_spec, with_group_constant
from app.components.field_catalogue import catalogue
from app.components.sensor_builder import build_sensor
from app.components.sheet_block import extract_block

MONTREAL = zoneinfo.ZoneInfo("America/Montreal")
FORMATS = {0: "%Y-%m-%d %H:%M"}

POOLS = {
    "Parameter": [
        {"parameter_id": 1, "parameter_name": "Turbidity"},
        {"parameter_id": 2, "parameter_name": "Level"},
    ],
    "Unit": [{"unit_id": 1, "unit": "NTU"}, {"unit_id": 2, "unit": "m"}],
    "DataAcquisitionSystem": [{"data_acquisition_system_id": 1, "name": "SCADA"}],
    "Equipment": [{"equipment_id": 1, "identifier": "Sonde-1"}],
    "SignalInterface": [{"signal_interface_id": 1, "name": "Panel A"}],
}


def _lookup(table: str) -> list[dict]:
    return POOLS.get(table, [])


def _grid() -> pd.DataFrame:
    return pd.DataFrame(
        [
            ["timestamp", "turbidity", "level"],
            ["2026-04-03 14:30", 12.5, 1.2],
            ["2026-04-03 14:40", 13.0, 1.3],
        ]
    )


def _two_tag_spec(overrides: dict | None = None):
    """Two value columns, each its own channel, identified per group."""
    block = extract_block(_grid(), 0, 1)
    cat = catalogue("sensor")
    spec = build_spec(
        block,
        cat,
        {0: "point.timestamp", 1: "point.value", 2: "point.value"},
        {1: 1, 2: 2},
    )
    identity = {
        (1, "channel.das_name"): "SCADA",
        (1, "channel.tag"): "AI-101",
        (1, "channel.parameter_name"): "Turbidity",
        (1, "channel.unit_name"): "NTU",
        (2, "channel.das_name"): "SCADA",
        (2, "channel.tag"): "AI-102",
        (2, "channel.parameter_name"): "Level",
        (2, "channel.unit_name"): "m",
    }
    identity.update(overrides or {})
    for (group, field), value in identity.items():
        if value is not None:
            spec = with_group_constant(spec, group, field, value)
    return spec, block, cat


def _build(spec, block, cat):
    return build_sensor(spec, block, cat, _lookup, MONTREAL, FORMATS)


# --- the catalogue ------------------------------------------------------------


def test_the_two_kinds_speak_their_own_vocabularies():
    lab, sensor = catalogue("lab"), catalogue("sensor")
    assert catalogue() is lab  # the default is unchanged for every existing caller
    assert lab.value_key == "measurement.value"
    assert sensor.value_key == "point.value"
    keys = {f.key for f in sensor.fields}
    assert "channel.tag" in keys and "channel.equipment_name" in keys
    assert not [k for k in keys if k.startswith("measurement.")]


def test_a_name_the_server_resolves_gets_a_picker_and_stays_a_name():
    sensor = catalogue("sensor")
    parameter = sensor.by_key("channel.parameter_name")
    assert parameter.fk_table == "Parameter"
    assert parameter.emits == "name"  # sensor ingest takes the name, not the id


def test_the_mutually_exclusive_identities_are_not_both_required():
    sensor = catalogue("sensor")
    for key in ("channel.tag", "channel.equipment_name", "channel.signal_interface_name"):
        assert not sensor.by_key(key).required


# --- the builder --------------------------------------------------------------


def test_two_tag_columns_become_two_requests():
    result = _build(*_two_tag_spec())
    assert not result.errors
    assert [r.endpoint for r in result.requests] == ["/ingest/sensor"] * 2
    first, second = result.requests
    assert first.payload["tag"] == "AI-101"
    assert first.payload["parameter_name"] == "Turbidity"
    assert [p["value"] for p in first.payload["values"]] == [12.5, 13.0]
    assert [p["value"] for p in second.payload["values"]] == [1.2, 1.3]
    # 14:30 EDT is 18:30 UTC
    assert first.payload["values"][0]["timestamp"] == "2026-04-03T18:30:00+00:00"


def test_a_station_with_no_tag_posts_to_the_tagless_endpoint():
    spec, block, cat = _two_tag_spec(
        {
            (1, "channel.tag"): None,
            (1, "channel.equipment_name"): "Sonde-1",
            (1, "channel.signal_interface_name"): "Panel A",
        }
    )
    result = _build(spec, block, cat)
    assert not result.errors
    endpoints = {r.group: r.endpoint for r in result.requests}
    assert endpoints == {1: "/ingest/sensor-tagless", 2: "/ingest/sensor"}
    tagless = next(r for r in result.requests if r.group == 1)
    assert tagless.payload["equipment_name"] == "Sonde-1"
    assert "tag" not in tagless.payload


def test_half_a_tagless_identity_names_what_is_missing():
    spec, block, cat = _two_tag_spec(
        {(1, "channel.tag"): None, (1, "channel.equipment_name"): "Sonde-1"}
    )
    result = _build(spec, block, cat)
    assert len(result.errors) == 1
    assert "Signal interface" in result.errors[0].message
    assert "Group 1" in result.errors[0].message


def test_a_tag_and_a_station_identity_at_once_is_refused():
    spec, block, cat = _two_tag_spec(
        {
            (1, "channel.equipment_name"): "Sonde-1",
            (1, "channel.signal_interface_name"): "Panel A",
        }
    )
    result = _build(spec, block, cat)
    assert result.errors
    assert "SCADA tag" in result.errors[0].message


def test_a_parameter_the_server_will_not_create_is_an_error():
    spec, block, cat = _two_tag_spec({(1, "channel.parameter_name"): "Chlorophyll"})
    result = _build(spec, block, cat)
    assert any("Chlorophyll" in e.message for e in result.errors)


def test_a_system_the_server_will_create_is_only_a_warning():
    spec, block, cat = _two_tag_spec({(1, "channel.das_name"): "New SCADA"})
    result = _build(spec, block, cat)
    assert not result.errors
    assert any("New SCADA" in w for w in result.warnings)
    assert any("will be created" in w for w in result.warnings)


def test_a_bound_name_is_sent_as_the_name_the_server_knows():
    from app.components.column_mapping import with_binding

    spec, block, cat = _two_tag_spec({(1, "channel.parameter_name"): "Turb."})
    spec = with_binding(spec, "channel.parameter_name", "Turb.", 1)
    result = _build(spec, block, cat)
    assert not result.errors
    first = next(r for r in result.requests if r.group == 1)
    assert first.payload["parameter_name"] == "Turbidity"


def test_an_unknown_channel_kind_is_refused_before_the_post():
    spec, block, cat = _two_tag_spec({(1, "channel.channel_kind"): "guesswork"})
    result = _build(spec, block, cat)
    assert any("guesswork" in e.message for e in result.errors)


def test_an_identity_that_varies_inside_one_group_cannot_be_one_channel():
    """Two tags in one group is two channels, which one request cannot say."""
    block = extract_block(_grid(), 0, 1)
    cat = catalogue("sensor")
    spec = build_spec(
        block,
        cat,
        {0: "point.timestamp", 1: "point.value", 2: "channel.tag"},
        {1: 1, 2: 1},
    )
    for field, value in (
        ("channel.das_name", "SCADA"),
        ("channel.parameter_name", "Turbidity"),
        ("channel.unit_name", "NTU"),
    ):
        spec = with_group_constant(spec, 1, field, value)
    result = build_sensor(spec, block, cat, _lookup, MONTREAL, FORMATS)
    assert any("varies" in e.message for e in result.errors)


# --- the page ------------------------------------------------------------------


def _page_script():  # pragma: no cover - executed inside AppTest
    from app.pages import sheet_import

    from tests.unit.test_sensor_catalogue_builder import _grid

    sheet_import._sheet_ui("K", _grid())


def _run_page(kind: str):
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_function(_page_script, default_timeout=60)
    at.session_state["sheet_header_row::K"] = 0
    at.session_state["sheet_data_row::K"] = 1
    at.session_state["sheet_kind::K"] = kind
    at.run()
    assert not at.exception
    return at


def _options(at):
    """The vocabulary the page offers, off the constants editor's field picker."""
    return next(sb for sb in at.selectbox if sb.key == "sheet_const_field::K").options


def test_the_kind_chosen_decides_which_words_the_columns_are_mapped_in():
    lab_options = " ".join(_options(_run_page("lab")))
    sensor_options = " ".join(_options(_run_page("sensor")))
    assert "When & where · Sampling start" in lab_options
    assert "The channel · SCADA tag" in sensor_options
    assert "sample" not in sensor_options.lower()


def test_changing_the_kind_drops_a_mapping_written_in_the_other_vocabulary():
    from app.components.column_mapping import ColumnMapping, MappingSpec

    at = _run_page("lab")
    at.session_state["sheet_mapping::K"] = MappingSpec(
        (ColumnMapping(0, "sample.sample_datetime_start"), ColumnMapping(1), ColumnMapping(2))
    )
    at.radio(key="sheet_kind::K").set_value("sensor")
    at.run()
    assert not at.exception
    assert not at.session_state["sheet_mapping::K"].mapped()


def test_a_row_with_no_reading_is_not_sent_as_a_point():
    grid = _grid()
    grid.iloc[2, 1] = None  # the turbidity sensor reported nothing at 14:40
    block = extract_block(grid, 0, 1)
    cat = catalogue("sensor")
    spec, _, _ = _two_tag_spec()
    result = build_sensor(spec, block, cat, _lookup, MONTREAL, FORMATS)
    turbidity = next(r for r in result.requests if r.group == 1)
    assert len(turbidity.payload["values"]) == 1
