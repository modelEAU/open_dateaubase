"""Campaign Story page coverage via streamlit.testing.v1.AppTest.

All api_client calls and the (heavy) Explore figure builder are patched, so the
test runs without a live API. It guards that the page assembles the overview
into its story sections without error and surfaces the key facts.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import plotly.graph_objects as go
from streamlit.testing.v1 import AppTest

PAGE = str(Path(__file__).parent.parent.parent / "app" / "pages" / "campaign_story.py")

_CAMPAIGNS = [{"campaign_id": 7, "name": "Verdun CSO Monitoring"}]
_CHANNELS = {
    "items": [
        {
            "channel_id": 101, "channel_kind_name": "Value", "parameter_name": "pH",
            "unit_name": "pH", "equipment_id": 12, "equipment_identifier": "EXO2 #A12",
        }
    ]
}
_OVERVIEW = {
    "campaign": {
        "campaign_id": 7, "campaign_kind_id": 2, "campaign_kind_name": "Monitoring",
        "site_id": 3, "site_name": "Verdun WRRF", "name": "Verdun CSO Monitoring",
        "description": None, "start_date": "2026-01-05T00:00:00", "end_date": None,
        "responsible_person_id": None, "responsible_person_name": "M. Tremblay",
    },
    "watershed": {"id": 1, "name": "Rivière St-Pierre"},
    "sampling_points": [{"id": 1, "name": "Inlet", "lat": 45.45, "lon": -73.57, "role": "Inlet"}],
    "data_acquisition_systems": [{"id": 1, "name": "CommCube-A", "kind": "Logger", "valid_from": None}],
    "equipment": [
        {"equipment_id": 12, "identifier": "EXO2 #A12", "model": "YSI EXO2",
         "role": "Primary sonde", "location": "Inlet", "is_active": True, "ongoing_event": None},
        {"equipment_id": 9, "identifier": "Spectro #C4", "model": "s::can",
         "role": "UV-Vis", "location": "Effluent", "is_active": True, "ongoing_event": "Maintenance"},
    ],
    "lab_series": [{"stream_id": 481, "name": "COD at Inlet", "parameter_name": "COD",
                    "unit_name": "mg/L", "value_kind_name": "Scalar", "sampling_point_label": "Inlet"}],
    "lab_panels": [{"id": 1, "name": "Winter influent panel", "series_count": 3}],
    "annotations": [{"id": 1, "kind": "Fault", "color": "#DC2626", "title": "Lamp failure",
                     "comment": "Spectro offline", "start_time": "2026-06-18T00:00:00", "end_time": None,
                     "anchor": "TEST_ COD at Influent"}],
    "freshness": [
        {"stream_id": 101, "kind": "sensor", "label": "pH",
         "first_point": "2026-01-06T00:00:00", "last_point": "2026-06-22T08:40:00"},
        {"stream_id": 481, "kind": "lab", "label": "COD at Inlet",
         "first_point": "2026-02-01T09:00:00", "last_point": "2026-06-19T14:10:00"},
    ],
}


def _run():
    # AppTest.from_file re-execs the page (re-running its ``from app.api_client
    # import ...`` lines), so patch the *source* modules, not the page module.
    with (
        patch("app.api_client.list_campaigns_lookup", return_value=_CAMPAIGNS),
        patch("app.api_client.get_campaign_overview", return_value=_OVERVIEW),
        patch("app.api_client.list_channels", return_value=_CHANNELS),
        patch("app.components.explore_scalar._build_scalar_figure", return_value=(go.Figure(), [])),
    ):
        return AppTest.from_file(PAGE).run()


def test_page_renders_without_error():
    at = _run()
    assert not at.exception


def test_plot_seeds_explore_session_state():
    # Regression: the reused Explore figure builder reads explore_start/_end and
    # the per-entity caches from session state. The page must seed them or the
    # plot raises AttributeError (caught only in the live browser, not by mocking
    # the builder). Guards that the seeding ran on the plot path.
    at = _run()
    assert at.session_state["explore_start"] is not None
    assert at.session_state["explore_end"] is not None
    for cache in ("explore_data", "explore_annotations", "explore_eq_events"):
        assert cache in at.session_state


def test_story_surfaces_key_facts():
    at = _run()
    blob = " ".join(m.value for m in at.markdown)
    assert "Verdun CSO Monitoring" in blob       # header title
    assert "Rivière St-Pierre" in blob           # watershed in meta
    assert "In service" in blob                  # healthy equipment status badge
    assert "Maintenance" in blob                 # ongoing-event status badge
    assert "Winter influent panel" in blob       # lab panel
    assert "Lamp failure" in blob                # annotation log
