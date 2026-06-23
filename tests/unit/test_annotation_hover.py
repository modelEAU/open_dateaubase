"""Unit test for the annotation hover-tooltip formatter used in the scalar plot."""

from __future__ import annotations

from unittest.mock import patch

from app.components.explore_scalar import _ann_hover, _build_scalar_figure


def test_hover_includes_kind_title_comment_and_span():
    h = _ann_hover({
        "type": {"name": "Fault"},
        "title": "Lamp failure",
        "comment": "Spectro offline",
        "start_time": "2026-06-18T00:00:00",
        "end_time": "2026-06-20T00:00:00",
    })
    assert "Fault" in h and "Lamp failure" in h
    assert "Spectro offline" in h
    assert "2026-06-18T00:00:00 → 2026-06-20T00:00:00" in h


def test_hover_point_annotation_has_no_arrow_span():
    h = _ann_hover({
        "type": {"name": "Note"},
        "title": "",
        "comment": "",
        "start_time": "2026-06-18T00:00:00",
        "end_time": None,
    })
    assert "Note" in h
    assert "→" not in h          # point annotation: single timestamp, no range
    assert "2026-06-18T00:00:00" in h


def test_hover_handles_missing_type():
    h = _ann_hover({"start_time": "2026-06-18T00:00:00"})
    assert "Annotation" in h     # falls back to a generic kind label


_MOD = "app.components.explore_scalar"


def test_figure_annotation_marker_carries_hovertext():
    """The annotation overlay's [ref] label must expose hovertext on the built
    figure, so it's readable on hover in the plot (Campaign Story + Explore)."""
    ts = {"data": [
        {"timestamp": "2026-06-18T00:00:00", "value": 1.0, "quality_code": 1, "observation_id": 1},
        {"timestamp": "2026-06-19T00:00:00", "value": 2.0, "quality_code": 1, "observation_id": 2},
    ]}
    ann = [{
        "start_time": "2026-06-18T00:00:00", "end_time": None,
        "type": {"name": "Fault", "color": "#DC2626"},
        "title": "Lamp failure", "comment": "Spectro offline",
    }]
    with (
        patch(f"{_MOD}._load_timeseries", return_value=ts),
        patch(f"{_MOD}._load_annotations", return_value=ann),
        patch(f"{_MOD}._load_equipment_events", return_value=[]),
    ):
        fig, rows = _build_scalar_figure([101], {101: {"parameter_name": "pH"}}, "extract")

    hovertexts = [a.hovertext for a in fig.layout.annotations if a.hovertext]
    assert any("Fault" in h and "Lamp failure" in h for h in hovertexts), (
        f"annotation marker missing hovertext; got {hovertexts}"
    )
