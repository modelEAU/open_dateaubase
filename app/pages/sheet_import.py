"""Spreadsheet-first import — see the sheet, point at the header and the data.

Upload a workbook, pick a sheet, click the row holding your column names and
the first row of real data. Everything between is skipped. The cleaned block
renders beside the raw sheet and its cells are editable. Each column is then
mapped — in the vocabulary of the user's own work — from a field catalogue
derived from the ingest payload schemas, keyed by column index so repeated
header names stay independent.
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

from app.components.column_mapping import (
    IGNORE,
    empty_spec,
    mapping_frame,
    missing_required,
    spec_from_frame,
    validate,
)
from app.components.datetime_parse import FORMAT_PRESETS, detect_format, parse_values, to_utc
from app.components.field_catalogue import GROUPS, catalogue
from app.components.sheet_block import SheetBlock, extract_block, read_grids
from app.components.timezone_select import timezone_selector

_CUSTOM = "Custom…"
_CHOOSE = "— choose a format —"


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
        edited_indexed = edited.set_axis(list(block.columns), axis=1)
        st.session_state[f"sheet_block::{sheet}"] = edited_indexed
        native = sorted(block.datetime_columns)
        st.caption(
            f"{len(edited)} rows × {len(block.columns)} columns. "
            + (
                f"Columns {native} already hold real datetimes."
                if native
                else "No column holds native datetimes."
            )
        )
        _mapping_section(sheet, block)
        _datetime_section(sheet, block, edited_indexed)


def _mapping_section(sheet: str, block: SheetBlock) -> None:
    """One row per column: what the column holds, keyed by column index."""
    st.divider()
    st.subheader("🧭 Map the columns")
    cat = catalogue()
    spec_key = f"sheet_mapping::{sheet}"
    spec = st.session_state.get(spec_key)
    if spec is None or tuple(m.column for m in spec.mappings) != block.columns:
        spec = empty_spec(block)  # first visit, or the block was re-pointed
    edited = st.data_editor(
        mapping_frame(block, cat, spec),
        key=f"sheet_map::{sheet}",
        disabled=["Header", "Banner"],
        column_config={
            "Header": st.column_config.TextColumn(
                "Header", help="The column's header, collapsed to one line."
            ),
            "Banner": st.column_config.TextColumn(
                "Banner",
                help="The grouping banners above this column, forward-filled "
                "from the rows above the header. Read-only context — this is "
                "how repeated headers are told apart.",
            ),
            "Maps to": st.column_config.SelectboxColumn(
                "Maps to",
                options=[IGNORE, *cat.option_labels()],
                help="What this column holds, in the vocabulary of your work. "
                "Every column starts ignored.",
                width="large",
            ),
        },
        height=400,
    )
    spec = spec_from_frame(block, cat, edited)
    st.session_state[spec_key] = spec

    for error in validate(spec, block, cat):
        st.warning(error.message)
    if spec.mapped():
        missing = missing_required(spec, cat)
        if missing:
            st.caption(
                "Still needed before this can import: "
                + ", ".join(f.label for f in missing)
                + "."
            )
    else:
        st.caption(
            "Every column is ignored — pick what each column holds above. "
            "Columns you leave ignored are simply not imported."
        )
    _catalogue_browser(cat)


def _catalogue_browser(cat) -> None:
    """The full field vocabulary, grouped by activity — scope shown, never editable."""
    with st.expander("📖 Field catalogue — everything the import accepts"):
        st.caption(
            "Grouped by what you did, not by which table a field lives in. "
            "The scope — file, row or measurement — is a property of the "
            "field, never something you choose."
        )
        for group in GROUPS:
            st.markdown(f"**{group}**")
            for f in cat.in_group(group):
                line = (
                    f"- **{f.label}** — `{f.ref}` · {f.scope} scope"
                    + (" · required" if f.required else "")
                )
                if f.fk_table:
                    line += f" · picks from {f.fk_table}"
                st.markdown(line)
                if f.help:
                    st.caption(f.help)


def _show(moment) -> str:
    """A timestamp for the preview table, or a dash when there is none."""
    return "—" if pd.isna(moment) else moment.strftime("%Y-%m-%d %H:%M")


def _datetime_section(sheet: str, block: SheetBlock, data: pd.DataFrame) -> None:
    """Timezone, format and dual local/UTC preview for one date/time column."""
    st.divider()
    st.subheader("🕒 Dates & times")
    tz = timezone_selector(
        key=f"sheet_tz::{sheet}",
        label="File timezone",
        help="The timezone the file's times are written in. Parsed times preview "
        "below in both this zone and UTC, so a wrong pick is visible immediately.",
    )
    columns = list(block.columns)
    labels = block.labels()
    native_first = sorted(
        columns, key=lambda c: (c not in block.datetime_columns, columns.index(c))
    )
    column = st.selectbox(
        "Date/time column",
        options=native_first,
        format_func=lambda c: labels[columns.index(c)],
        key=f"sheet_dt_col::{sheet}",
        help="Which column holds each row's date/time. Columns already holding "
        "real dates sort first. Only one column previews at a time.",
    )
    values = data[column]

    if column in block.datetime_columns:
        st.info(
            "This column already holds real dates/times from the spreadsheet, so "
            "there is no format to choose — they are read as wall-clock times in "
            "the file timezone above."
        )
        parsed = parse_values(values, None)
    else:
        detection = detect_format(values)
        if detection.format is not None:
            st.success(f"Detected format: {detection.label}")
        else:
            st.warning("The date format cannot be told from the data — choose one yourself.")
        for line in detection.evidence:
            st.markdown(f"- {line}")
        options = [*FORMAT_PRESETS, _CUSTOM]
        if detection.label is not None:
            index = options.index(detection.label)
        else:
            options = [_CHOOSE, *options]
            index = 0
        choice = st.selectbox(
            "Date format",
            options=options,
            index=index,
            key=f"sheet_dt_fmt::{sheet}::{column}",
            help="How day, month and year are ordered in this column. Detection "
            "proposes a format when the evidence is clear and refuses when it "
            "is not — it never guesses.",
        )
        if choice == _CHOOSE:
            st.info("Choose a format to see the parsed times. Nothing is parsed until you do.")
            return
        if choice == _CUSTOM:
            fmt = st.text_input(
                "Custom format (strptime)",
                key=f"sheet_dt_custom::{sheet}::{column}",
                placeholder="%d/%m/%Y %H:%M",
                help="A Python strptime string, e.g. %d.%m.%Y %H:%M reads "
                "03.04.2026 14:30.",
            )
            if not fmt.strip():
                st.info("Enter a format to see the parsed times.")
                return
        else:
            fmt = FORMAT_PRESETS[choice]
        parsed = parse_values(values, fmt)

    if parsed.failures:
        st.warning(
            f"{len(parsed.failures)} value(s) would not parse — listed here, never "
            "dropped. Fix them in the cleaned table above or pick another format."
        )
        st.dataframe(
            pd.DataFrame(parsed.failures[:50], columns=["row", "value"]),
            hide_index=True,
        )
    utc = to_utc(parsed.wall_clock, tz)
    rows = list(values.index[:8])
    st.caption(
        f"First {len(rows)} of {len(values)} rows — wall-clock time in the file "
        "zone, and the UTC instant it becomes:"
    )
    st.dataframe(
        pd.DataFrame(
            {
                "row": rows,
                "value": [str(values.loc[row]) for row in rows],
                f"local ({tz.key})": [_show(parsed.wall_clock.loc[row]) for row in rows],
                "UTC": [_show(utc.loc[row]) for row in rows],
            }
        ),
        hide_index=True,
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
