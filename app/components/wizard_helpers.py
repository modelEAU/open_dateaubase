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
    next_label: str | None = None,
) -> None:
    """Render Cancel / Back / Next row and handle step transitions.

    Pass ``next_label`` to override the default ("Next ▶" or "Confirm & Create")
    — useful when the wizard has a terminal Summary step that follows the
    review step, so the review step still reads "Confirm & Create".
    """
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
        label = next_label or ("Confirm & Create" if is_last else "Next ▶")
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


def snapshot_get(wiz_id: str, step: int, key: str, default=None):
    """Read a value a prior step captured in its snapshot.

    Streamlit drops a widget's session-state entry on any rerun where that
    widget is not rendered. A later step that reads an earlier step's widget key
    directly therefore sees ``None`` after the first in-step rerun (e.g. a
    selectbox change), losing the earlier selection. The snapshot is a plain
    dict that survives, so cross-step reads must come from it. Live state wins
    when present (most up to date); fall back to the snapshot when dropped.
    """
    if key in st.session_state:
        return st.session_state[key]
    return st.session_state.get(f"_{wiz_id}_snap_{step}", {}).get(key, default)


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


def render_wizard_result(
    *,
    wiz_id: str,
    title: str,
    created: list[dict],
    errors: list[str],
    on_restart: Callable[[], None],
) -> None:
    """Render the terminal "Summary" step of a wizard.

    Shows a success/partial/failure banner, lists everything that was created
    (with optional details), lists any errors, and offers a "Create another"
    button that calls ``on_restart`` (typically ``clear_wizard``) and reruns.

    ``created`` items should be ``{"label": str, "detail": str | None}`` dicts;
    plain strings are accepted and rendered as labels.
    """
    if errors and not created:
        st.error(f"❌ {title} could not be created.")
    elif errors:
        st.warning(f"⚠️ {title} created with errors — review below.")
    else:
        st.success(f"✅ {title} created successfully!")

    if created:
        st.markdown("### What was created")
        for item in created:
            if isinstance(item, str):
                st.markdown(f"- {item}")
            else:
                label = item.get("label", "")
                detail = item.get("detail")
                if detail:
                    st.markdown(f"- **{label}** — {detail}")
                else:
                    st.markdown(f"- {label}")

    if errors:
        st.markdown("### Errors")
        for err in errors:
            st.error(err)

    st.divider()
    col_restart, col_done = st.columns(2)
    with col_restart:
        if st.button(
            "✨ Create another",
            key=f"{wiz_id}_summary_restart",
            type="primary",
            use_container_width=True,
        ):
            on_restart()
            st.rerun()
    with col_done:
        if st.button(
            "Done",
            key=f"{wiz_id}_summary_done",
            use_container_width=True,
        ):
            on_restart()
            st.rerun()


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
