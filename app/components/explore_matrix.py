"""Matrix value-type figure builders for the Explore page.

Pure data→figure helpers extracted from explore.py (Phase 5): a time-slice
heatmap over (row × col) bins and a row/column time-series slice. Callers load
the data and pass it in. Re-exported from explore.py so existing references
resolve unchanged.
"""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st


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


def _build_matrix_timeslice(data: dict, timestamp: str) -> go.Figure:
    """Build a 2D heatmap for a specific timestamp slice of matrix data."""
    rows = data.get("data", [])
    if not rows:
        return go.Figure()

    df = pd.DataFrame(rows)
    ts_col = "timestamp"
    df[ts_col] = df[ts_col].astype(str)
    slice_df = df[df[ts_col] == timestamp]
    if slice_df.empty:
        st.warning(f"No data at {timestamp}")
        return go.Figure()

    row_labels = _matrix_axis_label_map(df, "row")
    col_labels = _matrix_axis_label_map(df, "col")
    slice_df = slice_df.copy()
    slice_df["row_label"] = slice_df["row_bin_index"].map(row_labels)
    slice_df["col_label"] = slice_df["col_bin_index"].map(col_labels)

    pivot = slice_df.pivot_table(
        index="row_label", columns="col_label", values="value", aggfunc="first"
    )
    fig = go.Figure(
        data=go.Heatmap(
            z=pivot.values.tolist(),
            x=pivot.columns.tolist(),
            y=pivot.index.tolist(),
            colorscale="Viridis",
        )
    )
    fig.update_layout(
        xaxis_title="Column bin",
        yaxis_title="Row bin",
        title=f"Matrix at {timestamp}",
        height=420,
    )
    return fig


def _build_matrix_slice_line(data: dict, axis: str, bin_idx: int) -> go.Figure:
    """Build a time-series line chart for a fixed row or column slice of matrix data."""
    rows = data.get("data", [])
    if not rows:
        return go.Figure()

    df = pd.DataFrame(rows)
    label_map = _matrix_axis_label_map(df, axis)
    bin_label = label_map.get(bin_idx, bin_idx)

    if axis == "row":
        slice_df = df[df["row_bin_index"] == bin_idx]
        trace_label = f"Row {bin_label}"
    else:
        slice_df = df[df["col_bin_index"] == bin_idx]
        trace_label = f"Col {bin_label}"

    fig = go.Figure(
        go.Scatter(
            x=slice_df["timestamp"].tolist(),
            y=slice_df["value"].tolist(),
            mode="lines+markers",
            name=trace_label,
        )
    )
    fig.update_layout(xaxis_title="Time", yaxis_title="Value", height=380)
    return fig
