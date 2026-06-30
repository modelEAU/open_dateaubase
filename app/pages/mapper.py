"""Mapper Engine — S2: upload CSV/XLSX → pick sheet/header/range
→ tag column roles → preview → resolve entities (text → DB ID).

PRD-3 S1: shell. PRD-3 S2: entity resolution.
"""

from __future__ import annotations

import sys
from pathlib import Path

_project_root = str(Path(__file__).resolve().parent.parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

import io

import pandas as pd
import streamlit as st

import app.api_client as api
from app.components.resolver import EntityResolver

# ---------------------------------------------------------------------------
# Profile stub — role vocabulary (S1: hardcoded; S2+ will load from saved profile)
# ---------------------------------------------------------------------------

LAB_ROLES = [
    "(ignore)",
    "sample_datetime",
    "sampling_location",
    "replicate",
    "parameter_value",
]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _read_dataframe(
    file_bytes: bytes,
    filename: str,
    sheet_name: str | int = 0,
    header_row: int = 0,
) -> pd.DataFrame:
    """Parse uploaded file into a DataFrame using the given sheet and header."""
    if filename.endswith(".xlsx"):
        return pd.read_excel(
            io.BytesIO(file_bytes),
            sheet_name=sheet_name,
            header=header_row,
        )
    # CSV — sheet_name is ignored
    return pd.read_csv(io.BytesIO(file_bytes), header=header_row)


# ---------------------------------------------------------------------------
# Page
# ---------------------------------------------------------------------------


def mapper_page() -> None:
    st.header("Import Data (Mapper)")
    st.caption("PRD-3 S1 — engine shell: upload → tag column roles → preview")

    uploaded = st.file_uploader(
        "Upload a spreadsheet",
        type=["csv", "xlsx"],
        help="CSV or Excel files are supported.",
    )

    if uploaded is None:
        st.info("Upload a CSV or XLSX file to get started.")
        return

    file_bytes = uploaded.read()
    filename = uploaded.name

    # ------------------------------------------------------------------
    # Sheet picker (XLSX only)
    # ------------------------------------------------------------------
    sheet_name: str | int = 0
    if filename.endswith(".xlsx"):
        try:
            xl = pd.ExcelFile(io.BytesIO(file_bytes))
            sheet_names = xl.sheet_names
        except Exception as exc:
            st.error(f"Could not open Excel file: {exc}")
            return

        if len(sheet_names) > 1:
            sheet_name = st.selectbox("Sheet", options=sheet_names, index=0, key="mapper_sheet")
        else:
            sheet_name = sheet_names[0]
            st.info(f"Sheet: **{sheet_name}**")

    # ------------------------------------------------------------------
    # Header row / data start row
    # ------------------------------------------------------------------
    col_h, col_d = st.columns(2)
    with col_h:
        header_row = st.number_input(
            "Header row (0-indexed)",
            min_value=0,
            value=0,
            step=1,
            key="mapper_header_row",
            help="Row number containing column names (0 = first row).",
        )
    with col_d:
        data_start_row = st.number_input(
            "Data start row (0-indexed)",
            min_value=0,
            value=1,
            step=1,
            key="mapper_data_start",
            help="First row of data (must be > header row).",
        )

    # ------------------------------------------------------------------
    # Parse
    # ------------------------------------------------------------------
    try:
        df = _read_dataframe(file_bytes, filename, sheet_name=sheet_name, header_row=int(header_row))
    except Exception as exc:
        st.error(f"Could not parse file: {exc}")
        return

    if df.empty:
        st.warning("The parsed table is empty. Check header row and sheet settings.")
        return

    # Slice to data_start_row
    data_start = int(data_start_row)
    if data_start > 0:
        # header_row already consumed by pd.read_excel/csv; data_start_row is relative
        # to the full file, so offset by header_row + 1 (already stripped by pandas).
        skip = max(0, data_start - int(header_row) - 1)
        df_data = df.iloc[skip:].reset_index(drop=True)
    else:
        df_data = df.copy()

    columns = list(df.columns.astype(str))
    st.markdown(f"**{len(columns)} columns** detected")

    # ------------------------------------------------------------------
    # Role tagging — one selectbox per column
    # ------------------------------------------------------------------
    st.subheader("Tag column roles")
    st.caption("Assign a role to each column. Columns tagged '(ignore)' are excluded from the preview.")

    role_map: dict[str, str] = {}
    n_cols = min(len(columns), 4)
    grid_rows = [columns[i : i + n_cols] for i in range(0, len(columns), n_cols)]

    for row_cols in grid_rows:
        grid = st.columns(len(row_cols))
        for col_widget, col_name in zip(grid, row_cols):
            with col_widget:
                role = st.selectbox(
                    col_name,
                    options=LAB_ROLES,
                    index=0,
                    key=f"mapper_role_{col_name}",
                )
                role_map[col_name] = role

    # ------------------------------------------------------------------
    # Dumb preview — first 5 rows, role-tagged columns only
    # ------------------------------------------------------------------
    st.subheader("Preview")
    active_cols = {col: role for col, role in role_map.items() if role != "(ignore)"}

    if not active_cols:
        st.info("Tag at least one column with a role to see the preview.")
        return

    preview_df = df_data[list(active_cols.keys())].head(5).copy()
    preview_df.columns = [f"{col} [{role}]" for col, role in active_cols.items()]
    st.dataframe(preview_df, use_container_width=True)
    st.caption("Preview shows the first 5 data rows with role labels as column headers.")

    # ------------------------------------------------------------------
    # S2: Entity resolution — columns tagged as parameter_value
    # ------------------------------------------------------------------
    param_value_cols = [col for col, role in active_cols.items() if role == "parameter_value"]
    if param_value_cols:
        st.subheader("Resolve entities")
        st.caption(
            "Match column headers to Parameters in the database using fuzzy text matching. "
            "Unresolved columns are listed so nothing is silently dropped."
        )
        if st.button("Resolve entities", key="mapper_resolve"):
            try:
                units_list = api.list_units_lookup()
                params_list = api.list_parameters_lookup()
                sps_list = api.list_sampling_points_lookup()
            except Exception as exc:
                st.error(f"Could not load lookup data from API: {exc}")
                return

            resolver = EntityResolver(
                units=units_list,
                parameters=params_list,
                sampling_points=sps_list,
            )

            rows = []
            for col in param_value_cols:
                match = resolver.resolve_parameter(col)
                rows.append(
                    {
                        "Column header": col,
                        "Matched parameter": match["name"] if match else "— unresolved —",
                        "parameter_id": match["parameter_id"] if match else None,
                        "Status": "✓ resolved" if match else "✗ unresolved",
                    }
                )

            result_df = pd.DataFrame(rows)
            st.dataframe(result_df, use_container_width=True)

            unresolved = [r["Column header"] for r in rows if r["parameter_id"] is None]
            if unresolved:
                st.warning(
                    f"{len(unresolved)} column(s) could not be matched: "
                    + ", ".join(f"**{c}**" for c in unresolved)
                    + ". Review column names or add the missing parameters."
                )
            else:
                st.success("All parameter_value columns resolved successfully.")


mapper_page()
