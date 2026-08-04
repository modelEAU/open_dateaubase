"""A dropdown must offer exactly one empty choice, whatever the caller passes."""

from __future__ import annotations

import ast
import pathlib
from unittest.mock import patch

from app.components.crud_form import render_form_field
from app.components.kind_select import kind_select
from app.components.labels import NONE_LABEL

_CALLER_SENTINEL = {"id": None, "label": "— none —", "description": ""}
# Plain selectbox path: no option carries a description.
_PLAIN = [{"id": 1, "label": "grit"}, {"id": 2, "label": "domestic wastewater"}]
# Described options route through kind_select instead.
_KINDS = [
    {"id": 1, "label": "grit", "description": ""},
    {"id": 2, "label": "domestic wastewater", "description": "sewage"},
]


def _labels_from_plain_select(options, required):
    with patch("app.components.crud_form.st") as st:
        st.selectbox.side_effect = lambda *a, **kw: kw["options"][0]
        render_form_field("mk", "select", options=options, required=required)
        return st.selectbox.call_args.kwargs["options"]


def _labels_from_kind_select(options, allow_empty):
    with patch("app.components.kind_select.st") as st:
        st.selectbox.return_value = options[0]
        kind_select(
            "mk",
            options,
            id_field="id",
            name_field="label",
            desc_field="description",
            allow_empty=allow_empty,
        )
        rows = st.selectbox.call_args.kwargs["options"]
        return [r["label"] for r in rows]


def test_plain_select_dedupes_caller_sentinel():
    labels = _labels_from_plain_select([_CALLER_SENTINEL, *_PLAIN], required=False)
    assert labels.count(NONE_LABEL) == 1
    assert labels == [NONE_LABEL, "grit", "domestic wastewater"]


def test_required_select_has_no_empty_choice():
    labels = _labels_from_plain_select([_CALLER_SENTINEL, *_PLAIN], required=True)
    assert NONE_LABEL not in labels


def test_kind_select_dedupes_caller_sentinel():
    labels = _labels_from_kind_select([_CALLER_SENTINEL, *_KINDS], allow_empty=True)
    assert labels.count(NONE_LABEL) == 1


def test_optional_described_field_still_offers_none():
    # Descriptions route through kind_select; optional means an empty choice.
    with patch("app.components.kind_select.st") as st:
        st.selectbox.return_value = _KINDS[0]
        render_form_field("mk", "select", options=_KINDS, required=False)
        rows = st.selectbox.call_args.kwargs["options"]
    assert [r["label"] for r in rows][0] == NONE_LABEL


def test_no_hand_spelled_sentinel_labels():
    # Every dropdown sentinel comes from app.components.labels. A hand-spelled
    # variant is how "— None —" and "— none —" ended up in the same dropdown.
    banned = (
        "(none)",
        "(all sites)",
        "(all process units)",
        "— select —",
        "— pick —",
        "— not specified —",
        "— None —",
        "All Sites",
    )
    app = pathlib.Path(__file__).resolve().parents[2] / "app"
    offenders = [
        f"{path.relative_to(app.parent)}:{n}: {line.strip()}"
        for path in app.rglob("*.py")
        if path.name != "labels.py"
        for n, line in enumerate(path.read_text().splitlines(), 1)
        if any(b in line for b in banned)
    ]
    assert not offenders, "hand-spelled sentinel labels:\n" + "\n".join(offenders)


def test_dropdowns_use_the_none_row_not_streamlit_empty_state():
    # "index=None" is Streamlit's native empty state — a second, different-looking
    # way to say "nothing picked". The house style is the NONE_LABEL row
    # (select_or_none / kind_select), so dropdowns match each other everywhere.
    # Radios and pills have no NONE_LABEL convention; their empty state is fine.
    app = pathlib.Path(__file__).resolve().parents[2] / "app"
    offenders = []
    for path in app.rglob("*.py"):
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
                continue
            if node.func.attr not in ("selectbox", "multiselect"):
                continue
            if any(
                kw.arg == "index" and isinstance(kw.value, ast.Constant) and kw.value.value is None
                for kw in node.keywords
            ):
                offenders.append(f"{path.relative_to(app.parent)}:{node.lineno}")
    assert not offenders, "dropdowns using index=None:\n" + "\n".join(offenders)
