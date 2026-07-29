"""PRD-7 S2 — spreadsheet-first import: raw grid, pointed rows, cleaned block.

Run against the real acceptance workbook: a header three rows above the data
with help text, type annotations and blank rows in between, 96 columns, header
names repeated four times, and banner rows above the header.

The workbook holds real data and stays out of git, so the tests that need it
skip when it is absent.
"""

from __future__ import annotations

import io
from datetime import datetime
from pathlib import Path

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

from app.components.sheet_block import extract_block, read_grids

REPO = Path(__file__).resolve().parents[2]
FIXTURE = REPO / "data" / "sample_data" / "CentrEau-COVID_Resultats_Quebec_2022.xlsx"
SHEET = "QC Data Daily Samples (McGill)"
HEADER_ROW = 2
DATA_ROW = 8

needs_fixture = pytest.mark.skipif(
    not FIXTURE.exists(), reason=f"acceptance workbook not present at {FIXTURE}"
)


@pytest.fixture(scope="module")
def grid() -> pd.DataFrame:
    if not FIXTURE.exists():
        pytest.skip(f"acceptance workbook not present at {FIXTURE}")
    return pd.read_excel(FIXTURE, sheet_name=SHEET, header=None)


@pytest.fixture(scope="module")
def block(grid):
    return extract_block(grid, HEADER_ROW, DATA_ROW)


# --- block extraction, synthetic (always runs) ------------------------------


def _synthetic_grid() -> pd.DataFrame:
    """A miniature of the acceptance workbook's awkward shape."""
    return pd.DataFrame(
        [
            ["SAMPLING DATA", None, "PCR", None],  # banner
            [None, None, "SARS-CoV-2 (N1)", None],  # banner
            ["date\nstart", "Label", "Ct", "Ct"],  # header
            ["when it started", "the id", "cycles", "cycles"],  # help text
            [None, None, None, None],  # blank
            [datetime(2022, 3, 21, 22), "QC_01", 1.0, 2.0],  # data
            [datetime(2022, 3, 22, 22), "QC_02", 3.0, 4.0],
        ]
    )


def test_synthetic_block_skips_help_and_blanks_and_keeps_columns_distinct():
    small = extract_block(_synthetic_grid(), 2, 5)
    assert list(small.data.index) == [5, 6]
    assert small.headers == ("date start", "Label", "Ct", "Ct")
    assert small.banners[1] == ("SAMPLING DATA",)  # forward-filled from column 0
    assert small.banner_path(2) == "PCR › SARS-CoV-2 (N1)"
    assert small.datetime_columns == {0}
    assert len(set(small.labels())) == 4
    assert small.data.loc[5, 2] == 1.0 and small.data.loc[5, 3] == 2.0


# --- block extraction, real acceptance workbook -----------------------------


def test_pointed_rows_yield_the_data_only(block):
    assert len(block.data) == 1697
    assert block.data.index[0] == DATA_ROW
    # the help-text (4), type-annotation (5) and blank (3, 6, 7) rows are gone
    for skipped in (3, 4, 5, 6, 7):
        assert skipped not in block.data.index
    assert block.data.loc[DATA_ROW, 3] == "QC_01_cpFP24h_rawWW"


def test_repeated_headers_stay_addressable_by_index(block):
    assert [i for i, h in enumerate(block.headers) if h == "Ct"] == [38, 47, 55, 67]
    assert [i for i, h in enumerate(block.headers) if h == "Standard Curves"] == [
        42,
        51,
        59,
        71,
    ]
    assert len(set(block.labels())) == len(block.columns)


def test_multiline_header_collapses_to_one_line(block):
    assert block.headers[0] == "dateTimeStart (YYYY-MM-DD HH:MM - 24h)"
    assert all("\n" not in h for h in block.headers)


def test_banner_rows_forward_fill_across_the_columns_they_span(block):
    assert block.banners[38] == ("PCR", "External control (BRSV)")
    assert block.banners[47] == ("PCR", "PMMV")
    assert block.banner_path(55) == "PCR › SARS-CoV-2 (N1)"
    assert block.banners[0] == ("SAMPLING DATA", "Identification")


def test_native_datetime_columns_are_reported(block):
    assert {0, 1, 2, 16, 35, 64} <= block.datetime_columns
    assert 3 not in block.datetime_columns  # Label_ID is text
    assert 8 not in block.datetime_columns  # Sample Size is numeric


def test_column_subset_is_honoured(grid):
    narrow = extract_block(grid, HEADER_ROW, DATA_ROW, columns=[0, 38])
    assert narrow.columns == (0, 38)
    assert list(narrow.data.columns) == [0, 38]


def test_data_must_start_below_the_header():
    with pytest.raises(ValueError):
        extract_block(_synthetic_grid(), 2, 1)


def test_csv_reads_as_a_single_raw_grid():
    grids = read_grids(io.BytesIO(b"a,b\n1,2\n"), "x.csv")
    assert list(grids) == ["CSV"]
    assert grids["CSV"].shape == (2, 2)
    assert grids["CSV"].iloc[0, 0] == "a"


# --- the page ---------------------------------------------------------------


def test_new_page_sits_beside_the_existing_mapper():
    home = (REPO / "app" / "Home.py").read_text()
    assert 'sheet_import.py"), title="Import Data (Sheet)"' in home
    assert 'mapper.py"), title="Import Data (Mapper)"' in home


def test_page_renders_without_an_upload():
    at = AppTest.from_file(str(REPO / "app" / "pages" / "sheet_import.py"), default_timeout=30)
    at.run()
    assert not at.exception
    assert "Import Data (Sheet)" in at.title[0].value


def _fixture_sheet_script():  # pragma: no cover - executed inside AppTest
    import os

    import pandas as pd

    from app.pages import sheet_import

    sheet = os.environ["SHEET_IMPORT_TEST_SHEET"]
    grid = pd.read_excel(os.environ["SHEET_IMPORT_TEST_FIXTURE"], sheet_name=sheet, header=None)
    sheet_import._sheet_ui(sheet, grid)


@needs_fixture
def test_pointed_sheet_renders_an_editable_cleaned_block(monkeypatch):
    monkeypatch.setenv("SHEET_IMPORT_TEST_FIXTURE", str(FIXTURE))
    monkeypatch.setenv("SHEET_IMPORT_TEST_SHEET", SHEET)
    at = AppTest.from_function(_fixture_sheet_script, default_timeout=60)
    at.session_state[f"sheet_header_row::{SHEET}"] = HEADER_ROW
    at.session_state[f"sheet_data_row::{SHEET}"] = DATA_ROW
    at.run()
    assert not at.exception

    captions = " ".join(str(getattr(el, "value", "")) for el in at.get("caption"))
    assert "1697 rows × 96 columns" in captions
    assert "already hold real datetimes" in captions
    stored = at.session_state[f"sheet_block::{SHEET}"]
    assert list(stored.columns)[:3] == [0, 1, 2]
    assert len(stored) == 1697

    # selection is remembered per sheet, and the cleaned block survives a rerun
    at.run()
    assert not at.exception
    assert at.session_state[f"sheet_header_row::{SHEET}"] == HEADER_ROW
    assert len(at.session_state[f"sheet_block::{SHEET}"]) == 1697
