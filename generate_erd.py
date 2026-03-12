"""Compatibility wrapper for legacy ERD generator."""

from __future__ import annotations

import importlib.util
from pathlib import Path

_module_path = (
    Path(__file__).resolve().parent
    / "scripts"
    / "legacy"
    / "generate_erd.py"
)

_spec = importlib.util.spec_from_file_location(
    "_legacy_generate_erd",
    _module_path,
)
_module = importlib.util.module_from_spec(_spec)
assert _spec is not None and _spec.loader is not None
_spec.loader.exec_module(_module)

parse_erd_json = _module.parse_erd_json
generate_erd_data = _module.generate_erd_data
generate_erd_html = _module.generate_erd_html
generate_erd_files = _module.generate_erd_files
ERDTable = _module.ERDTable
ERDField = _module.ERDField
ERDRelationship = _module.ERDRelationship

__all__ = [
    "parse_erd_json",
    "generate_erd_data",
    "generate_erd_html",
    "generate_erd_files",
    "ERDTable",
    "ERDField",
    "ERDRelationship",
]