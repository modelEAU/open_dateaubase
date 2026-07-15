"""Audit log page — who did what and when.

Accessible from the sidebar navigation once authenticated.
Home.py handles auth guard and sidebar rendering; this file only renders page content.
"""

from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

_project_root = str(Path(__file__).resolve().parents[2])
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

import streamlit as st

from app.api_client import APIError, get_audit_logs
from app.components.labels import ALL_LABEL

_LOCAL_TZ = datetime.now().astimezone().tzinfo  # type: ignore[attr-defined]

st.title("Audit Log")
st.caption("Complete history of all actions performed in the system — who did what, and when.")

# ---------------------------------------------------------------------------
# Action badge colours
# ---------------------------------------------------------------------------
_ACTION_BADGE = {
    "SIGNUP": "🟢 SIGNUP",
    "LOGIN":  "🔵 LOGIN",
    "CREATE": "🟡 CREATE",
    "UPDATE": "🟠 UPDATE",
    "DELETE": "🔴 DELETE",
}


def _badge(action: str) -> str:
    return _ACTION_BADGE.get(action, f"⚪ {action}")


# ---------------------------------------------------------------------------
# Summary metrics
# ---------------------------------------------------------------------------
try:
    overview = get_audit_logs(limit=500, offset=0)
except APIError as e:
    st.error(f"Cannot load audit log: {e.message}")
    st.stop()

all_items = overview["items"]
total_all  = overview["total"]

if all_items:
    from collections import Counter
    action_counts = Counter(e["action"] for e in all_items)
    user_counts   = Counter(e["full_name"] or "Anonymous" for e in all_items)

    st.markdown("### Activity overview")
    cols = st.columns(len(action_counts) or 1)
    for col, (action, count) in zip(cols, action_counts.items()):
        col.metric(_badge(action), count)
    st.divider()

# ---------------------------------------------------------------------------
# Filters
# ---------------------------------------------------------------------------
st.markdown("### Filter")
f_col1, f_col2, f_col3, f_col4 = st.columns(4)

with f_col1:
    action_filter = st.selectbox(
        "Action",
        [ALL_LABEL, "SIGNUP", "LOGIN", "CREATE", "UPDATE", "DELETE"],
        help="Show only entries where a user performed this kind of action.",
    )
with f_col2:
    resource_filter = st.text_input(
        "Resource type",
        placeholder="e.g. Site, Campaign …",
        help="Show only entries touching this kind of entity. Matches the table name.",
    )
with f_col3:
    days_back = st.number_input(
        "Last N days",
        min_value=1,
        max_value=730,
        value=30,
        help="How far back to search the log.",
    )
with f_col4:
    author_filter = st.text_input(
        "Author (name or email)",
        placeholder="optional",
        help="Show only entries made by this user.",
    )

now     = datetime.now(timezone.utc)
from_dt = (now - timedelta(days=int(days_back))).isoformat()

# ---------------------------------------------------------------------------
# Pagination state
# ---------------------------------------------------------------------------
PAGE_SIZE = 25

if "audit_offset" not in st.session_state:
    st.session_state["audit_offset"] = 0

# Reset to page 1 when filters change
filter_key = (action_filter, resource_filter, days_back, author_filter)
if st.session_state.get("_audit_filter_key") != filter_key:
    st.session_state["_audit_filter_key"] = filter_key
    st.session_state["audit_offset"] = 0

offset = st.session_state["audit_offset"]

# ---------------------------------------------------------------------------
# Fetch filtered page
# ---------------------------------------------------------------------------
try:
    data = get_audit_logs(
        action=action_filter if action_filter != ALL_LABEL else None,
        resource_type=resource_filter or None,
        from_dt=from_dt,
        limit=PAGE_SIZE,
        offset=offset,
    )
except APIError as e:
    st.error(f"Cannot load audit log: {e.message}")
    st.stop()

total = data["total"]
items = data["items"]

# Client-side author filter (API doesn't expose it yet)
if author_filter:
    needle = author_filter.lower()
    items = [
        e for e in items
        if needle in (e.get("full_name") or "").lower()
        or needle in (e.get("email") or "").lower()
    ]

# ---------------------------------------------------------------------------
# Results header
# ---------------------------------------------------------------------------
st.markdown(f"### Results — {total} entries")

if not items:
    st.info("No entries match the current filters.")
    st.stop()

# ---------------------------------------------------------------------------
# Table
# ---------------------------------------------------------------------------
hdr = st.columns([2, 2.5, 1.5, 1.8, 1.2])
hdr[0].markdown("**When (local)**")
hdr[1].markdown("**Author**")
hdr[2].markdown("**Action**")
hdr[3].markdown("**Resource**")
hdr[4].markdown("**Record ID**")
st.divider()

for entry in items:
    ts: datetime | str = entry["timestamp"]
    if isinstance(ts, str):
        ts = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    if isinstance(ts, datetime):
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        ts = ts.astimezone(_LOCAL_TZ)

    full_name  = entry.get("full_name") or "—"
    email      = entry.get("email") or ""
    action     = entry["action"]
    resource   = entry["resource_type"]
    record_id  = entry.get("resource_id") or "—"
    details    = entry.get("details")

    row = st.columns([2, 2.5, 1.5, 1.8, 1.2])
    row[0].write(ts.strftime("%Y-%m-%d %H:%M") if hasattr(ts, "strftime") else str(ts))

    row[1].write(f"**{full_name}**")
    if email:
        row[1].caption(email)

    row[2].write(_badge(action))
    row[3].write(resource)
    row[4].write(f"`{record_id}`")

    if details:
        with st.expander(f"Details — {action} on {resource} {record_id}"):
            st.json(details)

    st.divider()

# ---------------------------------------------------------------------------
# Pagination controls
# ---------------------------------------------------------------------------
p_prev, p_info, p_next = st.columns([1, 4, 1])
current_page = offset // PAGE_SIZE + 1
total_pages  = max(1, -(-total // PAGE_SIZE))
p_info.caption(f"Page {current_page} of {total_pages}  ({total} total entries)")

if p_prev.button("← Prev", disabled=offset == 0):
    st.session_state["audit_offset"] = max(0, offset - PAGE_SIZE)
    st.rerun()

if p_next.button("Next →", disabled=offset + PAGE_SIZE >= total):
    st.session_state["audit_offset"] = offset + PAGE_SIZE
    st.rerun()
