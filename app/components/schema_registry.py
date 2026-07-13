"""YAML schema registry: loads table definitions and derives UI form metadata."""

from __future__ import annotations

import re
from collections.abc import Collection
from dataclasses import dataclass
from functools import lru_cache
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

    'SiteKind' → 'list_site_kind_lookup'
    'SignalInterface' → 'list_signal_interface_lookup'
    """
    return f"list_{_to_snake(table_name)}_lookup"


@dataclass
class ColumnMeta:
    name: str  # original YAML column name, e.g. "Unit_ID"
    field: str  # snake_case API field name, e.g. "unit_id"
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
    pk_field: str  # snake_case PK field name used in API responses
    columns: list[ColumnMeta]

    def form_columns(self) -> list[ColumnMeta]:
        """Columns to include in create/edit forms (excludes PK identity columns)."""
        return [c for c in self.columns if not (c.is_pk and c.is_identity)]

    def build_form_fields(
        self,
        *,
        exclude: Collection[str] = frozenset(),
        overrides: dict[str, dict] | None = None,
    ) -> list[dict]:
        """Return a form_fields list compatible with form_dialog and generic_crud.

        ``exclude``   drops columns by their snake_case field name (e.g. columns
                      the API deliberately doesn't accept for editing).
        ``overrides`` patches a field's entry, keyed by the original snake_case
                      field name. Use to rename a field to the API's name
                      (``{"name": "model_id"}``), fix an ``options_fn``, or swap
                      the widget. Keys naming a non-column are ignored here but
                      are flagged by the form-coverage test.
        """
        overrides = overrides or {}
        fields = []
        for col in self.form_columns():
            if col.is_pk or col.field in exclude:
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
            if col.field in overrides:
                entry.update(overrides[col.field])
            fields.append(entry)
        return fields


def list_tables() -> list[str]:
    """Return all table names defined in the YAML schema dictionary, sorted."""
    return sorted(p.stem for p in _SCHEMA_DIR.glob("*.yaml"))


@lru_cache(maxsize=None)
def describe(table: str, field: str) -> str:
    """The dictionary's definition of a column, for use as a widget's ``help``.

    Hand-rolled widgets (wizards, ingest, explore) don't go through
    ``build_form_fields``, so they must ask for the definition themselves —
    ``help=describe("Sample", "sample_kind_id")`` — rather than restate it
    inline, where it would drift from the schema.

    Keyed on (table, field) because the field name alone is ambiguous:
    ``campaign_id`` carries a different definition in each of the ten tables
    that reference it. ``field`` accepts the YAML name or the snake_case API
    name. Returns "" for an unknown column, so a typo degrades to no tooltip
    rather than an exception in the middle of a page.
    """
    try:
        meta = load_table(table)
    except (FileNotFoundError, KeyError):
        return ""
    want = _to_snake(field)
    return next((c.description for c in meta.columns if c.field == want), "")


@lru_cache(maxsize=None)
def describe_table(table: str) -> str:
    """The dictionary's definition of an entity, for a page/section tooltip."""
    try:
        return load_table(table).description.strip()
    except (FileNotFoundError, KeyError):
        return ""


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
