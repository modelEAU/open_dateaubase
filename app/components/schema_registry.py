"""YAML schema registry: loads table definitions and derives UI form metadata."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import yaml

_SCHEMA_DIR = Path(__file__).resolve().parents[2] / "schema_dictionary" / "tables"

_LOGICAL_TO_FORM: dict[str, str] = {
    "string": "text",
    "text": "textarea",
    "integer": "number",
    "float": "number",
    "boolean": "checkbox",
    "timestamp": "datetime",
}


def _to_snake(name: str) -> str:
    """'QualityCode_ID' → 'quality_code_id', 'IsUsable' → 'is_usable', 'LatitudeWGS84' → 'latitude_wgs84'."""
    # Insert _ at lowercase/digit → uppercase boundaries (handles CamelCase)
    s = re.sub(r"([a-z\d])([A-Z])", r"\1_\2", name)
    # Insert _ before a run of capitals followed by a lowercase (e.g. XMLParser → XML_Parser)
    s = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", s)
    return s.lower()


def fk_lookup_fn(table_name: str) -> str:
    """Derive the api_client lookup function name from a referenced table name.

    'SiteType' → 'list_site_type_lookup'
    'SignalPort' → 'list_signal_port_lookup'
    """
    return f"list_{_to_snake(table_name)}_lookup"


@dataclass
class ColumnMeta:
    name: str          # original YAML column name, e.g. "Unit_ID"
    field: str         # snake_case API field name, e.g. "unit_id"
    logical_type: str
    nullable: bool
    is_pk: bool
    is_identity: bool
    description: str
    max_length: int | None = None
    fk_table: str | None = None

    @property
    def form_type(self) -> str:
        if self.fk_table:
            return "select"
        return _LOGICAL_TO_FORM.get(self.logical_type, "text")

    @property
    def fk_lookup_fn(self) -> str | None:
        return fk_lookup_fn(self.fk_table) if self.fk_table else None


@dataclass
class TableMeta:
    table_name: str
    description: str
    pk_field: str      # snake_case PK field name used in API responses
    columns: list[ColumnMeta]

    def form_columns(self) -> list[ColumnMeta]:
        """Columns to include in create/edit forms (excludes PK identity columns)."""
        return [c for c in self.columns if not (c.is_pk and c.is_identity)]

    def build_form_fields(self) -> list[dict]:
        """Return a form_fields list compatible with form_dialog and generic_crud."""
        fields = []
        for col in self.form_columns():
            if col.is_pk:
                continue
            entry: dict = {
                "name": col.field,
                "type": col.form_type,
                "required": not col.nullable,
                "help": col.description,
                "label": col.name,
            }
            if col.fk_lookup_fn:
                entry["options_fn"] = col.fk_lookup_fn
            fields.append(entry)
        return fields


def load_table(table_name: str) -> TableMeta:
    """Load and parse a YAML table definition into a TableMeta."""
    yaml_path = _SCHEMA_DIR / f"{table_name}.yaml"
    raw = yaml.safe_load(yaml_path.read_text())["table"]

    pk_cols: set[str] = set(raw.get("primary_key", []))
    columns: list[ColumnMeta] = []

    for col in raw.get("columns", []):
        col_name: str = col["name"]
        fk = col.get("foreign_key")
        columns.append(
            ColumnMeta(
                name=col_name,
                field=_to_snake(col_name),
                logical_type=col.get("logical_type", "string"),
                nullable=col.get("nullable", True),
                is_pk=col_name in pk_cols,
                is_identity=col.get("identity", False),
                description=col.get("description", ""),
                max_length=col.get("max_length"),
                fk_table=fk["table"] if fk else None,
            )
        )

    pk_col = next((c for c in columns if c.is_pk), None)
    pk_field = pk_col.field if pk_col else "id"

    return TableMeta(
        table_name=raw["name"],
        description=raw.get("description", ""),
        pk_field=pk_field,
        columns=columns,
    )
