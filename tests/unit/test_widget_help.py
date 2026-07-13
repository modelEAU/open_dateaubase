"""Every widget must be able to explain itself.

The data model is the product here: a user staring at "Sample material" or
"Operation kind" needs the dictionary's definition without leaving the page. The
YAML-derived CRUD forms get this for free (``build_form_fields`` passes each
column's description through as ``help``). Hand-rolled widgets — wizards, ingest,
explore — must ask for it themselves:

    help=describe("Sample", "sample_kind_id")   # a data-model field
    help="Rows are matched to samples by this column."  # a UI-only control

This test fails on any widget with no ``help`` at all, which is how the last
sweep rotted: nothing stopped the next page from shipping bare labels.
"""

from __future__ import annotations

import ast
import pathlib

from app.components.schema_registry import describe, describe_table, list_tables

_APP = pathlib.Path(__file__).resolve().parents[2] / "app"

# Widgets that take a `help` argument and represent a user-facing input.
_WIDGETS = {
    "selectbox",
    "multiselect",
    "text_input",
    "text_area",
    "number_input",
    "date_input",
    "time_input",
    "checkbox",
    "toggle",
    "radio",
    "slider",
    "file_uploader",
}

# st.data_editor takes no `help` — its *columns* do. A grid column is a field
# like any other, so st.column_config.XColumn(...) is where its definition goes.
_COLUMN_CONFIG = "column_config"

# Helpers that wrap a widget and take `help` themselves; calls to these count.
_WRAPPERS = {"select_or_none", "kind_select", "unit_select", "render_form_field"}


def _widget_calls(tree: ast.AST):
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        fn = node.func
        if isinstance(fn, ast.Attribute) and fn.attr in _WIDGETS:
            obj = getattr(fn.value, "id", "")
            if obj == "st":
                yield node, fn.attr
        elif isinstance(fn, ast.Name) and fn.id in _WRAPPERS:
            yield node, fn.id
        # st.column_config.TextColumn(...) — an Attribute on an Attribute
        elif (
            isinstance(fn, ast.Attribute)
            and isinstance(fn.value, ast.Attribute)
            and fn.value.attr == _COLUMN_CONFIG
            and fn.attr.endswith("Column")
        ):
            yield node, f"column_config.{fn.attr}"


def test_every_widget_has_help():
    offenders = []
    for path in sorted(_APP.rglob("*.py")):
        tree = ast.parse(path.read_text())
        for node, name in _widget_calls(tree):
            # render_form_field spells it help_text (it forwards to several
            # widgets); either kwarg satisfies "this widget can explain itself".
            has_help = any(k.arg in ("help", "help_text") for k in node.keywords)
            # **kwargs forwarding (a wrapper passing help through) also counts
            forwards = any(k.arg is None for k in node.keywords)
            if not (has_help or forwards):
                rel = path.relative_to(_APP.parent)
                offenders.append(f"{rel}:{node.lineno}: {name} has no help=")
    assert not offenders, (
        f"{len(offenders)} widget(s) cannot explain themselves:\n" + "\n".join(offenders)
    )


def test_every_describe_call_resolves():
    # describe() returns "" for an unknown column so a typo can't crash a page
    # mid-render — but that means help=describe("Campaign", "start_date") renders
    # a widget with *no* tooltip and still satisfies the sweep above. The field is
    # really campaign_start_date_time. Every literal call must hit a real column.
    dead = []
    for path in sorted(_APP.rglob("*.py")):
        for node in ast.walk(ast.parse(path.read_text())):
            if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)):
                continue
            if node.func.id != "describe" or len(node.args) != 2:
                continue
            if not all(isinstance(a, ast.Constant) for a in node.args):
                continue  # computed args — can't check statically
            table, field = (a.value for a in node.args)
            if not describe(table, field):
                rel = path.relative_to(_APP.parent)
                dead.append(f'{rel}:{node.lineno}: describe("{table}", "{field}") → ""')
    assert not dead, "describe() calls that resolve to no definition:\n" + "\n".join(dead)


def test_describe_reads_the_dictionary():
    # Definitions come from the YAML, keyed by (table, field) — field alone is
    # ambiguous (campaign_id means something different in ten tables).
    assert "sample" in describe("Sample", "sample_kind_id").lower()
    assert describe("Sample", "SampleKind_ID") == describe("Sample", "sample_kind_id")
    assert describe("Sample", "no_such_column") == ""  # typo → no tooltip, not a crash
    assert describe("NoSuchTable", "x") == ""
    assert describe_table("Sample")


def test_dictionary_defines_everything_the_ui_can_ask_for():
    # The sweep above is only worth anything if the source it reads is complete.
    from app.components.schema_registry import load_table

    undefined = [
        f"{t}.{c.name}"
        for t in list_tables()
        for c in load_table(t).columns
        if not c.description.strip()
    ]
    assert not undefined, f"columns with no definition: {undefined}"
