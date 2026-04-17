"""Measurement Axes (Binning) CRUD page."""

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
    create_binning_axis,
    delete_binning_axis,
    get_binning_axis,
    list_binning_axes,
    list_units_lookup,
    update_binning_axis,
)



st.title("Measurement Axes (Binning)")
st.markdown(
    """
    Define the bin structure for spectral or distribution channels.
    Each axis describes the measurement scale (e.g., wavelength 200–700 nm or particle size 0.5–500 µm).
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

unit_options = {u["unit_id"]: u["unit"] for u in units}

BIN_MODE_OPTIONS = ["interval", "interval_with_nominal", "nominal"]
BIN_MODE_LABELS = {
    "interval": "Interval — lower + upper bounds",
    "interval_with_nominal": "Interval with nominal — bounds + center value",
    "nominal": "Nominal — single value per bin",
}


def _bin_mode_columns(mode: str) -> list[str]:
    if mode == "interval":
        return ["lower_bound", "upper_bound"]
    if mode == "interval_with_nominal":
        return ["lower_bound", "upper_bound", "nominal_value"]
    return ["nominal_value"]


def _editor_column_config(mode: str) -> dict:
    cfg: dict = {}
    if mode in ("interval", "interval_with_nominal"):
        cfg["lower_bound"] = st.column_config.NumberColumn("Lower Bound", required=True)
        cfg["upper_bound"] = st.column_config.NumberColumn("Upper Bound", required=True)
    if mode in ("interval_with_nominal", "nominal"):
        cfg["nominal_value"] = st.column_config.NumberColumn("Nominal Value", required=True)
    return cfg


def _empty_bins_df(mode: str, n: int) -> pd.DataFrame:
    cols = _bin_mode_columns(mode)
    return pd.DataFrame({c: [None] * n for c in cols})


def _bins_from_editor(df: pd.DataFrame, mode: str) -> list[dict]:
    """Convert data_editor DataFrame to API bin dicts, filtering incomplete rows."""
    bins = []
    cols = _bin_mode_columns(mode)
    for i, row in enumerate(df.itertuples(index=False)):
        vals = {c: getattr(row, c, None) for c in cols}
        # Skip entirely empty rows
        if all(v is None or (isinstance(v, float) and pd.isna(v)) for v in vals.values()):
            continue
        entry: dict = {"bin_index": i}
        for c in cols:
            v = vals[c]
            entry[c] = float(v) if v is not None and not (isinstance(v, float) and pd.isna(v)) else None
        bins.append(entry)
    return bins


def _bins_to_df(bins: list[dict], mode: str) -> pd.DataFrame:
    """Convert API bin dicts to a DataFrame for data_editor."""
    cols = _bin_mode_columns(mode)
    rows = []
    for b in sorted(bins, key=lambda x: x["bin_index"]):
        rows.append({c: b.get(c) for c in cols})
    return pd.DataFrame(rows) if rows else _empty_bins_df(mode, 5)


# Show axes table
if axes:
    df = pd.DataFrame(axes)
    df_display = df[["name", "bin_mode", "unit_name", "number_of_bins", "description"]].copy()
    df_display.columns = ["Name", "Bin Mode", "Unit", "Bins", "Description"]

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
        if 0 <= selected_idx < len(df):
            selected_axis_id = df.iloc[selected_idx]["value_binning_axis_id"]
else:
    selected_axis_id = None
    st.info("No axes defined yet.")

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

    st.markdown("### Bin Mode")
    bin_mode = st.radio(
        "How are bins defined?",
        options=BIN_MODE_OPTIONS,
        format_func=lambda x: BIN_MODE_LABELS[x],
        horizontal=True,
    )

    st.markdown("### Bins")
    n_initial = st.number_input(
        "Initial number of rows", min_value=1, max_value=1000, value=10, step=1
    )

    init_key = f"new_axis_bins_{bin_mode}"
    if init_key not in st.session_state:
        st.session_state[init_key] = _empty_bins_df(bin_mode, int(n_initial))

    edited_df = st.data_editor(
        st.session_state[init_key],
        column_config=_editor_column_config(bin_mode),
        num_rows="dynamic",
        use_container_width=True,
        key=f"new_axis_editor_{bin_mode}",
    )

    bins = _bins_from_editor(edited_df, bin_mode)
    if bins:
        st.caption(f"{len(bins)} valid bin(s) ready to submit.")

    st.markdown("---")
    submit_col1, submit_col2 = st.columns([1, 1])
    with submit_col1:
        if st.button("Cancel"):
            # Clear dialog state
            for key in list(st.session_state.keys()):
                if key.startswith("new_axis_bins_"):
                    del st.session_state[key]
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
                "bin_mode": bin_mode,
                "bins": bins,
            }
            try:
                create_binning_axis(data)
                st.success(f"Axis created with {len(bins)} bins!")
                for key in list(st.session_state.keys()):
                    if key.startswith("new_axis_bins_"):
                        del st.session_state[key]
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

    current = next((a for a in axes if a["value_binning_axis_id"] == axis_id), None)
    if current is None:
        st.error("Axis not found")
        return

    current_mode = current.get("bin_mode", "interval")

    name = st.text_input("Name *", value=current["name"])
    description = st.text_area("Description", value=current.get("description") or "")

    unit_id = st.selectbox(
        "Unit *",
        options=list(unit_options.keys()),
        index=list(unit_options.keys()).index(current["unit_id"])
        if current["unit_id"] in unit_options
        else 0,
        format_func=lambda x: unit_options.get(x, "Unknown"),
    )

    st.markdown("### Bins")
    st.caption(f"Current bin mode: **{BIN_MODE_LABELS.get(current_mode, current_mode)}** — {current['number_of_bins']} bins")
    replace_bins = st.checkbox("Replace bin definitions")

    new_bins: list | None = None
    new_mode: str = current_mode

    if replace_bins:
        new_mode = st.radio(
            "New bin mode",
            options=BIN_MODE_OPTIONS,
            format_func=lambda x: BIN_MODE_LABELS[x],
            index=BIN_MODE_OPTIONS.index(current_mode),
            horizontal=True,
            key="edit_bin_mode",
        )

        # Load current bins to pre-populate the editor
        edit_init_key = f"edit_axis_bins_{axis_id}_{new_mode}"
        if edit_init_key not in st.session_state:
            try:
                axis_detail = get_binning_axis(axis_id)
                existing_bins = axis_detail.get("bins", []) if axis_detail else []
                if existing_bins and new_mode == current_mode:
                    st.session_state[edit_init_key] = _bins_to_df(existing_bins, new_mode)
                else:
                    st.session_state[edit_init_key] = _empty_bins_df(new_mode, current["number_of_bins"])
            except APIError:
                st.session_state[edit_init_key] = _empty_bins_df(new_mode, 10)

        edited_df = st.data_editor(
            st.session_state[edit_init_key],
            column_config=_editor_column_config(new_mode),
            num_rows="dynamic",
            use_container_width=True,
            key=f"edit_axis_editor_{axis_id}_{new_mode}",
        )

        new_bins = _bins_from_editor(edited_df, new_mode)
        if new_bins:
            st.caption(f"{len(new_bins)} valid bin(s) ready to submit.")

    st.markdown("---")
    submit_col1, submit_col2 = st.columns([1, 1])
    with submit_col1:
        if st.button("Cancel"):
            for key in list(st.session_state.keys()):
                if key.startswith(f"edit_axis_bins_{axis_id}"):
                    del st.session_state[key]
            st.session_state["show_edit_axis_dialog"] = False
            st.session_state["axis_to_edit"] = None
            st.rerun()
    with submit_col2:
        save_disabled = not name or (replace_bins and not new_bins)
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
                payload["bin_mode"] = new_mode

            if not payload:
                st.info("No changes to save.")
                return

            try:
                update_binning_axis(axis_id, payload)
                st.success("Axis updated successfully!")
                for key in list(st.session_state.keys()):
                    if key.startswith(f"edit_axis_bins_{axis_id}"):
                        del st.session_state[key]
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

    axis = next((a for a in axes if a["value_binning_axis_id"] == axis_id), None)
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
                mode = axis_detail.get("bin_mode", "interval")
                cols = ["bin_index"] + _bin_mode_columns(mode)
                bins_df = pd.DataFrame(axis_detail["bins"])[cols]
                st.dataframe(bins_df, use_container_width=True, hide_index=True)
                st.caption(f"Total bins: {len(axis_detail['bins'])} — mode: {BIN_MODE_LABELS.get(mode, mode)}")
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
