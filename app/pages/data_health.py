"""Data Health — broken-link reports (consistency audit F5, F11).

Surfaces the reconciling views added in schema 2.1.0:
  - Unlinked channels (F5): ingested channels carrying data but never wired to
    equipment, so their observations resolve to no equipment / no location.
  - Live references to deactivated parents (F11): active wiring rows still
    pointing at a SignalInterface/SignalInterfacePort that was soft-deleted.
"""

from __future__ import annotations

import sys
from pathlib import Path

_project_root = str(Path(__file__).resolve().parent.parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

import pandas as pd
import streamlit as st

from app.api_client import (
    APIError,
    get_inactive_parent_references,
    get_unlinked_channels,
)

st.title("Data Health")
st.caption(
    "Reconciling reports for broken links in the equipment/wiring model. "
    "An empty section means that check is clean."
)

try:
    with st.spinner("Loading…"):
        unlinked = get_unlinked_channels()
        inactive_refs = get_inactive_parent_references()
except APIError as e:
    st.error(f"Could not load data-health reports: {e.message}")
    st.stop()

# --- F5: channels that need wiring -----------------------------------------
st.subheader("Channels needing wiring")
if unlinked:
    st.warning(
        f"{len(unlinked)} channel(s) carry observations but have no active "
        "equipment wiring — their data resolves to no equipment and no sampling "
        "point. Wire them via **Move a sensor** / the field-system wizard."
    )
    st.dataframe(pd.DataFrame(unlinked), use_container_width=True)
else:
    st.success("All channels with data are wired to equipment.")

# --- F11: live references to deactivated parents ---------------------------
st.subheader("Live references to deactivated interfaces/ports")
if inactive_refs:
    st.warning(
        f"{len(inactive_refs)} active wiring row(s) still point at a "
        "deactivated SignalInterface/SignalInterfacePort. They keep resolving "
        "as if active — rewire the equipment or reactivate the parent."
    )
    st.dataframe(pd.DataFrame(inactive_refs), use_container_width=True)
else:
    st.success("No active wiring points at a deactivated interface or port.")
