"""Generate one YAML file per table from the schema dictionary (dictionary.json).

Usage:
    python scripts/generate_yaml_tables.py

Output:
    schema_dictionary/tables/{TableName}.yaml  — one file per table, skipping MetaData.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parent.parent
DICT_PATH = REPO_ROOT / "src" / "open_dateaubase" / "dictionary.json"
OUT_DIR = REPO_ROOT / "schema_dictionary" / "tables"

# ---------------------------------------------------------------------------
# Table-name mapping  (Part_ID → PascalCase YAML/file name)
# ---------------------------------------------------------------------------
TABLE_NAME_MAP: dict[str, str] = {
    "metadata": "MetaData",
    "value": "Value",
    "comments": "Comments",
    "equipment": "Equipment",
    "equipment_model": "EquipmentModel",
    "equipment_model_has_Parameter": "EquipmentModelHasParameter",
    "equipment_model_has_procedures": "EquipmentModelHasProcedures",
    "parameter": "Parameter",
    "unit": "Unit",
    "procedures": "Procedures",
    "parameter_has_procedures": "ParameterHasProcedures",
    "purpose": "Purpose",
    "weather_condition": "WeatherCondition",
    "site": "Site",
    "sampling_points": "SamplingPoints",
    "watershed": "Watershed",
    "hydrological_characteristics": "HydrologicalCharacteristics",
    "urban_characteristics": "UrbanCharacteristics",
    "project": "Project",
    "project_has_contact": "ProjectHasContact",
    "project_has_equipment": "ProjectHasEquipment",
    "project_has_sampling_points": "ProjectHasSamplingPoints",
    "contact": "Contact",
}

SKIP_TABLES = {"MetaData"}  # already created manually

COLUMN_ROLES = {"key", "property", "compositeKeyFirst", "compositeKeySecond"}


# ---------------------------------------------------------------------------
# SQL → logical type helpers
# ---------------------------------------------------------------------------

def _parse_nvarchar(sql_type: str) -> dict[str, Any]:
    """Return logical_type attrs for nvarchar(N) / nvarchar(max)."""
    m = re.match(r"nvarchar\((\w+)\)", sql_type, re.IGNORECASE)
    if not m:
        return {"logical_type": "string", "max_length": "max"}
    n = m.group(1)
    if n.lower() == "max" or int(n) >= 1_073_741_823:
        return {"logical_type": "text"}
    return {"logical_type": "string", "max_length": int(n)}


def _parse_numeric(sql_type: str) -> dict[str, Any]:
    m = re.match(r"numeric\((\d+),\s*(\d+)\)", sql_type, re.IGNORECASE)
    if m:
        return {"logical_type": "decimal", "precision": int(m.group(1)), "scale": int(m.group(2))}
    # bare "numeric" without precision/scale — leave a TODO
    return {"logical_type": "decimal", "precision": None, "scale": None}


def _parse_datetime2(sql_type: str) -> dict[str, Any]:
    m = re.match(r"datetime2\((\d+)\)", sql_type, re.IGNORECASE)
    prec = int(m.group(1)) if m else 7
    return {"logical_type": "timestamp", "precision": prec}


SQL_SIMPLE: dict[str, str] = {
    "int": "integer",
    "bigint": "biginteger",
    "float": "float64",
    "real": "float32",
    "bit": "boolean",
    "date": "date",
    "nvarchar(max)": "text",
    "nvarchar(1073741823)": "text",
}


def map_sql_type(raw: str | None) -> dict[str, Any]:
    """Map an SQL_data_type string to a dict of logical-type attributes."""
    if not raw:
        return {"logical_type": "# TODO: unknown type"}
    cleaned = raw.strip()

    # Simple direct lookups first (case-insensitive)
    lower = cleaned.lower()
    for k, v in SQL_SIMPLE.items():
        if lower == k:
            return {"logical_type": v}

    if lower.startswith("nvarchar"):
        return _parse_nvarchar(cleaned)
    if lower.startswith("ntext") or lower == "nvarchar(1073741823)":
        return {"logical_type": "text"}
    if lower.startswith("numeric"):
        return _parse_numeric(cleaned)
    if lower.startswith("datetime2"):
        return _parse_datetime2(cleaned)

    # Fallback — emit a TODO so the author can fix it
    return {"logical_type": f"# TODO: unmapped SQL type: {cleaned}"}


# ---------------------------------------------------------------------------
# Column name stripping
# ---------------------------------------------------------------------------

def derive_column_name(part_id: str, table_id: str) -> str:
    """Strip the table-specific prefix from part_id if present.

    Only strip when the remainder is not just 'ID' or '_ID' — those are
    meaningful identifiers in their own right (e.g. Unit_ID should stay
    Unit_ID, not collapse to bare 'ID').
    """
    prefix = table_id.lower() + "_"
    if part_id.lower().startswith(prefix):
        remainder = part_id[len(prefix):]
        # Do not strip if the remainder is bare 'ID' — the full name is clearer
        if remainder.upper() != "ID":
            return remainder
    return part_id


# ---------------------------------------------------------------------------
# FK resolution
# ---------------------------------------------------------------------------

def find_fk_target(part_id: str, all_parts: list[dict[str, Any]]) -> tuple[str, str] | None:
    """Return (PascalCaseTable, ColumnName) if part_id is a FK, else None.

    A column is a FK when it ends with _ID and appears as "key" role in some
    other table's table_presence.  We find the table where it is the primary key
    and use that as the referenced table.
    """
    if not part_id.upper().endswith("_ID"):
        return None

    # Find the part entry
    for part in all_parts:
        if part.get("Part_ID") != part_id:
            continue
        tp = part.get("table_presence", {})
        for tbl_id, presence in tp.items():
            if presence.get("role") == "key":
                pascal = TABLE_NAME_MAP.get(tbl_id)
                if pascal:
                    col_name = derive_column_name(part_id, tbl_id)
                    return pascal, col_name
    return None


# ---------------------------------------------------------------------------
# YAML serialisation (hand-rolled to keep full control over formatting)
# ---------------------------------------------------------------------------

def _yaml_str(value: str) -> str:
    """Quote a string for YAML if it needs quoting."""
    # If the value contains special chars or looks like a YAML keyword, quote it.
    needs_quoting = any(c in value for c in (':', '#', '"', "'", '\n', '[', ']', '{', '}'))
    if needs_quoting or value.lower() in ("true", "false", "null", "yes", "no"):
        escaped = value.replace('"', '\\"')
        return f'"{escaped}"'
    return value


def _render_column(col: dict[str, Any]) -> list[str]:
    """Render a single column as YAML lines (without leading '-')."""
    lines: list[str] = []

    def add(key: str, val: Any) -> None:
        if isinstance(val, bool):
            lines.append(f"      {key}: {'true' if val else 'false'}")
        elif isinstance(val, int):
            lines.append(f"      {key}: {val}")
        elif val is None:
            lines.append(f"      {key}: null  # TODO: check value")
        elif str(val).startswith("# TODO"):
            lines.append(f"      {key}: {val}")
        else:
            lines.append(f"      {key}: {_yaml_str(str(val))}")

    add("name", col["name"])
    add("logical_type", col["logical_type"])

    # type modifiers
    if "max_length" in col:
        add("max_length", col["max_length"])
    if "precision" in col and col.get("logical_type") in ("decimal", "timestamp"):
        add("precision", col["precision"])
    if "scale" in col and col.get("logical_type") == "decimal":
        add("scale", col["scale"])

    add("nullable", col["nullable"])

    if col.get("identity"):
        add("identity", True)

    if col.get("description"):
        desc = col["description"].replace('"', '\\"')
        lines.append(f'      description: "{desc}"')

    if col.get("foreign_key"):
        fk = col["foreign_key"]
        lines.append("      foreign_key:")
        lines.append(f"        table: {fk['table']}")
        lines.append(f"        column: {fk['column']}")

    return lines


def render_table_yaml(
    table_id: str,
    table_part: dict[str, Any],
    columns: list[dict[str, Any]],
    primary_key: list[str],
) -> str:
    pascal = TABLE_NAME_MAP.get(table_id, table_id)
    description = table_part.get("Description", "").replace('"', '\\"')

    out: list[str] = [
        '_format_version: "1.0"',
        "table:",
        f"  name: {pascal}",
        "  schema: dbo",
        f'  description: "{description}"',
        "",
        "  columns:",
    ]

    for col in columns:
        col_lines = _render_column(col)
        out.append(f"    - {col_lines[0].lstrip()}")
        for line in col_lines[1:]:
            out.append(line)

    out.append("")
    pk_list = "[" + ", ".join(primary_key) + "]"
    out.append(f"  primary_key: {pk_list}")
    out.append("")

    return "\n".join(out)


# ---------------------------------------------------------------------------
# Main generation logic
# ---------------------------------------------------------------------------

def build_columns_for_table(
    table_id: str,
    all_parts: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[str]]:
    """Return (columns, primary_key_col_names) for the given table_id."""

    # Collect fields that appear in this table
    field_parts: list[tuple[dict[str, Any], dict[str, Any]]] = []  # (part, presence_info)
    for part in all_parts:
        role_set = COLUMN_ROLES
        tp = part.get("table_presence")
        if not tp or not isinstance(tp, dict):
            continue
        if table_id not in tp:
            continue
        presence = tp[table_id]
        role = presence.get("role", "")
        if role not in role_set:
            continue
        field_parts.append((part, presence))

    # Sort by presence order, fallback to global Sort_order
    field_parts.sort(key=lambda x: (x[1].get("order") or 999, x[0].get("Sort_order") or 999))

    # Determine which Part_IDs are sole PKs (role == "key") vs composite
    sole_keys = [
        p for p, pr in field_parts if pr.get("role") == "key"
    ]
    composite_first = [
        p for p, pr in field_parts if pr.get("role") == "compositeKeyFirst"
    ]
    composite_second = [
        p for p, pr in field_parts if pr.get("role") == "compositeKeySecond"
    ]

    # Build primary key list (column names after prefix-stripping)
    pk_parts = sole_keys + composite_first + composite_second
    primary_key: list[str] = []

    columns: list[dict[str, Any]] = []

    for part, presence in field_parts:
        part_id: str = part["Part_ID"]
        role: str = presence.get("role", "property")

        col_name = derive_column_name(part_id, table_id)

        type_attrs = map_sql_type(part.get("SQL_data_type"))

        is_required = part.get("Is_required", False) or False
        nullable = not is_required

        # identity: true only for sole primary keys (not composite)
        is_sole_pk = role == "key" and part_id in [p["Part_ID"] for p in sole_keys]
        identity = is_sole_pk  # sole PK columns get identity; composite keys do not

        col: dict[str, Any] = {"name": col_name, **type_attrs, "nullable": nullable}
        if identity:
            col["identity"] = True
        if part.get("Description"):
            col["description"] = part["Description"]

        # Foreign key: a column is a FK if:
        # 1. It ends with _ID
        # 2. In this table it has role "property" OR "compositeKeyFirst" / "compositeKeySecond"
        #    (i.e. not the primary key of THIS table — unless it references another table)
        # We look across ALL table_presence for this part to find where role == "key"
        # and that table is different from the current table.
        is_pk_of_this_table = role == "key" and not any(
            tbl != table_id and pr2.get("role") == "key"
            for tbl, pr2 in part.get("table_presence", {}).items()
        )

        fk_target: tuple[str, str] | None = None
        if part_id.upper().endswith("_ID"):
            # Find table where this part is the primary key (role=="key").
            # When multiple tables share the same PK column (e.g. Watershed_ID is
            # the PK of watershed, hydrological_characteristics, and
            # urban_characteristics), prefer the table whose Part_ID matches the
            # field name root (e.g. "Watershed_ID" → prefer table "watershed").
            tp_all = part.get("table_presence", {})
            field_root = part_id[: -len("_ID")].lower()  # e.g. "watershed"

            # Collect all candidate tables where this field is a key
            key_candidates: list[str] = [
                tbl for tbl, pr2 in tp_all.items()
                if tbl != table_id and pr2.get("role") == "key"
            ]

            if key_candidates:
                # Prefer candidate whose table ID matches the field root
                preferred = next(
                    (t for t in key_candidates if t.lower() == field_root),
                    key_candidates[0],
                )
                ref_pascal = TABLE_NAME_MAP.get(preferred)
                if ref_pascal:
                    ref_col = derive_column_name(part_id, preferred)
                    fk_target = (ref_pascal, ref_col)

        if fk_target and role != "key":
            col["foreign_key"] = {"table": fk_target[0], "column": fk_target[1]}
        elif fk_target and role in ("compositeKeyFirst", "compositeKeySecond"):
            # Composite key columns that reference another table — still add FK
            col["foreign_key"] = {"table": fk_target[0], "column": fk_target[1]}

        columns.append(col)

        if part_id in [p["Part_ID"] for p in pk_parts]:
            if col_name not in primary_key:
                primary_key.append(col_name)

    return columns, primary_key


def main() -> None:
    if not DICT_PATH.exists():
        print(f"ERROR: dictionary not found at {DICT_PATH}", file=sys.stderr)
        sys.exit(1)

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    with DICT_PATH.open(encoding="utf-8") as fh:
        data: dict[str, Any] = json.load(fh)

    all_parts: list[dict[str, Any]] = data["parts"]

    # Gather all table parts
    table_parts: list[dict[str, Any]] = [
        p for p in all_parts if p.get("Part_type") == "table"
    ]

    created: list[str] = []
    skipped: list[str] = []

    for table_part in table_parts:
        table_id: str = table_part["Part_ID"]
        pascal = TABLE_NAME_MAP.get(table_id)

        if pascal is None:
            print(f"WARNING: no PascalCase mapping for table '{table_id}' — skipping")
            continue

        if pascal in SKIP_TABLES:
            skipped.append(pascal)
            continue

        try:
            columns, primary_key = build_columns_for_table(table_id, all_parts)

            if not primary_key:
                print(f"WARNING: no primary key found for table '{table_id}'")

            yaml_text = render_table_yaml(table_id, table_part, columns, primary_key)

            out_path = OUT_DIR / f"{pascal}.yaml"
            out_path.write_text(yaml_text, encoding="utf-8")
            created.append(str(out_path))
            print(f"  Created: {out_path.relative_to(REPO_ROOT)}")

        except Exception as exc:  # noqa: BLE001
            print(f"ERROR generating {pascal}: {exc}", file=sys.stderr)
            import traceback
            traceback.print_exc()

    print()
    print(f"Done. {len(created)} file(s) created, {len(skipped)} skipped ({', '.join(skipped)}).")


if __name__ == "__main__":
    main()
