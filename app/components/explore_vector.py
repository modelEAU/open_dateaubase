"""Vector value-type ECharts option builders for the Explore page.

Pure data→option helpers: a 2D heatmap and a 3D surface over (time × bin), plus
the two orthogonal slice line charts. No Streamlit state or API access — callers
load the data and pass it in. Re-exported from explore.py so existing references
resolve unchanged.
"""

from __future__ import annotations

import pandas as pd

from app.components.explore_echarts import (
    heatmap_option,
    line_option,
    pivot_cells,
    surface_option,
)


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


def _bin_axis_label(data: dict) -> str:
    """Label for the bin axis: the binning axis name and its unit (e.g.
    "Particle size (nm)"), falling back to a generic "Bin"."""
    first = (data.get("data") or [{}])[0]
    name = first.get("axis_name")
    unit = first.get("axis_unit")
    if name and unit:
        return f"{name} ({unit})"
    return name or unit or "Bin"


def _vector_pivot(data: dict):
    """Return a (bin_label × time) pivot of the vector data, or None if empty."""
    rows = data.get("data", [])
    if not rows:
        return None
    df = pd.DataFrame(rows)
    if df.empty or "bin_index" not in df.columns:
        return None
    bin_label_map = (
        df.drop_duplicates("bin_index").set_index("bin_index").apply(_bin_label, axis=1)
    )
    df["bin_label"] = df["bin_index"].map(bin_label_map)
    return df.pivot_table(
        index="bin_label", columns="timestamp", values="value", aggfunc="first"
    )


def build_vector_heatmap_option(data: dict) -> dict:
    """ECharts 2D heatmap (time × bin) for vector data."""
    pivot = _vector_pivot(data)
    if pivot is None:
        return {}
    x = [str(c) for c in pivot.columns.tolist()]
    y = [str(v) for v in pivot.index.tolist()]
    return heatmap_option(x, y, pivot_cells(pivot), _vector_value_label(data), "Time", _bin_axis_label(data))


def build_vector_surface_option(data: dict) -> dict:
    """echarts-gl 3D surface (time × bin × value) for vector data."""
    pivot = _vector_pivot(data)
    if pivot is None:
        return {}
    x = [str(c) for c in pivot.columns.tolist()]
    y = [str(v) for v in pivot.index.tolist()]
    cells = pivot_cells(pivot)
    zvals = [c[2] for c in cells]
    zmin = min(zvals) if zvals else 0
    zmax = max(zvals) if zvals else 1
    return surface_option(x, y, cells, zmin, zmax, _vector_value_label(data), "Time", _bin_axis_label(data))


def build_vector_slice_time_option(data: dict, timestamp: str) -> dict:
    """ECharts line: value vs bin label at a fixed timestamp."""
    rows = data.get("data", [])
    if not rows:
        return {}
    df = pd.DataFrame(rows)
    bin_label_map = (
        df.drop_duplicates("bin_index").set_index("bin_index").apply(_bin_label, axis=1)
    )
    df["bin_label"] = df["bin_index"].map(bin_label_map)
    slice_df = df[df["timestamp"].astype(str) == timestamp].sort_values("bin_label")
    return line_option(
        slice_df["bin_label"].tolist(), slice_df["value"].tolist(),
        _bin_axis_label(data), _vector_value_label(data),
    )


def build_vector_slice_bin_option(data: dict, bin_idx: int) -> dict:
    """ECharts line: value vs time at a fixed bin."""
    rows = data.get("data", [])
    if not rows:
        return {}
    df = pd.DataFrame(rows)
    slice_df = df[df["bin_index"] == bin_idx].sort_values("timestamp")
    return line_option(
        slice_df["timestamp"].astype(str).tolist(),
        slice_df["value"].tolist(),
        "Time",
        _vector_value_label(data),
    )
