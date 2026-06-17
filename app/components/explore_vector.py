"""Vector value-type figure builders for the Explore page.

Pure data→figure helpers extracted from explore.py (Phase 5): a 2D/3D heatmap
over (time × bin) plus the two orthogonal slice charts. No Streamlit state or
API access — callers load the data and pass it in. Re-exported from explore.py
so existing references resolve unchanged.
"""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go


def _bin_label(row: dict) -> float:
    """Return a numeric label for a bin row.

    Priority: nominal_value → midpoint of (lower_bound + upper_bound) / 2 → bin_index.
    """
    nv = row.get("nominal_value")
    if nv is not None:
        return nv
    lb = row.get("lower_bound")
    ub = row.get("upper_bound")
    if lb is not None and ub is not None:
        return (lb + ub) / 2
    return row["bin_index"]


def _vector_value_label(data: dict) -> str:
    param = data.get("parameter") or ""
    unit = data.get("unit") or ""
    return f"{param} ({unit})" if param and unit else param or unit or "Value"


def _build_vector_heatmap(data: dict, as_3d: bool = False) -> go.Figure:
    """Build a 2D heatmap (time × bin) or 3D surface for vector data."""
    rows = data.get("data", [])
    if not rows:
        return go.Figure()

    df = pd.DataFrame(rows)
    if df.empty or "bin_index" not in df.columns:
        return go.Figure()

    # Build a label per bin_index (consistent across all timestamps)
    bin_label_map = (
        df.drop_duplicates("bin_index")
        .set_index("bin_index")
        .apply(_bin_label, axis=1)
    )
    df["bin_label"] = df["bin_index"].map(bin_label_map)

    pivot = df.pivot_table(
        index="bin_label", columns="timestamp", values="value", aggfunc="first"
    )
    z = pivot.values.tolist()
    x = [str(c) for c in pivot.columns.tolist()]
    y = pivot.index.tolist()

    value_label = _vector_value_label(data)

    if as_3d:
        # go.Surface requires numeric axes — use integer indices for time
        x_numeric = list(range(len(x)))
        tick_step = max(1, len(x) // 10)
        tickvals = x_numeric[::tick_step]
        ticktext = x[::tick_step]
        fig = go.Figure(data=[go.Surface(z=z, x=x_numeric, y=y, colorscale="Viridis")])
        fig.update_layout(
            scene=dict(
                xaxis=dict(title="Time", tickvals=tickvals, ticktext=ticktext),
                yaxis=dict(title="Bin"),
                zaxis=dict(title=value_label),
            ),
            height=520,
        )
    else:
        fig = go.Figure(
            data=go.Heatmap(
                z=z,
                x=x,
                y=y,
                colorscale="Viridis",
                hoverongaps=False,
                colorbar=dict(title=value_label),
            )
        )
        fig.update_layout(
            xaxis_title="Time",
            yaxis_title="Bin",
            height=420,
        )
    return fig


def _build_vector_slice_time(data: dict, timestamp: str) -> go.Figure:
    """Vertical slice: value vs bin label at a fixed timestamp."""
    rows = data.get("data", [])
    if not rows:
        return go.Figure()
    df = pd.DataFrame(rows)
    bin_label_map = (
        df.drop_duplicates("bin_index")
        .set_index("bin_index")
        .apply(_bin_label, axis=1)
    )
    df["bin_label"] = df["bin_index"].map(bin_label_map)
    slice_df = df[df["timestamp"].astype(str) == timestamp].sort_values("bin_label")
    value_label = _vector_value_label(data)
    fig = go.Figure(
        go.Scatter(
            x=slice_df["bin_label"].tolist(),
            y=slice_df["value"].tolist(),
            mode="lines+markers",
        )
    )
    fig.update_layout(xaxis_title="Bin", yaxis_title=value_label, height=320)
    return fig


def _build_vector_slice_bin(data: dict, bin_idx: int) -> go.Figure:
    """Horizontal slice: value vs time at a fixed bin."""
    rows = data.get("data", [])
    if not rows:
        return go.Figure()
    df = pd.DataFrame(rows)
    bin_label_map = (
        df.drop_duplicates("bin_index")
        .set_index("bin_index")
        .apply(_bin_label, axis=1)
    )
    slice_df = df[df["bin_index"] == bin_idx].sort_values("timestamp")
    value_label = _vector_value_label(data)
    label = bin_label_map.get(bin_idx, bin_idx)
    fig = go.Figure(
        go.Scatter(
            x=slice_df["timestamp"].tolist(),
            y=slice_df["value"].tolist(),
            mode="lines+markers",
            name=f"Bin {label}",
        )
    )
    fig.update_layout(xaxis_title="Time", yaxis_title=value_label, height=320)
    return fig
