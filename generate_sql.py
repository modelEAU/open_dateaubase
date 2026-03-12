"""Compatibility wrapper for legacy SQL generator."""

from __future__ import annotations

import importlib.util
from pathlib import Path

_module_path = (
    Path(__file__).resolve().parent
    / "scripts"
    / "legacy"
    / "generate_sql.py"
)

_spec = importlib.util.spec_from_file_location(
    "_legacy_generate_sql",
    _module_path,
)
_module = importlib.util.module_from_spec(_spec)
assert _spec is not None and _spec.loader is not None
_spec.loader.exec_module(_module)

parse_parts_json = _module.parse_parts_json
generate_sql_schema = _module.generate_sql_schema
generate_field_definition = _module.generate_field_definition
generate_foreign_key_constraint = _module.generate_foreign_key_constraint
validate_no_circular_fks = _module.validate_no_circular_fks
get_db_config = _module.get_db_config
extract_field_name = _module.extract_field_name
generate_sql_schemas = _module.generate_sql_schemas

__all__ = [
    "parse_parts_json",
    "generate_sql_schema",
    "generate_field_definition",
    "generate_foreign_key_constraint",
    "validate_no_circular_fks",
    "get_db_config",
    "extract_field_name",
    "generate_sql_schemas",
]