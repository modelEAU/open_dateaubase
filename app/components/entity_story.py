"""Reusable "story" components shared by the Campaign / Equipment / Stream pages.

These render the recurring story beats — header band, KPI strip, the event
timeline (the narrative spine), location history, annotation feed, and the
freshness table — on top of the shared design system in ``theme.py``.

Pure-display beats (header, timeline, annotations, freshness) are emitted as
themed HTML; anything that contains live Streamlit widgets (KPIs, plots, maps)
uses native layout (``st.container(border=True)``) so widgets aren't trapped
inside an HTML block.
"""

from __future__ import annotations

import html
from datetime import datetime, timezone

import streamlit as st

from app.components import theme

# Event kind -> timeline node CSS modifier (see theme.py .deau-ev.<kind>).
_EVENT_KINDS = {"", "warn", "bad", "note"}


def inject() -> None:
    """Inject the shared design-system CSS. Call once near the top of a page."""
    theme.inject_css()


def relative_age(ts: str | datetime | None) -> str:
    """Human 'time since' for a UTC timestamp — '12 min ago', '3 days ago'.

    Returns '—' for missing values. Naive timestamps are treated as UTC.
    """
    if ts is None or ts == "":
        return "—"
    if isinstance(ts, str):
        try:
            ts = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        except ValueError:
            return "—"
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    secs = (datetime.now(timezone.utc) - ts).total_seconds()
    if secs < 0:
        return "just now"
    for unit, size in (("day", 86400), ("hour", 3600), ("min", 60)):
        n = int(secs // size)
        if n >= 1:
            return f"{n} {unit}{'s' if n != 1 and unit != 'min' else ''} ago"
    return "just now"


def _esc(v) -> str:
    return html.escape(str(v)) if v is not None else ""


def header(
    title: str,
    *,
    crumb: str = "",
    badges: list[tuple[str, str, bool]] | None = None,
    meta: list[tuple[str, str]] | None = None,
) -> None:
    """Render the page header band: crumb, title, status badges, meta grid.

    ``badges`` items are ``(label, tone, dot)``; ``meta`` items are ``(key, value)``.
    """
    badge_html = "".join(
        theme.badge(_esc(lbl), tone=tone, dot=dot) for lbl, tone, dot in (badges or [])
    )
    meta_html = "".join(
        f'<div><span class="k">{_esc(k)}</span>'
        f'<span class="v">{_esc(v)}</span></div>'
        for k, v in (meta or [])
    )
    st.markdown(
        f'<div class="deau-hdr">'
        f'<div class="deau-crumb">{_esc(crumb)}</div>'
        f'<div style="display:flex;align-items:center;gap:12px;flex-wrap:wrap">'
        f"<h2>{_esc(title)}</h2>{badge_html}</div>"
        f'<div class="deau-meta">{meta_html}</div></div>',
        unsafe_allow_html=True,
    )


def kpis(items: list[tuple[str, str | int]]) -> None:
    """Render a KPI strip (themed st.metric cards), max 4 per row."""
    cols = st.columns(len(items)) if items else []
    for col, (label, value) in zip(cols, items):
        col.metric(label, value)


def timeline(events: list[dict]) -> None:
    """Render the story spine. Each event: when, title, desc, kind, tag (optional)."""
    if not events:
        st.caption("No events recorded.")
        return
    rows = []
    for ev in events:
        kind = ev.get("kind", "") if ev.get("kind", "") in _EVENT_KINDS else ""
        tag = ev.get("tag")
        tag_html = (
            f'<span class="deau-badge" style="background:#EFF4FF;color:#1E40AF;'
            f'margin-left:6px;padding:1px 7px">{_esc(tag)}</span>' if tag else ""
        )
        rows.append(
            f'<div class="deau-ev {kind}"><div class="deau-node"></div>'
            f'<div class="when">{_esc(ev.get("when", ""))}</div>'
            f'<div class="ttl">{_esc(ev.get("title", ""))}{tag_html}</div>'
            f'<div class="desc">{_esc(ev.get("desc", ""))}</div></div>'
        )
    st.markdown(f'<div class="deau-tl">{"".join(rows)}</div>', unsafe_allow_html=True)


def annotation_feed(annotations: list[dict]) -> None:
    """Render an annotation log. Each item: kind, color, title, comment, start_time,
    end_time, and an optional 'anchor' label."""
    if not annotations:
        st.caption("No annotations.")
        return
    rows = []
    for a in annotations:
        color = a.get("color") or "#94A3B8"
        when = _esc(a.get("start_time", "") or "")
        if a.get("end_time"):
            when += f" → {_esc(a['end_time'])}"
        anchor = a.get("anchor")
        anchor_html = f" · {_esc(anchor)}" if anchor else ""
        badge = (
            f'<span class="deau-badge" style="background:{_esc(color)}22;'
            f'color:{_esc(color)};padding:2px 8px">{_esc(a.get("kind", "Note"))}</span>'
        )
        rows.append(
            f'<div class="deau-annot"><div style="flex:none">{badge}</div>'
            f"<div><div class='at'>{when}{anchor_html}</div>"
            f"<div class='ah'>{_esc(a.get('title') or '')}</div>"
            f"<div class='ac'>{_esc(a.get('comment') or '')}</div></div></div>"
        )
    st.markdown("".join(rows), unsafe_allow_html=True)


def freshness_table(rows: list[dict]) -> None:
    """Render last-data-point-per-stream as a plain table.

    Deliberately no traffic-light badges — freshness depends on the importer
    task, which the DB doesn't own. Just the fact: last point + relative age.
    """
    if not rows:
        st.caption("No streams.")
        return
    body = "".join(
        f"<tr><td>{_esc(r.get('label') or r.get('stream_id'))}</td>"
        f"<td class='deau-stale' style='text-align:right'>{_esc(r.get('last_point') or '—')}</td>"
        f"<td class='deau-stale' style='text-align:right'>{_esc(relative_age(r.get('last_point')))}</td></tr>"
        for r in rows
    )
    st.markdown(
        "<table class='deau-card' style='width:100%;border-collapse:collapse'>"
        f"<tbody>{body}</tbody></table>",
        unsafe_allow_html=True,
    )


if __name__ == "__main__":  # tiny self-check for the non-trivial bit
    assert relative_age(None) == "—"
    assert relative_age(datetime.now(timezone.utc)).endswith("ago") or "now" in relative_age(
        datetime.now(timezone.utc)
    )
    from datetime import timedelta

    assert "min" in relative_age(datetime.now(timezone.utc) - timedelta(minutes=12))
    assert "day" in relative_age(datetime.now(timezone.utc) - timedelta(days=3))
    assert "hour" in relative_age(datetime.now(timezone.utc) - timedelta(hours=5))
    print("entity_story self-check OK")
