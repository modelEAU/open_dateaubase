"""A column's date format is a property of that column, not of the page.

A sheet routinely carries two date/time columns — when the sample was taken
and when it was analysed — written in two different formats. Both must be
configurable, so both get their own panel beside the column they belong to.
"""

from __future__ import annotations

import pandas as pd
from streamlit.testing.v1 import AppTest

from app.components.column_mapping import ColumnMapping, ConstantMapping, MappingSpec

SAMPLED = "sampled"
ANALYSED = "analysed"

DAY_FIRST = "03/04/2026 — day first"
ISO = "2026-04-03 14:30 — year first (ISO)"


def _two_date_grid() -> pd.DataFrame:
    """Sampling dates written day-first, analysis timestamps written ISO."""
    return pd.DataFrame(
        [
            [SAMPLED, "value", ANALYSED],
            ["13/04/2026", 240.0, "2026-04-03 14:30"],
            ["03/04/2026", 300.0, "2026-04-05 09:15"],
        ]
    )


def _two_dates_script():  # pragma: no cover - executed inside AppTest
    from app.pages import sheet_import

    from tests.unit.test_sheet_column_details import _two_date_grid

    sheet_import._sheet_ui("S", _two_date_grid())


def _spec() -> MappingSpec:
    return MappingSpec(
        (
            ColumnMapping(0, "sample.sample_datetime_start"),
            ColumnMapping(1, "measurement.value", group=1),
            ColumnMapping(2, "measurement.analysis_datetime", group=1),
        ),
        constants=(ConstantMapping("sample.replicate", 1),),
    )


def _run() -> AppTest:
    at = AppTest.from_function(_two_dates_script, default_timeout=60)
    at.session_state["sheet_header_row::S"] = 0
    at.session_state["sheet_data_row::S"] = 1
    at.session_state["sheet_tz::S"] = "America/Toronto"
    at.session_state["sheet_mapping::S"] = _spec()
    at.run()
    assert not at.exception
    return at


def _previews(at: AppTest) -> list[pd.DataFrame]:
    return [
        el.value for el in at.dataframe if "UTC" in getattr(el.value, "columns", [])
    ]


def test_both_mapped_date_columns_get_their_own_format_and_preview():
    at = _run()
    formats = {sb.key: sb.value for sb in at.selectbox if sb.label == "Date format"}
    assert formats == {"sheet_dt_fmt::S::0": DAY_FIRST, "sheet_dt_fmt::S::2": ISO}

    by_value = {
        row["value"]: row for preview in _previews(at) for _, row in preview.iterrows()
    }
    # the same 3 April, read day-first in one column and ISO in the other
    assert by_value["03/04/2026"]["local (America/Toronto)"] == "2026-04-03 00:00"
    assert by_value["2026-04-03 14:30"]["local (America/Toronto)"] == "2026-04-03 14:30"


def test_the_page_has_no_date_time_column_picker_left():
    at = _run()
    assert not [sb for sb in at.selectbox if sb.label == "Date/time column"]


def test_a_column_holding_no_date_gets_no_format_panel():
    at = _run()
    # column 1 is the value column: three mapped columns, two date panels
    assert len([sb for sb in at.selectbox if sb.label == "Date format"]) == 2


def test_an_unmapped_date_column_is_not_configurable_and_says_nothing():
    at = AppTest.from_function(_two_dates_script, default_timeout=60)
    at.session_state["sheet_header_row::S"] = 0
    at.session_state["sheet_data_row::S"] = 1
    at.session_state["sheet_tz::S"] = "America/Toronto"
    at.run()
    assert not at.exception
    assert not [sb for sb in at.selectbox if sb.label == "Date format"]
    assert any("needs a decision" in c.value for c in at.caption)
