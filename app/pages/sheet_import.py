"""Spreadsheet-first import — see the sheet, point at the header and the data.

Upload a workbook, pick a sheet, click the row holding your column names and
the first row of real data. Everything between is skipped. The cleaned block
renders beside the raw sheet and its cells are editable.
"""

from __future__ import annotations

import io
import sys
from pathlib import Path

_project_root = str(Path(__file__).resolve().parent.parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

import pandas as pd
import streamlit as st

from app.components.sheet_block import extract_block, read_grids


@st.cache_data(show_spinner="Reading the file…")
def _grids(payload: bytes, filename: str) -> dict[str, pd.DataFrame]:
    return read_grids(io.BytesIO(payload), filename)


@st.cache_data(show_spinner=False)
def _raw_view(grid: pd.DataFrame) -> pd.DataFrame:
    """The grid as plain text, so nothing is interpreted before the user says so."""
    return grid.fillna("").astype(str)


def _sheet_ui(sheet: str, grid: pd.DataFrame) -> None:
    header_key = f"sheet_header_row::{sheet}"
    data_key = f"sheet_data_row::{sheet}"
    raw_col, clean_col = st.columns(2)

    with raw_col:
        st.subheader("Raw sheet")
        st.caption(f"{len(grid)} rows × {len(grid.columns)} columns, nothing interpreted.")
        event = st.dataframe(
            _raw_view(grid),
            key=f"sheet_raw::{sheet}",
            on_select="rerun",
            selection_mode=["multi-row", "multi-column"],
            height=400,
        )
        picked = list((event or {}).get("selection", {}).get("rows", []))
        left, right = st.columns(2)
        if left.button(
            "☝️ This is my header row",
            key=f"sheet_pick_header::{sheet}",
            disabled=not picked,
            width="stretch",
        ):
            st.session_state[header_key] = picked[0]
            st.rerun()
        if right.button(
            "👇 This is my first data row",
            key=f"sheet_pick_data::{sheet}",
            disabled=not picked,
            width="stretch",
        ):
            st.session_state[data_key] = picked[0]
            st.rerun()

    with clean_col:
        st.subheader("Cleaned block")
        header_row = st.session_state.get(header_key)
        data_row = st.session_state.get(data_key)
        st.caption(
            f"Header row: {header_row if header_row is not None else '—'} · "
            f"first data row: {data_row if data_row is not None else '—'}"
        )
        if header_row is None or data_row is None:
            st.info(
                "Select a row on the left, then say whether it is the header row "
                "or the first data row."
            )
            return
        if data_row <= header_row:
            st.warning("The first data row must be below the header row.")
            return

        block = extract_block(grid, header_row, data_row)
        edited = st.data_editor(
            block.data.set_axis(block.labels(), axis=1),
            key=f"sheet_clean::{sheet}",
            height=400,
        )
        st.session_state[f"sheet_block::{sheet}"] = edited.set_axis(
            list(block.columns), axis=1
        )
        native = sorted(block.datetime_columns)
        st.caption(
            f"{len(edited)} rows × {len(block.columns)} columns. "
            + (
                f"Columns {native} already hold real datetimes."
                if native
                else "No column holds native datetimes."
            )
        )


def sheet_import_page() -> None:
    st.title("📗 Import Data (Sheet)")
    st.caption(
        "Upload a spreadsheet and point at your table. The old mapper page is "
        "still available while this one settles in."
    )
    upload = st.file_uploader(
        "CSV or Excel workbook",
        type=["csv", "xlsx", "xlsm", "xls"],
        help="Every worksheet of a workbook becomes a tab. Nothing is read as a table until you point at your header row.",
    )
    if upload is None:
        st.info("Upload a file to begin.")
        return

    grids = _grids(upload.getvalue(), upload.name)
    names = list(grids)
    for tab, name in zip(st.tabs(names), names):
        with tab:
            _sheet_ui(name, grids[name])


sheet_import_page()
