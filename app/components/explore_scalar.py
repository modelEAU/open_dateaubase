"""Scalar-view annotation helper for the Explore page.

The scalar chart itself is built by ``explore_echarts.build_scalar_echarts_option``;
this module keeps the annotation hover-text formatter, which is pure and shared.
"""

from __future__ import annotations


def _ann_hover(ann: dict) -> str:
    """Build the hover tooltip text for an annotation overlay marker."""
    kind = (ann.get("type", {}) or {}).get("name") or "Annotation"
    title = ann.get("title") or ""
    comment = ann.get("comment") or ""
    start = ann.get("start_time") or ""
    end = ann.get("end_time")
    span = f"{start} → {end}" if end else start
    parts = [f"<b>{kind}</b>" + (f": {title}" if title else "")]
    if comment:
        parts.append(comment)
    if span:
        parts.append(f"<i>{span}</i>")
    return "<br>".join(parts)
