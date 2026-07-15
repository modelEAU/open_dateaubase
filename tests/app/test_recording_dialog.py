"""The Recording dialog routes by rung (wayfinder 004/006/007/008).

The interesting assertion is the routing, so assert it directly: the stream rung
writes one Annotation per selected stream and no Event; any other rung writes one
Event with exactly that arc FK set. Driven via AppTest.from_function so the
@st.dialog body is re-opened on every rerun (the standard dialog-test pattern).
"""
from __future__ import annotations

from unittest.mock import patch

from streamlit.testing.v1 import AppTest

MOD = "app.pages.explore"

_VERDICTS = [
    {"id": 7, "name": "Data Quality", "description": "Suspect data"},
    {"id": 8, "name": "Note", "description": "General commentary"},
]
_CAUSES = [
    {"event_kind_id": 2, "name": "Cleaning", "description": "Physically cleaned"},
    {"event_kind_id": 3, "name": "Calibration", "description": "Adjusted"},
]


def _ped(
    stream_id: int,
    *,
    equipment=(5, "EQ5"),
    sp=(100, "Effluent"),
    pu=(7, "R-210"),
    site=(3, "pilEAU"),
    campaign=(1, "Campaign A"),
    si=(4, "Modbus RTU"),
    das=(2, "SCADA"),
) -> dict:
    return {
        "stream_id": stream_id,
        "kind": "sensor",
        "label": f"CH-{stream_id}",
        "parameter": "TSS",
        "signal_interface": {"id": si[0], "name": si[1]} if si else None,
        "data_acquisition_system": {"id": das[0], "name": das[1]} if das else None,
        "deployments": [{
            "equipment_id": equipment[0] if equipment else None,
            "equipment_identifier": equipment[1] if equipment else None,
            "sampling_location": {"sampling_point_id": sp[0], "name": sp[1]} if sp else None,
            "process_unit": {"process_unit_id": pu[0], "tag": pu[1]} if pu else None,
            "site": {"site_id": site[0], "name": site[1]} if site else None,
            "campaign": {"campaign_id": campaign[0], "name": campaign[1]} if campaign else None,
        }],
    }


def _run_dialog(streams, observation_id=None) -> None:
    import sys
    from pathlib import Path

    root = str(Path(__file__).parent.parent.parent)
    if root not in sys.path:
        sys.path.insert(0, root)
    from app.pages import explore as ex

    ex._recording_dialog(
        streams=streams,
        start_time="2026-05-01T00:00:00",
        end_time="2026-05-08T00:00:00",
        observation_id=observation_id,
    )


def test_stream_rung_verdict_writes_one_annotation_per_stream_no_event():
    ann_calls: list = []
    with ExitStack_patches(
        peds={5: _ped(5), 6: _ped(6)},
    ), patch(f"{MOD}.create_annotation", side_effect=lambda **kw: ann_calls.append(kw)) \
            as _ca, patch(f"{MOD}.create_event") as ce:
        at = AppTest.from_function(
            _run_dialog, kwargs={"streams": [("channel", 5), ("channel", 6)]}
        ).run()
        at.selectbox(key="rec_target").select("__stream__").run()
        at.selectbox(key="rec_kind").select("Data Quality").run()
        at.button(key="rec_save").click().run()

    assert not at.exception
    assert len(ann_calls) == 2, f"one verdict per selected stream; got {ann_calls}"
    assert {c["stream_id"] for c in ann_calls} == {5, 6}
    assert all(c["data"]["annotation_type"] == 7 for c in ann_calls)
    ce.assert_not_called()


def test_equipment_rung_cause_writes_one_event_with_one_arc_fk():
    ev_calls: list = []
    with ExitStack_patches(peds={5: _ped(5)}), \
            patch(f"{MOD}.create_event", side_effect=lambda d: ev_calls.append(d)), \
            patch(f"{MOD}.create_annotation") as ca:
        at = AppTest.from_function(_run_dialog, kwargs={"streams": [("channel", 5)]}).run()
        at.selectbox(key="rec_target").select("equipment_id").run()
        at.selectbox(key="rec_kind").select("Cleaning").run()
        at.button(key="rec_save").click().run()

    assert not at.exception
    assert len(ev_calls) == 1, f"one event; got {ev_calls}"
    payload = ev_calls[0]
    assert payload["equipment_id"] == 5
    assert payload["event_kind_id"] == 2
    arc_fks = [
        "channel_id", "equipment_id", "signal_interface_id",
        "data_acquisition_system_id", "sampling_point_id", "process_unit_id",
        "site_id", "campaign_id",
    ]
    assert [k for k in arc_fks if k in payload] == ["equipment_id"], (
        f"exactly one arc FK must be set; got {payload}"
    )
    ca.assert_not_called()


def test_heterogeneous_selection_offers_only_shared_rungs():
    """Two streams on different equipment but the same sampling point: the
    equipment rung disappears, the sampling-point rung survives."""
    with ExitStack_patches(
        peds={
            5: _ped(5, equipment=(5, "EQ5"), si=None, das=None),
            6: _ped(6, equipment=(6, "EQ6"), si=None, das=None),
        }
    ):
        at = AppTest.from_function(
            _run_dialog, kwargs={"streams": [("channel", 5), ("channel", 6)]}
        ).run()

    assert not at.exception
    # .options exposes the formatted rung labels, not the arc-FK keys.
    labels = " || ".join(at.selectbox(key="rec_target").options)
    assert "EQ5" not in labels and "EQ6" not in labels, (
        f"unshared equipment rung must not be offered; got {labels}"
    )
    assert "where it sits" in labels, "shared sampling-point rung must remain"
    assert "the series you're looking at" in labels, "the stream rung is always offered"


def test_observation_pin_checkbox_only_for_stream_rung():
    with ExitStack_patches(peds={5: _ped(5)}):
        at = AppTest.from_function(
            _run_dialog,
            kwargs={"streams": [("channel", 5)], "observation_id": 501},
        ).run()
        # Default rung is the equipment (a cause) — no pin.
        assert "rec_pin" not in [c.key for c in at.checkbox]
        at.selectbox(key="rec_target").select("__stream__").run()
        assert "rec_pin" in [c.key for c in at.checkbox], (
            "the observation pin appears only on the stream rung with a clicked point"
        )


# --- helper: patch the three vocab/pedigree loads the dialog performs ---------
from contextlib import contextmanager  # noqa: E402


@contextmanager
def ExitStack_patches(peds: dict[int, dict]):
    with patch(f"{MOD}.get_stream_pedigree", side_effect=lambda sid, **_: peds[sid]), \
            patch(f"{MOD}.list_annotation_kinds", return_value=_VERDICTS), \
            patch(f"{MOD}.list_event_kinds", return_value=_CAUSES):
        yield
