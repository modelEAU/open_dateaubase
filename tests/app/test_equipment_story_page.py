"""Equipment Story page coverage via streamlit.testing.v1.AppTest.

api_client is patched at the source module (AppTest re-execs the page's
``from app.api_client import ...``), so no live API is needed.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

PAGE = str(Path(__file__).parent.parent.parent / "app" / "pages" / "equipment_story.py")

_EQUIPMENT = [{"equipment_id": 12, "identifier": "EXO2 #A12"}]
_STORY = {
    "equipment": {
        "equipment_id": 12, "identifier": "EXO2 #A12", "serial_number": "18C103456",
        "model": "YSI EXO2", "manufacturer": "YSI", "owner": "modelEAU",
        "purchase_date": "2019-03-14", "is_active": True, "current_location": "Inlet",
    },
    "campaigns": [{"id": 7, "name": "Verdun CSO Monitoring", "kind": "Monitoring",
                   "role": "Primary sonde", "start": "2026-01-05T00:00:00", "end": None}],
    "location_history": [
        {"location": "Inlet", "valid_from": "2026-01-05T00:00:00", "valid_to": None,
         "campaign": "Verdun CSO Monitoring", "notes": None},
        {"location": "Bioreactor 2", "valid_from": "2024-04-02T00:00:00",
         "valid_to": "2025-10-30T00:00:00", "campaign": "pilEAUte", "notes": None},
    ],
    "events": [
        {"id": 1, "kind": "Sensor failure", "start": "2026-06-02T00:00:00", "end": None,
         "instantaneous": False, "notes": "Conductivity cell drift"},
        {"id": 2, "kind": "Calibration", "start": "2025-11-20T00:00:00", "end": None,
         "instantaneous": True, "notes": "Annual calibration"},
    ],
    "streams": [{"stream_id": 101, "parameter_name": "pH", "unit_name": "pH",
                 "channel_kind": "Value", "point_count": 14210}],
    "annotations": [{"id": 1, "kind": "Fault", "color": "#DC2626", "title": "Cell drift flagged",
                     "comment": "masked", "start_time": "2026-06-02T00:00:00",
                     "end_time": None, "anchor": "Conductivity"}],
}


def _run():
    with (
        patch("app.api_client.list_equipment_lookup", return_value=_EQUIPMENT),
        patch("app.api_client.get_equipment_story", return_value=_STORY),
    ):
        return AppTest.from_file(PAGE).run()


def test_page_renders_without_error():
    assert not _run().exception


def test_timeline_merges_and_orders_events():
    at = _run()
    blob = " ".join(m.value for m in at.markdown)
    assert "EXO2 #A12" in blob                 # header
    assert "In service" in blob                # active badge
    assert "Sensor failure" in blob            # event in timeline
    assert "Installed at Inlet" in blob        # location move in timeline
    assert "Verdun CSO Monitoring" in blob     # campaign stint in timeline
    assert "Cell drift flagged" in blob        # annotation feed
    # Newest event (2026-06-02 failure) must appear before the older one (2025-11-20).
    assert blob.index("Sensor failure") < blob.index("Calibration")
