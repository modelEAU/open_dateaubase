"""Field System Wizard — create Data Acquisition Systems, signal interfaces, equipment, and channels."""

from __future__ import annotations

from datetime import datetime

import streamlit as st

from app.api_client import (
    APIError,
    create_channel,
    create_das,
    create_equipment,
    create_equipment_model,
    create_signal_interface,
    list_das_kinds,
    list_equipment_lookup,
    list_equipment_models_lookup,
    list_operation_kinds_lookup,
    list_parameters_lookup,
    register_equipment_at_interface,
)
from app.components.wizard_helpers import (
    clear_wizard,
    nav,
    render_wizard_header,
    render_wizard_result,
    resolve_id,
    restore_snapshot,
)

_WIZ = "fs_wiz"

STEPS = [
    "Data Acquisition System",
    "Signal Interfaces",
    "Equipment",
    "Channels",
    "Review & Create",
    "Summary",
]

_STEP_PREFIXES: dict[int, list[str]] = {
    0: [f"{_WIZ}_s0_"],
    1: [f"{_WIZ}_si_"],
    2: [f"{_WIZ}_eq_"],
    3: [f"{_WIZ}_ch_"],
    4: [],
    5: [],
}

_VALUE_TYPES = [
    {"id": 1, "label": "Scalar"},
    {"id": 2, "label": "Vector"},
    {"id": 3, "label": "Matrix"},
    {"id": 4, "label": "Image"},
]


def _init() -> None:
    defaults: dict = {
        f"{_WIZ}_step": 0,
        f"{_WIZ}_si_ids": [],
        f"{_WIZ}_si_next_id": 0,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def _cancel() -> None:
    clear_wizard(_WIZ)


def _load_lookups() -> dict | None:
    try:
        return {
            "equipment": list_equipment_lookup(),
            "equipment_models": list_equipment_models_lookup(),
            "parameters": list_parameters_lookup(),
            "operation_kinds": list_operation_kinds_lookup(),
            "das_kinds": list_das_kinds(),
        }
    except APIError as e:
        st.error(f"Failed to load lookup data: {e.message}")
        return None


def _model_label(m: dict) -> str:
    parts = [p for p in [m.get("manufacturer"), m.get("model_name")] if p]
    return " - ".join(parts) if parts else f"Model {m.get('model_id', '?')}"


# ---------------------------------------------------------------------------
# Steps
# ---------------------------------------------------------------------------


def _step_das(lookups: dict) -> None:
    restore_snapshot(_WIZ, 0)

    st.caption(
        "A Data Acquisition System (DAS) is the computer or device at your field site "
        "that collects measurements from instruments — a logger, a SCADA station, or a "
        "laptop running your instrument software."
    )
    st.text_input("Data Acquisition System name *", key=f"{_WIZ}_s0_name")

    das_kinds = lookups.get("das_kinds", [])
    kind_options = [{"id": None, "label": "— not specified —"}] + [
        {"id": k["das_kind_id"], "label": k["name"]} for k in das_kinds
    ]
    kind_labels = [o["label"] for o in kind_options]
    kind_idx = st.selectbox(
        "Data Acquisition System Kind (optional)",
        range(len(kind_labels)),
        format_func=lambda i: kind_labels[i],
        key=f"{_WIZ}_s0_kind_idx",
    )
    st.session_state[f"{_WIZ}_s0_kind_id"] = kind_options[kind_idx]["id"]

    st.text_area("Description (optional)", key=f"{_WIZ}_s0_description")

    def on_next() -> list[str]:
        errors: list[str] = []
        if not (st.session_state.get(f"{_WIZ}_s0_name") or "").strip():
            errors.append("DAS name is required.")
        return errors

    nav(
        wiz_id=_WIZ,
        step=0,
        steps=STEPS,
        step_prefixes=_STEP_PREFIXES,
        on_next=on_next,
        on_cancel=_cancel,
    )


def _step_signal_interfaces(lookups: dict) -> None:  # lookups unused; consistent signature
    restore_snapshot(_WIZ, 1)

    si_ids: list[int] = st.session_state[f"{_WIZ}_si_ids"]

    st.caption(
        "Signal interfaces are the software windows or connections through which your "
        "DAS receives data from instruments. Each vendor typically has its own interface "
        "— for example, a Hach SC1000 controller or a WTW IQ Sensor Net basestation."
    )

    if st.button("+ Add Signal Interface", key=f"{_WIZ}_si_add_btn"):
        nid = st.session_state[f"{_WIZ}_si_next_id"]
        st.session_state[f"{_WIZ}_si_ids"].append(nid)
        st.session_state[f"{_WIZ}_si_next_id"] = nid + 1
        # Initialize per-SI equipment and channel lists
        st.session_state[f"{_WIZ}_eq_{nid}_ids"] = []
        st.session_state[f"{_WIZ}_eq_{nid}_next_id"] = 0
        st.session_state[f"{_WIZ}_ch_{nid}_ids"] = []
        st.session_state[f"{_WIZ}_ch_{nid}_next_id"] = 0
        st.rerun()

    for si_id in list(si_ids):
        label = st.session_state.get(f"{_WIZ}_si_{si_id}_name") or f"Signal Interface {si_id + 1}"
        with st.expander(label, expanded=True):
            st.text_input("Name *", key=f"{_WIZ}_si_{si_id}_name")
            show_advanced = st.checkbox(
                "Show advanced fields (manufacturer, model, serial number)",
                key=f"{_WIZ}_si_{si_id}_show_advanced",
            )
            if show_advanced:
                col_manufacturer, col_model, col_serial = st.columns(3)
                with col_manufacturer:
                    st.text_input("Manufacturer", key=f"{_WIZ}_si_{si_id}_manufacturer")
                with col_model:
                    st.text_input("Model", key=f"{_WIZ}_si_{si_id}_model_name")
                with col_serial:
                    st.text_input("Serial number", key=f"{_WIZ}_si_{si_id}_serial")
            if st.button("Remove", key=f"{_WIZ}_si_{si_id}_remove_btn"):
                st.session_state[f"{_WIZ}_si_ids"].remove(si_id)
                st.rerun()

    def on_next() -> list[str]:
        errors: list[str] = []
        if not st.session_state[f"{_WIZ}_si_ids"]:
            errors.append("At least one signal interface is required.")
        for si_id in st.session_state[f"{_WIZ}_si_ids"]:
            if not (st.session_state.get(f"{_WIZ}_si_{si_id}_name") or "").strip():
                errors.append(f"Signal Interface {si_id + 1}: name is required.")
        return errors

    nav(
        wiz_id=_WIZ,
        step=1,
        steps=STEPS,
        step_prefixes=_STEP_PREFIXES,
        on_next=on_next,
        on_cancel=_cancel,
    )


def _step_equipment(lookups: dict) -> None:
    restore_snapshot(_WIZ, 2)

    eq_opts = [
        {"id": e["equipment_id"], "label": e["identifier"]}
        for e in lookups["equipment"]
    ]
    eq_labels = [o["label"] for o in eq_opts]
    model_opts = [
        {"id": m["model_id"], "label": _model_label(m)}
        for m in lookups["equipment_models"]
    ]
    model_labels = ["(new model)"] + [o["label"] for o in model_opts]

    si_ids: list[int] = st.session_state.get(f"{_WIZ}_si_ids", [])

    st.info("Wire existing or new equipment to each signal interface (optional).")

    for si_id in si_ids:
        si_name = st.session_state.get(f"{_WIZ}_si_{si_id}_name") or f"SI {si_id + 1}"
        st.markdown(f"#### {si_name}")

        # Ensure equipment list exists for this SI
        if f"{_WIZ}_eq_{si_id}_ids" not in st.session_state:
            st.session_state[f"{_WIZ}_eq_{si_id}_ids"] = []
            st.session_state[f"{_WIZ}_eq_{si_id}_next_id"] = 0

        eq_ids: list[int] = st.session_state[f"{_WIZ}_eq_{si_id}_ids"]

        if st.button(f"+ Add Equipment to {si_name}", key=f"{_WIZ}_eq_{si_id}_add_btn"):
            nid = st.session_state[f"{_WIZ}_eq_{si_id}_next_id"]
            st.session_state[f"{_WIZ}_eq_{si_id}_ids"].append(nid)
            st.session_state[f"{_WIZ}_eq_{si_id}_next_id"] = nid + 1
            st.rerun()

        for eq_id in list(eq_ids):
            eq_label = (
                st.session_state.get(f"{_WIZ}_eq_{si_id}_{eq_id}_identifier")
                or f"Equipment {eq_id + 1}"
            )
            with st.expander(eq_label, expanded=True):
                mode = st.radio(
                    "Equipment",
                    ["Existing", "New"],
                    key=f"{_WIZ}_eq_{si_id}_{eq_id}_mode",
                    horizontal=True,
                )
                if mode == "Existing":
                    if eq_labels:
                        st.selectbox(
                            "Select equipment",
                            eq_labels,
                            key=f"{_WIZ}_eq_{si_id}_{eq_id}_existing",
                        )
                    else:
                        st.info("No equipment found. Switch to New to create one.")
                else:
                    st.text_input("Identifier", key=f"{_WIZ}_eq_{si_id}_{eq_id}_identifier")
                    st.text_input("Serial number", key=f"{_WIZ}_eq_{si_id}_{eq_id}_serial")
                    st.selectbox("Model", model_labels, key=f"{_WIZ}_eq_{si_id}_{eq_id}_model")
                    if st.session_state.get(f"{_WIZ}_eq_{si_id}_{eq_id}_model") == "(new model)":
                        col_mfr, col_mname = st.columns(2)
                        with col_mfr:
                            st.text_input(
                                "Manufacturer",
                                key=f"{_WIZ}_eq_{si_id}_{eq_id}_model_manufacturer",
                            )
                        with col_mname:
                            st.text_input(
                                "Model name",
                                key=f"{_WIZ}_eq_{si_id}_{eq_id}_model_name",
                            )

                if st.button("Remove", key=f"{_WIZ}_eq_{si_id}_{eq_id}_remove_btn"):
                    st.session_state[f"{_WIZ}_eq_{si_id}_ids"].remove(eq_id)
                    st.rerun()

    nav(
        wiz_id=_WIZ,
        step=2,
        steps=STEPS,
        step_prefixes=_STEP_PREFIXES,
        on_next=lambda: [],
        on_cancel=_cancel,
    )


def _step_channels(lookups: dict) -> None:
    restore_snapshot(_WIZ, 3)

    param_opts = [
        {"id": p["parameter_id"], "label": p["parameter_name"]}
        for p in lookups["parameters"]
    ]
    param_labels = ["(none)"] + [o["label"] for o in param_opts]
    proc_opts = [
        {"id": p["operation_kind_id"], "label": p["name"]}
        for p in lookups["operation_kinds"]
    ]
    proc_labels = ["(none)"] + [o["label"] for o in proc_opts]
    vt_labels = ["(none)"] + [o["label"] for o in _VALUE_TYPES]

    si_ids: list[int] = st.session_state.get(f"{_WIZ}_si_ids", [])

    st.info("Define data channels (tag names) published by each signal interface.")

    for si_id in si_ids:
        si_name = st.session_state.get(f"{_WIZ}_si_{si_id}_name") or f"SI {si_id + 1}"
        st.markdown(f"#### {si_name}")

        if f"{_WIZ}_ch_{si_id}_ids" not in st.session_state:
            st.session_state[f"{_WIZ}_ch_{si_id}_ids"] = []
            st.session_state[f"{_WIZ}_ch_{si_id}_next_id"] = 0

        ch_ids: list[int] = st.session_state[f"{_WIZ}_ch_{si_id}_ids"]

        if st.button(f"+ Add Channel to {si_name}", key=f"{_WIZ}_ch_{si_id}_add_btn"):
            nid = st.session_state[f"{_WIZ}_ch_{si_id}_next_id"]
            st.session_state[f"{_WIZ}_ch_{si_id}_ids"].append(nid)
            st.session_state[f"{_WIZ}_ch_{si_id}_next_id"] = nid + 1
            st.rerun()

        for ch_id in list(ch_ids):
            tag = st.session_state.get(f"{_WIZ}_ch_{si_id}_{ch_id}_tag") or f"Channel {ch_id + 1}"
            with st.expander(tag, expanded=True):
                col_tag, col_param = st.columns(2)
                with col_tag:
                    st.text_input("Tag name *", key=f"{_WIZ}_ch_{si_id}_{ch_id}_tag")
                with col_param:
                    st.selectbox("Parameter", param_labels, key=f"{_WIZ}_ch_{si_id}_{ch_id}_parameter")
                col_vt, col_proc = st.columns(2)
                with col_vt:
                    st.selectbox("Value type", vt_labels, key=f"{_WIZ}_ch_{si_id}_{ch_id}_value_type")
                with col_proc:
                    st.selectbox(
                        "Processing",
                        proc_labels,
                        key=f"{_WIZ}_ch_{si_id}_{ch_id}_processing",
                    )
                if st.button("Remove", key=f"{_WIZ}_ch_{si_id}_{ch_id}_remove_btn"):
                    st.session_state[f"{_WIZ}_ch_{si_id}_ids"].remove(ch_id)
                    st.rerun()

    def on_next() -> list[str]:
        errors: list[str] = []
        for si_id in st.session_state.get(f"{_WIZ}_si_ids", []):
            for ch_id in st.session_state.get(f"{_WIZ}_ch_{si_id}_ids", []):
                if not (st.session_state.get(f"{_WIZ}_ch_{si_id}_{ch_id}_tag") or "").strip():
                    errors.append(f"Channel {ch_id + 1} on SI {si_id + 1}: tag name is required.")
        return errors

    nav(
        wiz_id=_WIZ,
        step=3,
        steps=STEPS,
        step_prefixes=_STEP_PREFIXES,
        on_next=on_next,
        on_cancel=_cancel,
    )


def _step_review(lookups: dict) -> None:
    das_name = st.session_state.get(f"{_WIZ}_s0_name", "")
    das_desc = st.session_state.get(f"{_WIZ}_s0_description", "")
    si_ids = st.session_state.get(f"{_WIZ}_si_ids", [])

    st.markdown("### Data Acquisition System")
    st.write(f"**Name:** {das_name}")
    if das_desc:
        st.write(f"**Description:** {das_desc}")

    for si_id in si_ids:
        si_name = st.session_state.get(f"{_WIZ}_si_{si_id}_name", "")
        with st.expander(f"Signal Interface: {si_name}", expanded=True):
            eq_ids = st.session_state.get(f"{_WIZ}_eq_{si_id}_ids", [])
            if eq_ids:
                st.markdown("**Equipment:**")
                for eq_id in eq_ids:
                    mode = st.session_state.get(f"{_WIZ}_eq_{si_id}_{eq_id}_mode", "Existing")
                    if mode == "Existing":
                        label = st.session_state.get(f"{_WIZ}_eq_{si_id}_{eq_id}_existing", "?")
                        st.write(f"- Existing: {label}")
                    else:
                        ident = st.session_state.get(f"{_WIZ}_eq_{si_id}_{eq_id}_identifier", "?")
                        st.write(f"- New: {ident}")
            ch_ids = st.session_state.get(f"{_WIZ}_ch_{si_id}_ids", [])
            if ch_ids:
                st.markdown("**Channels:**")
                for ch_id in ch_ids:
                    tag = st.session_state.get(f"{_WIZ}_ch_{si_id}_{ch_id}_tag", "?")
                    param = st.session_state.get(f"{_WIZ}_ch_{si_id}_{ch_id}_parameter", "")
                    st.write(f"- `{tag}` ({param})")
            if not eq_ids and not ch_ids:
                st.caption("No equipment or channels defined.")

    def on_next() -> list[str]:
        created, errors = _execute_creates(lookups)
        st.session_state[f"_{_WIZ}_created"] = created
        st.session_state[f"_{_WIZ}_errors"] = errors
        return []

    nav(
        wiz_id=_WIZ,
        step=4,
        steps=STEPS,
        step_prefixes=_STEP_PREFIXES,
        on_next=on_next,
        on_cancel=_cancel,
        next_label="Confirm & Create",
    )


def _step_summary(lookups: dict) -> None:
    render_wizard_result(
        wiz_id=_WIZ,
        title="Field system",
        created=st.session_state.get(f"_{_WIZ}_created", []),
        errors=st.session_state.get(f"_{_WIZ}_errors", []),
        on_restart=lambda: clear_wizard(_WIZ),
    )


# ---------------------------------------------------------------------------
# Execution
# ---------------------------------------------------------------------------


def _execute_creates(lookups: dict) -> tuple[list[dict], list[str]]:
    for s in range(4):
        restore_snapshot(_WIZ, s)

    created: list[dict] = []
    errors: list[str] = []
    si_id_map: dict[int, int] = {}  # wiz_si_id → DB SignalInterface_ID

    eq_opts = [
        {"id": e["equipment_id"], "label": e["identifier"]}
        for e in lookups["equipment"]
    ]
    model_opts = [
        {"id": m["model_id"], "label": _model_label(m)}
        for m in lookups["equipment_models"]
    ]
    param_opts = [
        {"id": p["parameter_id"], "label": p["parameter_name"]}
        for p in lookups["parameters"]
    ]
    # 1. Create DAS
    try:
        das = create_das(
            {
                "name": (st.session_state.get(f"{_WIZ}_s0_name") or "").strip(),
                "description": st.session_state.get(f"{_WIZ}_s0_description") or None,
                "das_kind_id": st.session_state.get(f"{_WIZ}_s0_kind_id"),
            }
        )
        das_id: int = das["data_acquisition_system_id"]
        created.append({"label": f"DAS: {das.get('name', '')}", "detail": f"id={das_id}"})
    except APIError as e:
        errors.append(f"DAS creation failed: {e.message}")
        return created, errors

    # 2. Create signal interfaces
    for si_wiz_id in st.session_state.get(f"{_WIZ}_si_ids", []):
        si_name = (st.session_state.get(f"{_WIZ}_si_{si_wiz_id}_name") or "").strip()
        try:
            si = create_signal_interface(
                {
                    "data_acquisition_system_id": das_id,
                    "name": si_name,
                    "manufacturer": st.session_state.get(f"{_WIZ}_si_{si_wiz_id}_manufacturer") or None,
                    "model": st.session_state.get(f"{_WIZ}_si_{si_wiz_id}_model_name") or None,
                    "serial_number": st.session_state.get(f"{_WIZ}_si_{si_wiz_id}_serial") or None,
                }
            )
            si_id_map[si_wiz_id] = si["signal_interface_id"]
            created.append({"label": f"Signal interface: {si_name}", "detail": f"id={si['signal_interface_id']}"})
        except APIError as e:
            errors.append(f"Signal interface '{si_name}': {e.message}")
            continue

        actual_si_id = si_id_map[si_wiz_id]

        # 3. Wire equipment to this SI
        for eq_wiz_id in st.session_state.get(f"{_WIZ}_eq_{si_wiz_id}_ids", []):
            mode = st.session_state.get(f"{_WIZ}_eq_{si_wiz_id}_{eq_wiz_id}_mode", "Existing")
            actual_eq_id: int | None = None

            if mode == "Existing":
                existing_label = st.session_state.get(f"{_WIZ}_eq_{si_wiz_id}_{eq_wiz_id}_existing")
                actual_eq_id = resolve_id(existing_label, eq_opts)
            else:
                # Resolve or create model
                model_label = st.session_state.get(f"{_WIZ}_eq_{si_wiz_id}_{eq_wiz_id}_model") or "(new model)"
                resolved_model_id: int | None = None
                if model_label == "(new model)":
                    mfr = st.session_state.get(f"{_WIZ}_eq_{si_wiz_id}_{eq_wiz_id}_model_manufacturer") or None
                    mname = st.session_state.get(f"{_WIZ}_eq_{si_wiz_id}_{eq_wiz_id}_model_name") or None
                    if mfr or mname:
                        try:
                            new_model = create_equipment_model(
                                {"model_name": mname, "manufacturer": mfr}
                            )
                            resolved_model_id = new_model["model_id"]
                        except APIError as e:
                            errors.append(f"Equipment model: {e.message}")
                            continue
                else:
                    resolved_model_id = resolve_id(model_label, model_opts)

                try:
                    eq = create_equipment(
                        {
                            "model_id": resolved_model_id,
                            "identifier": st.session_state.get(f"{_WIZ}_eq_{si_wiz_id}_{eq_wiz_id}_identifier") or None,
                            "serial_number": st.session_state.get(f"{_WIZ}_eq_{si_wiz_id}_{eq_wiz_id}_serial") or None,
                        }
                    )
                    actual_eq_id = eq["equipment_id"]
                    created.append({"label": f"Equipment: {eq.get('identifier') or actual_eq_id}", "detail": f"id={actual_eq_id}"})
                except APIError as e:
                    errors.append(f"Equipment creation failed: {e.message}")
                    continue

            if actual_eq_id is not None:
                try:
                    register_equipment_at_interface(
                        actual_eq_id,
                        {
                            "signal_interface_id": actual_si_id,
                            "valid_from": datetime.now().isoformat(),
                        },
                    )
                except APIError as e:
                    errors.append(f"Equipment wiring failed: {e.message}")

        # 4. Create channels for this SI
        for ch_wiz_id in st.session_state.get(f"{_WIZ}_ch_{si_wiz_id}_ids", []):
            tag = (st.session_state.get(f"{_WIZ}_ch_{si_wiz_id}_{ch_wiz_id}_tag") or "").strip()
            if not tag:
                continue
            param_label = st.session_state.get(f"{_WIZ}_ch_{si_wiz_id}_{ch_wiz_id}_parameter")
            vt_label = st.session_state.get(f"{_WIZ}_ch_{si_wiz_id}_{ch_wiz_id}_value_type")
            param_id = (
                resolve_id(param_label, param_opts)
                if param_label and param_label != "(none)"
                else None
            )
            vt_id = (
                resolve_id(vt_label, _VALUE_TYPES)
                if vt_label and vt_label != "(none)"
                else None
            )
            # Channel identity does not carry an operation kind (set later via
            # the lineage/processing step); the selector here is informational.
            try:
                ch = create_channel(
                    {
                        "signal_interface_id": actual_si_id,
                        "tag_name": tag,
                        "parameter_id": param_id,
                        "value_kind_id": vt_id,
                    }
                )
                ch_id = ch.get("channel_id") if isinstance(ch, dict) else None
                created.append({"label": f"Channel: {tag}", "detail": f"id={ch_id}" if ch_id else None})
            except APIError as e:
                errors.append(f"Channel '{tag}': {e.message}")

    return created, errors


# ---------------------------------------------------------------------------
# Page entry point
# ---------------------------------------------------------------------------


def main() -> None:
    st.title("📡 Field System Wizard")
    _init()

    with st.spinner("Loading lookup data…"):
        lookups = _load_lookups()
    if lookups is None:
        return

    step = st.session_state[f"{_WIZ}_step"]
    render_wizard_header(step, STEPS)

    {
        0: _step_das,
        1: _step_signal_interfaces,
        2: _step_equipment,
        3: _step_channels,
        4: _step_review,
        5: _step_summary,
    }[step](lookups)


main()
