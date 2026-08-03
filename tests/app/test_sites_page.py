"""Sites page: the hand-rolled CRUD screen, which does not use generic_crud.

Covers the two guards the shared renderer gained and this page needed too —
a delete confirmation, and text fields capped at the column's width.
"""
from __future__ import annotations

import ast
from pathlib import Path

PAGE = Path(__file__).parent.parent.parent / "app" / "pages" / "sites.py"
TREE = ast.parse(PAGE.read_text())


def _calls_named(name: str, tree: ast.AST = TREE) -> list[ast.Call]:
    return [
        n for n in ast.walk(tree)
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == name
    ]


def test_delete_is_only_reachable_from_the_confirmation_handler():
    """delete_site must not be callable straight from the Delete button."""
    handler = next(
        n for n in ast.walk(TREE)
        if isinstance(n, ast.FunctionDef) and n.name == "_delete"
    )
    assert _calls_named("delete_site", handler), "_delete no longer deletes"
    assert len(_calls_named("delete_site")) == 1, (
        "delete_site is called outside the confirm handler"
    )
    assert _calls_named("confirm_delete_dialog"), "Delete button skips confirmation"


def test_every_text_field_is_capped_at_its_column_width():
    """A free-text field with no cap lets the user type past the column and get
    a 500 from the database instead of a message in the field."""
    from app.components.schema_registry import max_length

    uncapped = [
        call.args[0].value
        for call in _calls_named("render_form_field")
        if len(call.args) >= 2
        and getattr(call.args[1], "value", None) in ("text", "textarea")
        and not any(kw.arg == "max_length" for kw in call.keywords)
    ]
    assert not uncapped, f"text fields with no max_length: {uncapped}"
    assert max_length("Site", "name") == 100, "the cap must come from the dictionary"
