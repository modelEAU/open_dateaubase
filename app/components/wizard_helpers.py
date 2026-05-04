"""Shared utilities for multi-step wizard pages."""

from __future__ import annotations

from collections.abc import Callable

import streamlit as st


def render_wizard_header(step: int, steps: list[str]) -> None:
    fraction = step / max(len(steps) - 1, 1)
    st.progress(fraction)
    st.caption(f"Step {step + 1} / {len(steps)}: **{steps[step]}**")
    st.markdown(f"## {steps[step]}")


def nav(
    *,
    wiz_id: str,
    step: int,
    steps: list[str],
    step_prefixes: dict[int, list[str]],
    on_next: Callable[[], list[str]],
    on_cancel: Callable[[], None],
) -> None:
    """Render Cancel / Back / Next row and handle step transitions."""
    st.divider()
    col_cancel, col_back, _, col_next = st.columns([1, 1, 5, 2])

    with col_cancel:
        if st.button("✖ Cancel", key=f"{wiz_id}_cancel_{step}"):
            on_cancel()
            st.rerun()

    with col_back:
        if st.button("◀ Back", key=f"{wiz_id}_back_{step}", disabled=step == 0):
            _save_snapshot(wiz_id, step, step_prefixes)
            st.session_state[f"{wiz_id}_step"] -= 1
            st.rerun()

    with col_next:
        is_last = step == len(steps) - 1
        label = "Confirm & Create" if is_last else "Next ▶"
        if st.button(label, key=f"{wiz_id}_next_{step}", type="primary"):
            errors = on_next()
            if errors:
                for err in errors:
                    st.error(err)
            elif not is_last:
                _save_snapshot(wiz_id, step, step_prefixes)
                st.session_state[f"{wiz_id}_step"] += 1
                st.rerun()
            # Last step: on_next handles toast + clear + rerun on success


def restore_snapshot(wiz_id: str, step: int) -> None:
    """Restore previously captured session-state keys for this step."""
    snap: dict = st.session_state.get(f"_{wiz_id}_snap_{step}", {})
    for key, val in snap.items():
        if key not in st.session_state:
            st.session_state[key] = val


def clear_wizard(wiz_id: str) -> None:
    """Remove all wizard state keys from session_state."""
    prefix = f"{wiz_id}_"
    snap_prefix = f"_{wiz_id}_snap_"
    to_del = [
        k
        for k in list(st.session_state.keys())
        if isinstance(k, str)
        and (k.startswith(prefix) or k.startswith(snap_prefix))
    ]
    for k in to_del:
        del st.session_state[k]


def resolve_id(label: str | None, opts: list[dict]) -> int | None:
    """Return the `id` field for the first option whose `label` matches."""
    if not label:
        return None
    match = next((o for o in opts if o.get("label") == label), None)
    return match["id"] if match else None


def _save_snapshot(wiz_id: str, step: int, step_prefixes: dict[int, list[str]]) -> None:
    prefixes = step_prefixes.get(step, [])
    snap: dict = {}
    for key, val in st.session_state.items():
        if isinstance(key, str) and any(key.startswith(p) for p in prefixes):
            if (
                key.endswith("_remove")
                or key.endswith("_remove_confirm")
                or key.endswith("_remove_yes")
                or key.endswith("_add")
                or "_add_" in key
            ):
                continue
            snap[key] = val
    st.session_state[f"_{wiz_id}_snap_{step}"] = snap
