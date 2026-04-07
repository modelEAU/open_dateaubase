"""Measurement Axes (Binning) CRUD page."""

from __future__ import annotations

import sys
from pathlib import Path

_project_root = str(Path(__file__).resolve().parent.parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

import streamlit as st
import pandas as pd

from app.api_client import (
    APIError,
    create_binning_axis,
    delete_binning_axis,
    get_binning_axis,
    list_binning_axes,
    list_units_lookup,
    update_binning_axis,
)
from app.auth import get_current_user, logout, require_auth

require_auth()

with st.sidebar:
    user = get_current_user()
    if user:
        st.write(f"Logged in as: **{user['name']}**")
    if st.button("Sign out"):
        logout()

st.title("Measurement Axes (Binning)")
st.markdown(
    """
    Define the bin boundaries for spectral or distribution channels.
    Each axis describes the measurement scale (e.g., wavelength 200–700nm or particle size 0.5–500µm).
    Vector channels use one axis; matrix channels use two.
    """
)

# Load data
try:
    with st.spinner("Loading..."):
        axes = list_binning_axes()
        units = list_units_lookup()
except APIError as e:
    st.error(f"Cannot load data: {e.message}")
    st.stop()

# Prepare units dropdown options
unit_options = {u["unit_id"]: u["unit"] for u in units}

# Show axes table
if axes:
    df = pd.DataFrame(axes)
    df_display = df[["name", "unit_name", "number_of_bins", "description"]].copy()
    df_display.columns = ["Name", "Unit", "Bins", "Description"]

    event = st.dataframe(
        df_display,
        use_container_width=True,
        on_select="rerun",
        selection_mode="single-row",
        key="axes_table",
    )

    selected_rows = event.selection.get("rows", [])
    selected_axis_id = None
    if selected_rows:
        selected_idx = selected_rows[0]
        # Validate index is within bounds (data may have changed since selection)
        if 0 <= selected_idx < len(df):
            selected_axis_id = df.iloc[selected_idx]["value_binning_axis_id"]

# Action buttons
col1, col2, col3 = st.columns([1, 1, 1])
with col1:
    if st.button("➕ New Axis", type="primary"):
        st.session_state["show_new_axis_dialog"] = True
with col2:
    edit_disabled = selected_axis_id is None
    if st.button("✏️ Edit Axis", disabled=edit_disabled):
        st.session_state["show_edit_axis_dialog"] = True
        st.session_state["axis_to_edit"] = selected_axis_id
with col3:
    delete_disabled = selected_axis_id is None
    if st.button("🗑️ Delete Axis", disabled=delete_disabled, type="secondary"):
        st.session_state["show_delete_confirm"] = True
        st.session_state["axis_to_delete"] = selected_axis_id


@st.dialog("Define New Axis")
def new_axis_dialog():
    """Dialog for creating a new measurement axis."""
    name = st.text_input("Name *", placeholder="e.g., UV-Vis 200-700nm 2nm")
    description = st.text_area("Description", placeholder="Optional description")

    unit_id = st.selectbox(
        "Unit *",
        options=list(unit_options.keys()),
        format_func=lambda x: unit_options.get(x, "Unknown"),
    )

    st.markdown("### Bin Definition")
    bin_mode = st.radio(
        "Mode",
        options=["generate", "paste"],
        format_func=lambda x: (
            "Generate evenly-spaced bins" if x == "generate" else "Paste bin boundaries"
        ),
    )

    bins = []

    if bin_mode == "generate":
        col1, col2, col3 = st.columns(3)
        with col1:
            min_val = st.number_input("Min value", value=0.0)
        with col2:
            max_val = st.number_input("Max value", value=100.0)
        with col3:
            n_bins = st.number_input("Number of bins", min_value=1, value=10, step=1)

        if n_bins > 0 and max_val > min_val:
            step = (max_val - min_val) / n_bins
            bins = [
                {
                    "bin_index": i,
                    "lower_bound": min_val + i * step,
                    "upper_bound": min_val + (i + 1) * step,
                }
                for i in range(int(n_bins))
            ]

            # Show preview
            st.markdown("#### Preview")
            preview_df = pd.DataFrame(bins)
            st.dataframe(preview_df, use_container_width=True, hide_index=True)

    else:  # paste mode
        paste_text = st.text_area(
            "Paste comma-separated upper bounds",
            placeholder="e.g., 1,2,5,10,20,50,100",
            help="Lower bound of each bin = upper bound of previous (first bin starts at 0)",
        )

        if paste_text.strip():
            try:
                upper_bounds = [
                    float(x.strip()) for x in paste_text.split(",") if x.strip()
                ]
                if len(upper_bounds) > 0:
                    lower_bound = 0.0
                    bins = []
                    for i, upper in enumerate(upper_bounds):
                        bins.append(
                            {
                                "bin_index": i,
                                "lower_bound": lower_bound,
                                "upper_bound": upper,
                            }
                        )
                        lower_bound = upper

                    st.markdown(f"**{len(bins)} bins will be created**")
                    preview_df = pd.DataFrame(bins)
                    st.dataframe(preview_df, use_container_width=True, hide_index=True)
            except ValueError:
                st.error("Invalid input. Please enter comma-separated numbers.")

    # Submit button
    st.markdown("---")
    submit_col1, submit_col2 = st.columns([1, 1])
    with submit_col1:
        if st.button("Cancel"):
            st.session_state["show_new_axis_dialog"] = False
            st.rerun()
    with submit_col2:
        if st.button(
            "Create Axis", type="primary", disabled=not (name and unit_id and bins)
        ):
            data = {
                "name": name,
                "description": description if description else None,
                "unit_id": unit_id,
                "bins": bins,
            }
            try:
                result = create_binning_axis(data)
                st.success(f"Axis created with {len(bins)} bins!")
                st.session_state["show_new_axis_dialog"] = False
                st.rerun()
            except APIError as e:
                st.error(f"Failed to create axis: {e.message}")


@st.dialog("Edit Axis")
def edit_axis_dialog():
    """Dialog for editing an existing measurement axis."""
    axis_id = st.session_state.get("axis_to_edit")
    if axis_id is None:
        st.error("No axis selected")
        return

    # Find current values from the already-loaded list
    current = next((a for a in axes if a["value_binning_axis_id"] == axis_id), None)
    if current is None:
        st.error("Axis not found")
        return

    name = st.text_input("Name *", value=current["name"])
    description = st.text_area(
        "Description", value=current.get("description") or ""
    )

    unit_id = st.selectbox(
        "Unit *",
        options=list(unit_options.keys()),
        index=list(unit_options.keys()).index(current["unit_id"])
        if current["unit_id"] in unit_options
        else 0,
        format_func=lambda x: unit_options.get(x, "Unknown"),
    )

    st.markdown("### Bin Boundaries")
    st.caption(f"Current: {current['number_of_bins']} bins")
    replace_bins = st.checkbox("Replace bin boundaries")

    new_bins: list | None = None

    if replace_bins:
        bin_mode = st.radio(
            "Mode",
            options=["generate", "paste"],
            format_func=lambda x: (
                "Generate evenly-spaced bins" if x == "generate" else "Paste bin boundaries"
            ),
        )

        if bin_mode == "generate":
            c1, c2, c3 = st.columns(3)
            with c1:
                min_val = st.number_input("Min value", value=0.0, key="edit_min")
            with c2:
                max_val = st.number_input("Max value", value=100.0, key="edit_max")
            with c3:
                n_bins = st.number_input(
                    "Number of bins", min_value=1, value=10, step=1, key="edit_n"
                )

            if n_bins > 0 and max_val > min_val:
                step = (max_val - min_val) / n_bins
                new_bins = [
                    {
                        "bin_index": i,
                        "lower_bound": min_val + i * step,
                        "upper_bound": min_val + (i + 1) * step,
                    }
                    for i in range(int(n_bins))
                ]
                st.markdown("#### Preview")
                st.dataframe(pd.DataFrame(new_bins), use_container_width=True, hide_index=True)

        else:
            paste_text = st.text_area(
                "Paste comma-separated upper bounds",
                placeholder="e.g., 1,2,5,10,20,50,100",
                help="Lower bound of each bin = upper bound of previous (first bin starts at 0)",
                key="edit_paste",
            )
            if paste_text.strip():
                try:
                    upper_bounds = [
                        float(x.strip()) for x in paste_text.split(",") if x.strip()
                    ]
                    if upper_bounds:
                        lower_bound = 0.0
                        new_bins = []
                        for i, upper in enumerate(upper_bounds):
                            new_bins.append(
                                {
                                    "bin_index": i,
                                    "lower_bound": lower_bound,
                                    "upper_bound": upper,
                                }
                            )
                            lower_bound = upper
                        st.markdown(f"**{len(new_bins)} bins will be created**")
                        st.dataframe(
                            pd.DataFrame(new_bins), use_container_width=True, hide_index=True
                        )
                except ValueError:
                    st.error("Invalid input. Please enter comma-separated numbers.")
                    new_bins = None

    st.markdown("---")
    submit_col1, submit_col2 = st.columns([1, 1])
    with submit_col1:
        if st.button("Cancel"):
            st.session_state["show_edit_axis_dialog"] = False
            st.session_state["axis_to_edit"] = None
            st.rerun()
    with submit_col2:
        save_disabled = not name or (replace_bins and new_bins is None)
        if st.button("Save Changes", type="primary", disabled=save_disabled):
            payload: dict = {}
            if name != current["name"]:
                payload["name"] = name
            new_desc = description if description else None
            if new_desc != current.get("description"):
                payload["description"] = new_desc
            if unit_id != current["unit_id"]:
                payload["unit_id"] = unit_id
            if replace_bins and new_bins is not None:
                payload["bins"] = new_bins

            if not payload:
                st.info("No changes to save.")
                return

            try:
                update_binning_axis(axis_id, payload)
                st.success("Axis updated successfully!")
                st.session_state["show_edit_axis_dialog"] = False
                st.session_state["axis_to_edit"] = None
                st.rerun()
            except APIError as e:
                st.error(f"Failed to update axis: {e.message}")


@st.dialog("Confirm Delete")
def delete_confirm_dialog():
    """Dialog for confirming axis deletion."""
    axis_id = st.session_state.get("axis_to_delete")
    if axis_id is None:
        st.error("No axis selected")
        return

    # Get axis details for the message
    axis = next(
        (a for a in axes if a["value_binning_axis_id"] == axis_id),
        None,
    )
    axis_name = axis["name"] if axis else f"ID {axis_id}"

    st.warning(
        f"This will delete the axis '{axis_name}' and all its bins. "
        "Channels using this axis will no longer work. Continue?"
    )

    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("Cancel"):
            st.session_state["show_delete_confirm"] = False
            st.session_state["axis_to_delete"] = None
            st.rerun()
    with col2:
        if st.button("Yes, Delete", type="primary"):
            try:
                delete_binning_axis(axis_id)
                st.success(f"Axis '{axis_name}' deleted.")
                st.session_state["show_delete_confirm"] = False
                st.session_state["axis_to_delete"] = None
                st.rerun()
            except APIError as e:
                if e.status_code == 400:
                    st.error(f"Cannot delete: {e.message}")
                else:
                    st.error(f"Failed to delete: {e.message}")


# Show detail panel when an axis is selected
if selected_axis_id:
    with st.expander("Bin Details", expanded=True):
        try:
            axis_detail = get_binning_axis(selected_axis_id)
            if axis_detail and axis_detail.get("bins"):
                bins_df = pd.DataFrame(axis_detail["bins"])
                st.dataframe(bins_df, use_container_width=True, hide_index=True)
                st.caption(f"Total bins: {len(axis_detail['bins'])}")
            else:
                st.info("No bin details available.")
        except APIError as e:
            st.error(f"Failed to load axis details: {e.message}")

# Render dialogs
if st.session_state.get("show_new_axis_dialog"):
    new_axis_dialog()

if st.session_state.get("show_edit_axis_dialog"):
    edit_axis_dialog()

if st.session_state.get("show_delete_confirm"):
    delete_confirm_dialog()
