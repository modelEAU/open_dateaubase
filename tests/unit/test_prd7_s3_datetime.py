"""PRD-7 S3 — explicit timezone and date format, with evidence and dual preview.

The page tests run on tiny synthetic grids, so they need no fixture workbook.
"""

from __future__ import annotations

import zoneinfo
from datetime import datetime

import pandas as pd
from streamlit.testing.v1 import AppTest

from app.components.datetime_parse import (
    FORMAT_PRESETS,
    detect_format,
    parse_values,
    to_utc,
)

TORONTO = zoneinfo.ZoneInfo("America/Toronto")

DAY_FIRST = "03/04/2026 14:30 — day first"


def _series(values, start=10) -> pd.Series:
    return pd.Series(values, index=range(start, start + len(values)), dtype=object)


# --- format detection --------------------------------------------------------


def test_day_first_is_detected_and_parses_to_the_day_the_user_meant():
    values = _series(["13/04/2026", "03/04/2026", "27/04/2026"])
    detection = detect_format(values)
    assert detection.format == "%d/%m/%Y"
    parsed = parse_values(values, detection.format)
    # 03/04/2026 is 3 April to the francophone user, never 4 March
    assert parsed.wall_clock.loc[11] == pd.Timestamp(2026, 4, 3)
    assert not parsed.failures


def test_month_first_is_detected():
    detection = detect_format(_series(["04/13/2026", "04/02/2026"]))
    assert detection.format == "%m/%d/%Y"


def test_iso_is_detected():
    detection = detect_format(_series(["2026-04-03 14:30", "2026-04-04 9:15"]))
    assert detection.format == "%Y-%m-%d %H:%M"


def test_detection_reports_the_evidence_it_used():
    detection = detect_format(_series(["13/04/2026", "03/04/2026"]))
    blob = " ".join(detection.evidence)
    assert "13/04/2026" in blob
    assert "13" in blob and "12" in blob  # a month cannot exceed 12
    assert "day-first" in blob


def test_a_genuinely_ambiguous_sample_is_refused_not_guessed():
    detection = detect_format(_series(["03/04/2026", "05/06/2026", "11/12/2026"]))
    assert detection.format is None
    assert "%d/%m/%Y" in [FORMAT_PRESETS[c] for c in detection.contenders]
    assert "%m/%d/%Y" in [FORMAT_PRESETS[c] for c in detection.contenders]
    blob = " ".join(detection.evidence)
    assert "03/04/2026" in blob
    assert "3 April" in blob and "4 March" in blob  # both readings shown


def test_identical_day_and_month_is_still_ambiguous():
    detection = detect_format(_series(["04/04/2026", "06/06/2026"]))
    assert detection.format is None


def test_no_preset_fitting_is_refused_too():
    detection = detect_format(_series(["03.04.2026", "05.06.2026"]))
    assert detection.format is None
    assert detection.contenders == ()


# --- parsing -----------------------------------------------------------------


def test_unparseable_values_are_listed_with_their_row_never_dropped():
    values = _series(["2026-04-03", "not a date", "2026-04-05"], start=41)
    parsed = parse_values(values, "%Y-%m-%d")
    assert parsed.failures == ((42, "not a date"),)
    assert list(parsed.wall_clock.index) == [41, 42, 43]  # nothing dropped
    assert pd.isna(parsed.wall_clock.loc[42])
    assert parsed.wall_clock.loc[43] == pd.Timestamp(2026, 4, 5)


def test_empty_cells_are_missing_not_failures():
    parsed = parse_values(_series(["2026-04-03", None, "  "]), "%Y-%m-%d")
    assert parsed.failures == ()
    assert pd.isna(parsed.wall_clock.loc[11])


def test_native_datetimes_need_no_format():
    values = _series([datetime(2026, 4, 3, 12, 30), datetime(2026, 4, 5, 9, 15)])
    parsed = parse_values(values, None)
    assert parsed.wall_clock.loc[10] == pd.Timestamp(2026, 4, 3, 12, 30)
    assert not parsed.failures


def test_every_preset_reads_the_example_in_its_own_label():
    for label, fmt in FORMAT_PRESETS.items():
        example = label.split(" — ")[0]
        parsed = parse_values(_series([example]), fmt)
        assert not parsed.failures, f"{label!r} does not parse with {fmt!r}"


# --- timezone conversion -----------------------------------------------------


def test_wall_clock_converts_to_the_correct_utc_instant_across_dst():
    # America/Toronto: EST (UTC-5) before 2026-03-08, EDT (UTC-4) after
    wall = _series([pd.Timestamp(2026, 3, 1, 12, 0), pd.Timestamp(2026, 4, 1, 12, 0)])
    utc = to_utc(wall, TORONTO)
    assert utc.loc[10] == pd.Timestamp("2026-03-01 17:00", tz="UTC")
    assert utc.loc[11] == pd.Timestamp("2026-04-01 16:00", tz="UTC")


def test_unparsed_values_stay_missing_through_utc_conversion():
    parsed = parse_values(_series(["junk", "2026-04-03"]), "%Y-%m-%d")
    utc = to_utc(parsed.wall_clock, TORONTO)
    assert pd.isna(utc.loc[10])
    assert utc.loc[11] == pd.Timestamp("2026-04-03 04:00", tz="UTC")


# --- the page -----------------------------------------------------------------


def _sheet_script():  # pragma: no cover - executed inside AppTest
    import os
    from datetime import datetime

    import pandas as pd

    from app.pages import sheet_import

    kind = os.environ["SHEET_IMPORT_TEST_KIND"]
    if kind == "native":
        rows = [[datetime(2026, 4, 3, 12, 30), 1.0], [datetime(2026, 4, 5, 9, 15), 2.0]]
    elif kind == "day-first":
        rows = [["13/04/2026 12:30", 1.0], ["03/04/2026 12:30", 2.0]]
    else:  # ambiguous
        rows = [["03/04/2026 12:30", 1.0], ["05/06/2026 09:15", 2.0]]
    grid = pd.DataFrame([["date", "value"], *rows])
    sheet_import._sheet_ui("S", grid)


def _run_sheet(monkeypatch, kind: str) -> AppTest:
    monkeypatch.setenv("SHEET_IMPORT_TEST_KIND", kind)
    at = AppTest.from_function(_sheet_script, default_timeout=60)
    at.session_state["sheet_header_row::S"] = 0
    at.session_state["sheet_data_row::S"] = 1
    at.run()
    assert not at.exception
    return at


def _preview(at: AppTest) -> pd.DataFrame | None:
    for element in at.dataframe:
        if "UTC" in getattr(element.value, "columns", []):
            return element.value
    return None


def test_page_refuses_to_guess_then_parses_once_the_user_chooses(monkeypatch):
    at = _run_sheet(monkeypatch, "ambiguous")
    assert any("cannot be told" in w.value for w in at.warning)
    assert _preview(at) is None  # nothing parsed before the user chooses

    at.selectbox(key="sheet_dt_fmt::S::0").set_value(DAY_FIRST)
    at.selectbox(key="sheet_tz::S").set_value("America/Toronto")
    at.run()
    assert not at.exception
    preview = _preview(at)
    assert preview is not None
    row = preview.set_index("value").loc["03/04/2026 12:30"]
    assert row["local (America/Toronto)"] == "2026-04-03 12:30"
    assert row["UTC"] == "2026-04-03 16:30"  # EDT is UTC-4


def test_page_detects_day_first_and_shows_the_evidence(monkeypatch):
    at = _run_sheet(monkeypatch, "day-first")
    assert any("Detected format" in s.value for s in at.success)
    blob = " ".join(m.value for m in at.markdown)
    assert "13/04/2026" in blob and "day-first" in blob
    at.selectbox(key="sheet_tz::S").set_value("America/Toronto")
    at.run()
    preview = _preview(at)
    assert preview is not None
    assert preview.set_index("value").loc["03/04/2026 12:30", "UTC"] == "2026-04-03 16:30"


def test_native_column_skips_the_format_picker_and_says_why(monkeypatch):
    at = _run_sheet(monkeypatch, "native")
    assert not [sb for sb in at.selectbox if sb.label == "Date format"]
    assert any("already holds real dates" in i.value for i in at.info)
    at.selectbox(key="sheet_tz::S").set_value("America/Toronto")
    at.run()
    preview = _preview(at)
    assert preview is not None
    assert preview["UTC"].iloc[0] == "2026-04-03 16:30"


def test_page_lists_unparseable_values_with_their_row(monkeypatch):
    at = _run_sheet(monkeypatch, "day-first")
    # make row 2 (the second data row) unparseable in the cleaned table
    at.selectbox(key="sheet_dt_fmt::S::0").set_value("2026-04-03 — year first (ISO)")
    at.run()
    assert any("would not parse" in w.value for w in at.warning)
    failures = next(
        el.value for el in at.dataframe if list(el.value.columns) == ["row", "value"]
    )
    assert set(failures["value"]) == {"13/04/2026 12:30", "03/04/2026 12:30"}
    assert set(failures["row"]) == {1, 2}  # raw-sheet row numbers


# --- the shared timezone selector --------------------------------------------


def test_one_timezone_selector_is_shared_by_sensor_ingest_and_the_sheet_page():
    import app.components.ingest_shapes as shapes
    from app.components import timezone_select
    from app.pages import sheet_import

    assert shapes.timezone_selector is timezone_select.timezone_selector
    assert sheet_import.timezone_selector is timezone_select.timezone_selector
