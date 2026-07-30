"""Wall clocks a daylight-saving change broke, and rows that share one sample.

Both are cases a real sheet produces and a synthetic one rarely does: an hour
that does not exist in the file's zone, and a long-format sheet that spends
several rows describing one physical sample.
"""

from __future__ import annotations

import datetime as dt
import zoneinfo

import pandas as pd
import pytest

from app.components.column_mapping import build_spec, with_constant
from app.components.datetime_parse import dst_gaps, parse_values, to_utc
from app.components.field_catalogue import catalogue
from app.components.measurement_builder import build, sample_key
from app.components.sheet_block import extract_block

MONTREAL = zoneinfo.ZoneInfo("America/Montreal")

# 2026: the clocks jump forward 8 March 02:00 -> 03:00, so 02:30 never happens;
# they fall back 1 November 02:00 -> 01:00, so 01:30 happens twice.
SPRING_GAP = "08/03/2026 02:30"
AUTUMN_FOLD = "01/11/2026 01:30"
NORMAL = "08/03/2026 04:00"


def _series(values: list) -> pd.Series:
    return pd.Series(values, index=range(1, len(values) + 1))


# --- the conversion itself --------------------------------------------------


@pytest.mark.parametrize("text", [SPRING_GAP, AUTUMN_FOLD])
def test_a_broken_wall_clock_does_not_raise(text):
    parsed = parse_values(_series([text, NORMAL]), "%d/%m/%Y %H:%M")
    utc = to_utc(parsed.wall_clock, MONTREAL)
    assert pd.isna(utc.iloc[0])
    assert utc.iloc[1] == pd.Timestamp("2026-03-08 08:00", tz="UTC")


def test_broken_wall_clocks_are_named_with_their_rows():
    parsed = parse_values(_series([SPRING_GAP, NORMAL, AUTUMN_FOLD]), "%d/%m/%Y %H:%M")
    gaps = dst_gaps(parsed.wall_clock, to_utc(parsed.wall_clock, MONTREAL))
    assert [row for row, _ in gaps] == [1, 3]


def test_a_zone_without_daylight_saving_converts_the_same_times_fine():
    parsed = parse_values(_series([SPRING_GAP, AUTUMN_FOLD]), "%d/%m/%Y %H:%M")
    utc = to_utc(parsed.wall_clock, zoneinfo.ZoneInfo("UTC"))
    assert not dst_gaps(parsed.wall_clock, utc)


# --- the build refuses rather than dropping them silently -------------------


def _dst_grid() -> pd.DataFrame:
    return pd.DataFrame(
        [
            ["date start", "value"],
            [SPRING_GAP, 240.0],
            [NORMAL, 300.0],
        ]
    )


def _lookup(table: str) -> list[dict]:
    return {
        "SamplingPoint": [{"sampling_point_id": 1, "label": "Site 1"}],
        "Parameter": [{"parameter_id": 7, "parameter_name": "TSS"}],
        "Unit": [{"unit_id": 3, "unit": "mg/L"}],
    }.get(table, [])


def _spec(block, mapping, groups=None):
    spec = build_spec(block, catalogue(), mapping, groups)
    spec = with_constant(spec, "measurement.parameter_id", "TSS")
    spec = with_constant(spec, "measurement.unit_id", "mg/L")
    spec = with_constant(spec, "sample.sampling_point_id", "Site 1")
    spec = with_constant(spec, "batch.name", "Spring 2026 campaign")
    spec = with_constant(spec, "batch.experiment_datetime", dt.datetime(2026, 4, 1, 9))
    return spec


def test_the_build_names_the_broken_times_instead_of_dropping_their_rows():
    block = extract_block(_dst_grid(), 0, 1)
    spec = _spec(block, {0: "sample.sample_datetime_start", 1: "measurement.value"}, {1: 0})
    result = build(spec, block, catalogue(), _lookup, MONTREAL, {0: "%d/%m/%Y %H:%M"})
    assert not result.rows
    assert len(result.errors) == 1
    message = result.errors[0].message
    assert "America/Montreal" in message and "2026-03-08 02:30" in message
    assert "row 1" in message


def _dst_page_script():  # pragma: no cover - executed inside AppTest
    from app.pages import sheet_import

    from tests.unit.test_sheet_import_dst_and_identity import _dst_grid

    sheet_import._sheet_ui("DST", _dst_grid())


def test_the_page_survives_a_broken_wall_clock_and_says_so():
    """A wall clock the zone does not have must warn, not raise, in the preview."""
    from streamlit.testing.v1 import AppTest

    from app.components.column_mapping import ColumnMapping, MappingSpec

    at = AppTest.from_function(_dst_page_script, default_timeout=60)
    at.session_state["sheet_header_row::DST"] = 0
    at.session_state["sheet_data_row::DST"] = 1
    at.session_state["sheet_tz::DST"] = "America/Montreal"
    at.session_state["sheet_dt_fmt::DST::0"] = "03/04/2026 14:30 — day first"
    at.session_state["sheet_mapping::DST"] = MappingSpec(
        (
            ColumnMapping(0, "sample.sample_datetime_start"),
            ColumnMapping(1, "measurement.value", group=1),
        )
    )
    at.run()
    assert not at.exception
    warnings = " ".join(el.value for el in at.warning)
    assert "do not exist, or happen twice, in America/Montreal" in warnings


# --- several source rows, one physical sample -------------------------------


def _long_grid() -> pd.DataFrame:
    when = dt.datetime(2026, 7, 15, 14, 30)
    return pd.DataFrame(
        [
            ["date start", "parameter", "value"],
            [when, "TSS", 240.0],
            [when, "COD", 300.0],  # same sample, a second parameter
        ]
    )


def _long_result():
    block = extract_block(_long_grid(), 0, 1)
    spec = _spec(
        block,
        {
            0: "sample.sample_datetime_start",
            1: "measurement.parameter_id",
            2: "measurement.value",
        },
        {1: 0, 2: 0},
    )
    lookup = lambda t: (  # noqa: E731
        [{"parameter_id": 7, "parameter_name": "TSS"}, {"parameter_id": 8, "parameter_name": "COD"}]
        if t == "Parameter"
        else _lookup(t)
    )
    return build(spec, block, catalogue(), lookup, MONTREAL, {})


def test_rows_describing_one_sample_are_counted_once():
    result = _long_result()
    assert not result.errors and not result.collisions
    assert len(result.rows) == 2  # two source rows
    assert result.counts()["samples"] == 1  # one physical sample
    assert result.counts()["measurements"] == 2
    assert len({sample_key(r.sample) for r in result.rows}) == 1


def test_a_second_replicate_is_a_second_sample():
    result = _long_result()
    a, b = (dict(r.sample) for r in result.rows)
    b["replicate"] = 2
    assert sample_key(a) != sample_key(b)
