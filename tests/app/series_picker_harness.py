"""Minimal Streamlit harness for series_picker AppTest.

Not a test file — executed by AppTest.from_file(). The picker calls
``st.rerun(scope="fragment")`` after creating a series, so it must run inside a
fragment; a dialog is what the real caller (form_dialog) uses.
"""
from __future__ import annotations

import sys
from pathlib import Path

_root = str(Path(__file__).parent.parent.parent)
if _root not in sys.path:
    sys.path.insert(0, _root)

import streamlit as st

from app.components.series_picker import render_series_picker

CAMPAIGNS = [{"campaign_id": 1, "name": "Alpha"}, {"campaign_id": 2, "name": "Beta"}]
PARAMETERS = [
    {"parameter_id": 10, "parameter_name": "TSS", "value_kind_id": 1},
    {"parameter_id": 11, "parameter_name": "Thermal image", "value_kind_id": 4},
]
SAMPLING_POINTS = [
    {"sampling_point_id": 100, "label": "Inlet"},
    {"sampling_point_id": 101, "label": "Outlet"},
]
UNITS = [{"unit_id": 5, "unit": "mg/L"}]
SERIES = [
    {
        "analysis_series_id": 1,
        "name": "TSS at Inlet",
        "parameter_id": 10,
        "parameter_name": "TSS",
        "sampling_point_id": 100,
        "sampling_point_label": "Inlet",
        "unit_name": "mg/L",
        "value_kind_id": 1,
        "campaign_id": 1,
    }
]


@st.dialog("Picker")
def _show() -> None:
    render_series_picker(
        {"field_name": "series", "label": "Series", "value": [], "required": False},
        series_list=SERIES,
        campaigns=CAMPAIGNS,
        parameters=PARAMETERS,
        sampling_points=SAMPLING_POINTS,
        units=UNITS,
    )


_show()
