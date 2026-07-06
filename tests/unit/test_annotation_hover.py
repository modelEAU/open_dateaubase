"""Unit test for the annotation hover-tooltip formatter used in the scalar plot."""

from __future__ import annotations

from app.components.explore_scalar import _ann_hover


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
