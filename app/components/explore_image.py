"""Image value-type lightbox for the Explore page.

The full-size image viewer dialog (the "lightbox"), extracted from explore.py
(Phase 5 follow-up). Self-contained: given a (kind, id) trace + timestamp it
fetches the full-resolution bytes and renders them, with a sensor-only affordance
to start an image annotation (signalled via session-state flags the page reads).

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
    annotation_types: list[dict],
) -> None:
    kind, t_id = trace
    try:
        st.image(get_image_file(observation_id), caption=timestamp, use_container_width=True)
    except APIError as e:
        st.warning(f"Could not load full image: {e.message}")

    # Image-level annotation is sensor-only for now. Lab AnalysisSeries traces
    # are fully annotatable from the scalar chart view (range + point, via
    # /analysis-series/{id}/annotations); only this per-image affordance remains
    # channel-only.
    if kind == "channel":
        st.divider()
        if st.button("Create Annotation for this image"):
            st.session_state._show_annotation_dialog = True
            st.session_state._ann_channel_id = t_id
            st.session_state._ann_start = timestamp
            st.session_state._ann_end = timestamp
            st.rerun()
