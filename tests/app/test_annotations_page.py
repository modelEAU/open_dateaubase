"""Annotations CRUD page coverage using streamlit.testing.v1.AppTest.

Guards the Slice 15 migration: the page's create handler must call the new
stream-anchored create_annotation(stream_id=…, data=…, anchor_kind="channel")
signature, mapping the selected channel_id to the Stream_ID. The page only
selects sensor channels, so anchor_kind is always "channel".
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

PAGE = str(Path(__file__).parent.parent.parent / "app" / "pages" / "annotations.py")
MOD = "app.pages.annotations"

_CHANNELS = [
    {"channel_id": 7, "parameter_name": "TSS", "equipment_identifier": "EQ7"},
]


def test_create_handler_uses_stream_anchored_signature():
    captured: dict = {}

    def _capture_create(*args, **kwargs):
        captured["args"] = args
        captured["kwargs"] = kwargs
        return {"annotation_id": 1}

    with (
        patch(f"{MOD}.list_channels", return_value={"items": _CHANNELS}),
        patch(f"{MOD}.list_annotations", return_value={"items": []}),
        patch(f"{MOD}.create_annotation", side_effect=_capture_create),
    ):
        at = AppTest.from_file(PAGE).run()
        assert not at.exception
        # Invoke the handler directly with a channel-keyed payload (what the
        # create form emits).
        from app.pages import annotations as page

        result = page.handle_create_annotation(
            {
                "channel_id": 7,
                "annotation_type": 3,
                "start_time": "2026-05-01T00:00:00",
            }
        )

    assert result is True
    assert captured, "create_annotation was not called"
    kwargs = captured["kwargs"]
    assert kwargs.get("stream_id") == 7, (
        f"expected stream_id=7 (channel's Stream_ID); got {captured}"
    )
    assert kwargs.get("anchor_kind") == "channel", (
        f"expected anchor_kind='channel' for a sensor selection; got {captured}"
    )
    assert isinstance(kwargs.get("data"), dict), (
        f"expected the payload passed as data=…; got {captured}"
    )
    # channel_id must be consumed as the anchor, not left in the body payload.
    assert "channel_id" not in kwargs["data"], (
        f"channel_id should be popped into stream_id, not sent in data; got {captured}"
    )
