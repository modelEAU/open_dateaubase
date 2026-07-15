"""Image value-type lightbox for the Explore page.

The full-size image viewer dialog (the "lightbox"), extracted from explore.py
(Phase 5 follow-up). Self-contained: given a (kind, id) trace + timestamp it
fetches the full-resolution bytes and renders them, with an affordance to
annotate that image (signalled via session-state flags the page reads).

The image *gallery* (_render_image_view) stays in explore.py with the other
_render_*_view orchestrators — they are a cohesive cluster and share the
annotation/equipment dialogs. Re-exported from explore.py.
"""

from __future__ import annotations

import streamlit as st

from app.api_client import APIError, get_image_file


@st.dialog("Image viewer", width="large")
def _image_viewer_dialog(
    trace: tuple[str, int],
    observation_id: int,
    timestamp: str,
) -> None:
    kind, t_id = trace
    try:
        st.image(get_image_file(observation_id), caption=timestamp, use_container_width=True)
    except APIError as e:
        st.warning(f"Could not load full image: {e.message}")

    st.divider()
    # Streamlit forbids a dialog inside a dialog, so this hands the request to the
    # page via session state; explore.py opens the annotation dialog on the rerun.
    # The image is its observation, so the annotation is pinned to that id — a lab
    # sample's replicates all share the collection timestamp.
    if st.button("Create Annotation for this image"):
        st.session_state._show_annotation_dialog = True
        st.session_state._ann_trace = (kind, t_id)
        st.session_state._ann_obs_id = observation_id
        st.session_state._ann_start = timestamp
        st.session_state._ann_end = None
        st.rerun()
