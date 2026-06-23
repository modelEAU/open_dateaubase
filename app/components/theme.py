"""Shared visual design system for the datEAUbase app.

Native Streamlit theming (colors, font) lives in ``.streamlit/config.toml`` and
applies to every page automatically. This module adds the few things the native
theme can't express — status badges, KPI cards, the story timeline, section
cards — as a one-shot CSS injection plus small HTML helpers.

Design rationale and the full token list are documented in
``docs/design-system.md``. Keep this file and that doc in sync.
"""

from __future__ import annotations

import streamlit as st

# --- Design tokens (mirror docs/design-system.md and .streamlit/config.toml) ---
PRIMARY = "#1E40AF"
ACCENT = "#D97706"
SUB = "#475569"          # secondary text
MUTED = "#E9EEF6"
BORDER = "#DBEAFE"
OK = "#16A34A"
WARN = "#D97706"
BAD = "#DC2626"

# Status tone -> (background, foreground, dot color) for badges.
_TONES = {
    "ok": ("#E7F6EC", "#15803D", OK),
    "warn": ("#FEF3E2", "#B45309", WARN),
    "bad": ("#FDE8E8", "#B91C1C", BAD),
    "blue": ("#EFF4FF", PRIMARY, PRIMARY),
    "amber": ("#FEF3E2", "#B45309", ACCENT),
    "grey": (MUTED, SUB, "#94A3B8"),
}

_CSS = """
<style>
/* tabular figures everywhere data is shown */
[data-testid="stMetricValue"], .deau-num, .deau-card td { font-variant-numeric: tabular-nums; }

/* KPI metric cards: give Streamlit metrics the dashboard card treatment */
[data-testid="stMetric"]{
  background:#FFFFFF;border:1px solid #DBEAFE;border-radius:10px;
  padding:14px 16px;box-shadow:0 1px 2px rgba(15,23,42,.06),0 1px 3px rgba(15,23,42,.08);
}
[data-testid="stMetricLabel"]{ color:#475569; }

/* Section card (header + body) */
.deau-card{background:#FFFFFF;border:1px solid #DBEAFE;border-radius:10px;
  box-shadow:0 1px 2px rgba(15,23,42,.06),0 1px 3px rgba(15,23,42,.08);
  overflow:hidden;margin-bottom:6px;}
.deau-card .deau-ch{display:flex;align-items:center;justify-content:space-between;
  padding:11px 16px;border-bottom:1px solid #E9EEF6;}
.deau-card .deau-ch h3{margin:0;font-size:15px;font-weight:600;}
.deau-card .deau-ch .deau-sub{font-size:12px;color:#475569;}
.deau-card .deau-cb{padding:14px 16px;}

/* Status / category badge */
.deau-badge{display:inline-flex;align-items:center;gap:6px;font-size:12px;font-weight:600;
  padding:3px 10px;border-radius:999px;line-height:1.4;}
.deau-badge .deau-dot{width:8px;height:8px;border-radius:50%;}

/* Header band */
.deau-hdr{background:#FFFFFF;border:1px solid #DBEAFE;border-radius:10px;padding:18px 20px;
  box-shadow:0 1px 2px rgba(15,23,42,.06),0 1px 3px rgba(15,23,42,.08);margin-bottom:6px;}
.deau-hdr .deau-crumb{font-size:12.5px;color:#475569;margin-bottom:6px;}
.deau-hdr h2{margin:0;font-size:22px;font-weight:600;letter-spacing:-.3px;}
.deau-meta{display:flex;gap:24px;flex-wrap:wrap;margin-top:12px;font-size:13.5px;}
.deau-meta .k{display:block;color:#475569;font-size:11px;text-transform:uppercase;letter-spacing:.05em;}
.deau-meta .v{font-weight:500;}

/* Story timeline (the spine) */
.deau-tl{position:relative;padding-left:26px;}
.deau-tl:before{content:"";position:absolute;left:7px;top:4px;bottom:4px;width:2px;background:#DBEAFE;}
.deau-ev{position:relative;padding:0 0 16px;}
.deau-ev:last-child{padding-bottom:0;}
.deau-ev .deau-node{position:absolute;left:-26px;top:2px;width:16px;height:16px;border-radius:50%;
  background:#fff;border:2px solid #1E40AF;}
.deau-ev.warn .deau-node{border-color:#D97706;}
.deau-ev.bad .deau-node{border-color:#DC2626;}
.deau-ev.note .deau-node{border-color:#D97706;}
.deau-ev .when{font-size:12px;color:#475569;font-family:ui-monospace,monospace;}
.deau-ev .ttl{font-weight:600;font-size:14px;margin:1px 0;}
.deau-ev .desc{font-size:13px;color:#475569;}

/* Annotation feed row */
.deau-annot{display:flex;gap:12px;padding:10px 0;border-bottom:1px solid #F1F5F9;}
.deau-annot:last-child{border:none;}
.deau-annot .at{font-size:11px;color:#475569;font-family:ui-monospace,monospace;}
.deau-annot .ah{font-weight:600;font-size:13.5px;}
.deau-annot .ac{font-size:13px;color:#475569;}
.deau-stale{color:#475569;font-family:ui-monospace,monospace;}
</style>
"""


def inject_css() -> None:
    """Inject the shared component CSS once per page run."""
    st.markdown(_CSS, unsafe_allow_html=True)


def badge(label: str, tone: str = "grey", dot: bool = False) -> str:
    """Return an inline HTML badge. ``tone`` in ok/warn/bad/blue/amber/grey.

    With ``dot=True`` the status is conveyed by a colored dot *and* the text
    label (never color alone — accessibility rule color-not-only).
    """
    bg, fg, dot_color = _TONES.get(tone, _TONES["grey"])
    dot_html = (
        f'<span class="deau-dot" style="background:{dot_color}"></span>' if dot else ""
    )
    return (
        f'<span class="deau-badge" style="background:{bg};color:{fg}">'
        f"{dot_html}{label}</span>"
    )
