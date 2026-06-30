"""Unit tests for PRD-2.5 S2 — maintenance control chart page.

Red→green: these tests verify the page can be imported and that
the pure helper functions work correctly without a running API.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pandas as pd
import pytest

# ---------------------------------------------------------------------------
# Module loader helpers
# ---------------------------------------------------------------------------

_PAGE_PATH = (
    Path(__file__).resolve().parent.parent.parent
    / "app"
    / "pages"
    / "maintenance_control_chart.py"
)


def _load_page_module():
    """Load maintenance_control_chart.py without running main() or hitting the API."""
    import unittest.mock as mock

    fake_st = mock.MagicMock()
    # _in_streamlit_run() → False so main() is not called at import time
    fake_st.runtime.scriptrunner.get_script_run_ctx.return_value = None

    with mock.patch.dict(sys.modules, {"streamlit": fake_st, "streamlit_echarts": mock.MagicMock()}):
        spec = importlib.util.spec_from_file_location("mcc_s2", str(_PAGE_PATH))
        assert spec is not None
        mod = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(mod)  # type: ignore[union-attr]

    return mod


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_page_file_exists():
    """Fails immediately if the page file is missing."""
    assert _PAGE_PATH.exists(), f"maintenance_control_chart.py not found at {_PAGE_PATH}"


def test_page_importable():
    """Page module must import without errors when streamlit is mocked."""
    mod = _load_page_module()
    assert mod is not None


def test_build_dataframe_empty():
    """_build_dataframe returns an empty DataFrame with correct columns for no rows."""
    mod = _load_page_module()
    df = mod._build_dataframe([])
    assert list(df.columns) == ["timestamp", "value", "quality_code_id"]
    assert len(df) == 0


def test_build_dataframe_basic():
    """_build_dataframe converts rows to a sorted DataFrame with correct dtypes."""
    mod = _load_page_module()
    rows = [
        {"timestamp": "2024-01-02T00:00:00Z", "value": 3.14, "quality_code_id": None},
        {"timestamp": "2024-01-01T00:00:00Z", "value": 2.71, "quality_code_id": 1},
    ]
    df = mod._build_dataframe(rows)
    assert len(df) == 2
    # Sorted by timestamp
    assert df.iloc[0]["value"] == pytest.approx(2.71)
    assert df.iloc[1]["value"] == pytest.approx(3.14)
    # quality_code_id preserved
    assert df.iloc[0]["quality_code_id"] == 1


def test_build_chart_option_structure():
    """_build_chart_option returns a dict with required ECharts keys."""
    mod = _load_page_module()

    drift_rows = [
        {"timestamp": "2024-01-01T00:00:00Z", "value": 1.0, "quality_code_id": None},
        {"timestamp": "2024-01-02T00:00:00Z", "value": 10.0, "quality_code_id": None},  # out-of-limit
        {"timestamp": "2024-01-03T00:00:00Z", "value": 2.0, "quality_code_id": 99},    # flagged
    ]
    drift_df = mod._build_dataframe(drift_rows)
    source_df = pd.DataFrame(columns=["timestamp", "value", "quality_code_id"])

    option = mod._build_chart_option(drift_df, source_df, upper_limit=5.0, lower_limit=-5.0, quality_codes={})

    assert "series" in option
    assert "xAxis" in option
    assert "yAxis" in option
    assert "dataZoom" in option

    series_names = [s["name"] for s in option["series"]]
    assert "Drift" in series_names
    assert "Out of limit" in series_names
    assert "Quality-flagged" in series_names


def test_out_of_limit_points_separated():
    """Points outside [lower, upper] must end up in the 'Out of limit' series."""
    mod = _load_page_module()

    rows = [
        {"timestamp": "2024-01-01T00:00:00Z", "value": 0.0, "quality_code_id": None},   # in-limit
        {"timestamp": "2024-01-02T00:00:00Z", "value": 8.0, "quality_code_id": None},    # above UCL=5
        {"timestamp": "2024-01-03T00:00:00Z", "value": -8.0, "quality_code_id": None},   # below LCL=-5
    ]
    df = mod._build_dataframe(rows)
    source_df = pd.DataFrame(columns=["timestamp", "value", "quality_code_id"])
    option = mod._build_chart_option(df, source_df, upper_limit=5.0, lower_limit=-5.0, quality_codes={})

    ool_series = next(s for s in option["series"] if s["name"] == "Out of limit")
    assert len(ool_series["data"]) == 2

    normal_series = next(s for s in option["series"] if s["name"] == "Drift")
    assert len(normal_series["data"]) == 1


def test_source_series_included_when_provided():
    """A non-empty source_df adds a 'Raw source' series to the chart."""
    mod = _load_page_module()

    drift_rows = [{"timestamp": "2024-01-01T00:00:00Z", "value": 1.0, "quality_code_id": None}]
    source_rows = [{"timestamp": "2024-01-01T00:00:00Z", "value": 100.0, "quality_code_id": None}]
    drift_df = mod._build_dataframe(drift_rows)
    source_df = mod._build_dataframe(source_rows)

    option = mod._build_chart_option(drift_df, source_df, upper_limit=5.0, lower_limit=-5.0, quality_codes={})
    series_names = [s["name"] for s in option["series"]]
    assert "Raw source" in series_names


def test_navigation_includes_maintenance_chart():
    """Home.py navigation must reference maintenance_control_chart.py."""
    home_path = Path(__file__).resolve().parent.parent.parent / "app" / "Home.py"
    content = home_path.read_text()
    assert "maintenance_control_chart.py" in content, (
        "Home.py does not reference maintenance_control_chart.py — page not wired into navigation"
    )
