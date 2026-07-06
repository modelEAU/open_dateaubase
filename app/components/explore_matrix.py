"""Matrix value-type ECharts option builders for the Explore page.

Pure data→option helpers: a time-slice heatmap over (row × col) bins and a
row/column time-series slice. Callers load the data and pass it in. Re-exported
from explore.py so existing references resolve unchanged.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from app.components.explore_echarts import heatmap_option, line_option, pivot_cells


def _matrix_axis_label_map(df: "pd.DataFrame", axis: str) -> dict:
    """Return {bin_index: label} for the given matrix axis ('row' or 'col').

    Label priority: nominal_value → (lower+upper)/2 → bin_index.
    """
    prefix = axis  # 'row' or 'col'
    idx_col = f"{prefix}_bin_index"
    nom_col = f"{prefix}_nominal_value"
    lb_col = f"{prefix}_lower_bound"
    ub_col = f"{prefix}_upper_bound"

    result = {}
    for _, row in df.drop_duplicates(idx_col).iterrows():
        nv = row.get(nom_col)
        if nv is not None:
            result[row[idx_col]] = nv
            continue
        lb = row.get(lb_col)
        ub = row.get(ub_col)
        if lb is not None and ub is not None:
            result[row[idx_col]] = (lb + ub) / 2
            continue
        result[row[idx_col]] = row[idx_col]
    return result


def _axis_label(data: dict, axis: str) -> str:
    """Label for a matrix axis: its binning-axis name + unit (e.g. "Wavelength
    (nm)"), falling back to "Row bin"/"Column bin"."""
    first = (data.get("data") or [{}])[0]
    name = first.get(f"{axis}_axis_name")
    unit = first.get(f"{axis}_axis_unit")
    if name and unit:
        return f"{name} ({unit})"
    return name or unit or ("Row bin" if axis == "row" else "Column bin")


def build_matrix_timeslice_option(data: dict, timestamp: str) -> dict:
    """ECharts heatmap for a specific timestamp slice of matrix data."""
    rows = data.get("data", [])
    if not rows:
        return {}
    df = pd.DataFrame(rows)
    df["timestamp"] = df["timestamp"].astype(str)
    slice_df = df[df["timestamp"] == timestamp]
    if slice_df.empty:
        st.warning(f"No data at {timestamp}")
        return {}
    row_labels = _matrix_axis_label_map(df, "row")
    col_labels = _matrix_axis_label_map(df, "col")
    slice_df = slice_df.copy()
    slice_df["row_label"] = slice_df["row_bin_index"].map(row_labels)
    slice_df["col_label"] = slice_df["col_bin_index"].map(col_labels)
    pivot = slice_df.pivot_table(
        index="row_label", columns="col_label", values="value", aggfunc="first"
    )
    x = [str(c) for c in pivot.columns.tolist()]
    y = [str(v) for v in pivot.index.tolist()]
    return heatmap_option(
        x, y, pivot_cells(pivot), "Value",
        _axis_label(data, "col"), _axis_label(data, "row"),
    )


def build_matrix_slice_line_option(data: dict, axis: str, bin_idx: int) -> dict:
    """ECharts time-series line for a fixed row or column slice of matrix data."""
    rows = data.get("data", [])
    if not rows:
        return {}
    df = pd.DataFrame(rows)
    label_map = _matrix_axis_label_map(df, axis)
    bin_label = label_map.get(bin_idx, bin_idx)
    if axis == "row":
        slice_df = df[df["row_bin_index"] == bin_idx]
        name = f"Row {bin_label}"
    else:
        slice_df = df[df["col_bin_index"] == bin_idx]
        name = f"Col {bin_label}"
    slice_df = slice_df.sort_values("timestamp")
    return line_option(
        slice_df["timestamp"].astype(str).tolist(),
        slice_df["value"].tolist(),
        "Time",
        "Value",
        name=name,
    )
