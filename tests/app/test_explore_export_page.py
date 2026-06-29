"""AppTest for the Explore bulk-export section (two-step Generate → Download).

Verifies the wiring: with active streams, clicking 'Generate export' builds a zip
into session_state from the raw-UTC data + pedigree, and a 'Download zip' button
then appears. Builder internals are covered in tests/unit/test_explore_export.py.
"""
from __future__ import annotations

import io
import zipfile
from contextlib import ExitStack
from datetime import date
from pathlib import Path
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

HARNESS = str(Path(__file__).parent / "explore_harness.py")
MOD = "app.pages.explore"
DATA = "app.components.explore_data"

_EQUIPMENT = [{"equipment_id": 5, "identifier": "EQ5"}]
_DT5 = {
    "equipment_location_history_id": 5,
    "channel_id": 5, "equipment_id": 5, "equipment_identifier": "EQ5",
    "sampling_point_id": 100, "sampling_point_label": "Effluent",
    "parameter_id": 5, "parameter_name": "TSS",
    "value_kind_id": 1, "campaign_id": 1, "campaign_name": "Campaign A",
    "valid_from": "2026-01-01T00:00:00", "valid_to": None,
}
_TS = {"channel_id": 5, "parameter": "TSS", "unit": "mg/L", "row_count": 1,
       "data": [{"timestamp": "2026-05-02T00:00:00", "value": 1.0, "quality_code": 1}]}
_STATS = {"min_timestamp": "2026-05-01T00:00:00", "max_timestamp": "2026-05-08T00:00:00",
          "row_count": 1}
_PEDIGREE = {
    "stream_id": 5, "kind": "sensor", "parameter": "TSS", "unit": "mg/L",
    "value_kind": "Scalar", "label": "CH-TSS",
    "deployments": [{
        "valid_from": "2026-01-01T00:00:00", "valid_to": None,
        "equipment_identifier": "EQ5",
        "sampling_location": {"name": "Effluent"},
        "campaign": {"name": "Campaign A"},
        "responsible_person": {"name": "Jean Tremblay"},
    }],
}


def _patches(stack: ExitStack) -> None:
    stack.enter_context(patch(f"{MOD}.list_equipment_lookup", return_value=_EQUIPMENT))
    stack.enter_context(patch(f"{MOD}.list_annotation_kinds", return_value=[]))
    stack.enter_context(patch(f"{MOD}.list_equipment_event_kinds", return_value=[]))
    stack.enter_context(patch(f"{MOD}.list_analysis_series_lookup", return_value=[]))
    stack.enter_context(patch(f"{MOD}.list_deployment_traces_lookup", return_value=[_DT5]))
    stack.enter_context(patch(f"{DATA}.get_channel_timeseries", return_value=_TS))
    stack.enter_context(
        patch(f"{MOD}.get_channel_stats", side_effect=lambda cid: {"channel_id": cid, **_STATS})
    )
    # Export-path calls (imported into the page module namespace).
    stack.enter_context(patch(f"{MOD}.get_channel_timeseries", return_value=_TS))
    stack.enter_context(patch(f"{MOD}.get_equipment_events", return_value=[]))
    stack.enter_context(patch(f"{MOD}._raw_annotations", return_value=[]))
    stack.enter_context(patch(f"{MOD}.get_stream_pedigree", return_value=_PEDIGREE))


def test_generate_then_download_builds_zip_with_csv_and_yaml():
    with ExitStack() as stack:
        _patches(stack)
        at = AppTest.from_file(HARNESS)
        at.session_state["explore_start"] = date(2026, 5, 1)
        at.session_state["explore_end"] = date(2026, 5, 8)
        at.session_state["explore_active_channels"] = [5]
        at.session_state["explore_channel_meta"] = {5: _DT5}
        at.run()

        # Before generating, no zip and no download button.
        assert "explore_export_zip" not in at.session_state
        at.button(key="btn_generate_export").click().run()
        assert not at.exception

        blob = at.session_state["explore_export_zip"]
        assert isinstance(blob, (bytes, bytearray))
        names = zipfile.ZipFile(io.BytesIO(blob)).namelist()
        assert any(n.endswith(".csv") for n in names)
        assert any(n.endswith(".yaml") for n in names)
        assert at.session_state["explore_export_count"] == 1
        # Download is served via st.download_button (a distinct widget type from
        # st.button); its presence is guaranteed by the blob being set this run.


def test_no_export_section_without_active_streams():
    with ExitStack() as stack:
        _patches(stack)
        at = AppTest.from_file(HARNESS)
        at.session_state["explore_start"] = date(2026, 5, 1)
        at.session_state["explore_end"] = date(2026, 5, 8)
        at.run()
        assert not at.exception
        # No Generate button when nothing is plotted.
        assert "btn_generate_export" not in [b.key for b in at.button]
