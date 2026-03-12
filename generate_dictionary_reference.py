"""Compatibility wrapper for legacy dictionary reference generator."""

from __future__ import annotations

import importlib.util
from pathlib import Path

_module_path = (
    Path(__file__).resolve().parent
    / "scripts"
    / "legacy"
    / "generate_dictionary_reference.py"
)

_spec = importlib.util.spec_from_file_location(
    "_legacy_generate_dictionary_reference",
    _module_path,
)
_module = importlib.util.module_from_spec(_spec)
assert _spec is not None and _spec.loader is not None
_spec.loader.exec_module(_module)

parse_parts_json = _module.parse_parts_json
generate_tables_markdown = _module.generate_tables_markdown
generate_value_sets_markdown = _module.generate_value_sets_markdown
generate_views_markdown = _module.generate_views_markdown

__all__ = [
    "parse_parts_json",
    "generate_tables_markdown",
    "generate_value_sets_markdown",
    "generate_views_markdown",
]