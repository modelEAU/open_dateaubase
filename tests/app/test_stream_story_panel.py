"""Stream Story panel coverage (the additive Explore section).

Exercises ``explore._render_stream_story_panel`` in isolation via a tiny AppTest
harness that seeds an inspected stream and patches the api_client source.
"""

from __future__ import annotations

from unittest.mock import patch

from streamlit.testing.v1 import AppTest

_HARNESS = """
import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd()))
import streamlit as st
from app.pages.explore import _render_stream_story_panel

st.session_state.setdefault("explore_inspect_trail", [("channel", 101)])
_render_stream_story_panel()
"""

_STORY = {
    "stream_id": 101,
    "record": {
        "kind": "sensor", "parameter_name": "pH", "unit_name": "pH",
        "value_kind_name": "Scalar", "label": "pH/raw",
        "first_point": "2024-04-02T00:00:00", "last_point": "2026-06-22T08:40:00",
        "point_count": 14210,
    },
    "location_history": [{"location": "Inlet", "valid_from": "2026-01-05T00:00:00",
                          "valid_to": None, "equipment": "EXO2 #A12"}],
    "annotations": [{"id": 1, "kind": "Mask", "color": "#DC2626", "title": "Sensor fault masked",
                     "comment": "drift", "start_time": "2026-06-02T00:00:00", "end_time": None}],
}


def _run():
    # The harness imports the panel from the already-loaded explore module, so
    # patch the name where explore bound it (not the api_client source).
    with patch("app.pages.explore.get_stream_story", return_value=_STORY):
        return AppTest.from_string(_HARNESS).run()


def test_panel_renders_without_error():
    assert not _run().exception


def test_panel_shows_record_location_and_annotations():
    at = _run()
    blob = " ".join(m.value for m in at.markdown)
    assert "What it records" in blob
    assert "Inlet" in blob                      # location history
    assert "Sensor fault masked" in blob        # annotation feed
