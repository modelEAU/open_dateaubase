#!/usr/bin/env python3
"""
Generate dictionary reference documentation (tables and value sets).

This script extracts table and value set generation logic from the main
generate_docs hook to create modular, testable components.

Usage:
    python generate_dictionary_reference.py <json_path> <output_path>
"""

import sys
import json
from pathlib import Path


def parse_parts_json(json_path):
    """
    Parse dictionary.json using Pydantic validation.
    Returns same dict structure as parse_parts_table() for compatibility.
    """
    # Add src to path to import models
    project_root = Path(json_path).parent.parent
    sys.path.insert(0, str(project_root / "src"))

    from open_dateaubase.data_model.models import Dictionary, ViewPart, ViewColumnPart

    # Load and validate
    with open(json_path, "r", encoding="utf-8") as f:
        raw_data = json.load(f)

    # Pydantic validation
    dictionary = Dictionary.model_validate(raw_data)

    # Transform to legacy format for generators
    data = {
        "tables": {},
        "value_sets": {},
        "metadata": {},
        "id_field_locations": {},
        "views": {},
    }

    # Process tables
    for part in dictionary.parts:
        if part.part_type == "table":
            data["tables"][part.part_id] = {
                "label": part.label,
                "description": part.description,
                "fields": [],
            }

    # Process views
    for part in dictionary.parts:
        if part.part_type == "view":
            data["views"][part.part_id] = {
                "label": part.label,
                "description": part.description,
                "view_definition": part.view_definition,
                "columns": [],
            }

    # Process fields
    for part in dictionary.parts:
        # Only process field parts that have table_presence
        if hasattr(part, "table_presence") and part.part_type in [
            "key",
            "property",
            "compositeKeyFirst",
            "compositeKeySecond",
            "parentKey",
        ]:
            for table_name, presence in part.table_presence.items():
                if table_name not in data["tables"]:
                    continue

                # Track ID field locations
                if part.part_id.endswith("_ID"):
                    if part.part_id not in data["id_field_locations"]:
                        data["id_field_locations"][part.part_id] = {}
                    data["id_field_locations"][part.part_id][table_name] = presence.role

                # Determine FK target and relationship type from explicit metadata
                fk_to = ""
                relationship_type = None
                if part.part_type == "parentKey":
                    fk_to = part.ancestor_part_id
                elif presence.relationship_type:
                    # Infer FK target from field name (field ending in _ID references same-named primary key)
                    if part.part_id.endswith("_ID"):
                        fk_to = part.part_id
                    relationship_type = presence.relationship_type

                field_info = {
                    "part_id": part.part_id,
                    "label": part.label,
                    "description": part.description,
                    "part_type": presence.role,
                    "sql_data_type": getattr(part, "sql_data_type", None) or "",
                    "is_required": presence.required,
                    "default_value": getattr(part, "default_value", None) or "",
                    "fk_to": fk_to,
                    "relationship_type": relationship_type,
                    "value_set": getattr(part, "value_set_part_id", None) or "",
                    "sort_order": presence.order,
                }
                data["tables"][table_name]["fields"].append(field_info)

    # Process value sets
    for part in dictionary.parts:
        if part.part_type == "valueSet":
            data["value_sets"][part.part_id] = {
                "label": part.label,
                "description": part.description,
                "members": [],
            }

    for part in dictionary.parts:
        if part.part_type == "valueSetMember":
            value_set_id = part.member_of_set_part_id
            if value_set_id in data["value_sets"]:
                member_info = {
                    "part_id": part.part_id,
                    "label": part.label,
                    "description": part.description,
                    "sort_order": part.sort_order if part.sort_order else 999,
                }
                data["value_sets"][value_set_id]["members"].append(member_info)

    # Sort fields and members
    for table in data["tables"].values():
        table["fields"].sort(key=lambda x: x["sort_order"])

    for value_set in data["value_sets"].values():
        value_set["members"].sort(key=lambda x: x["sort_order"])

    # Process view columns
    for part in dictionary.parts:
        if part.part_type == "viewColumn":
            for view_name, view_meta in part.view_presence.items():
                if view_name not in data["views"]:
                    continue

                col_info = {
                    "part_id": part.part_id,
                    "label": part.label,
                    "description": part.description,
                    "source_field_part_id": part.source_field_part_id,
                    "sql_data_type": part.sql_data_type or "",
                    "sort_order": view_meta.get("order", 999),
                }
                data["views"][view_name]["columns"].append(col_info)

    # Sort columns
    for view in data["views"].values():
        view["columns"].sort(key=lambda x: x["sort_order"])

    return data


def generate_tables_markdown(data):
    """
    Generate markdown documentation from parsed data.
    """
    md = ["# Database Tables\n"]
    md.append("This documentation is auto-generated from dictionary.json.\n")

    # Generate table documentation
    md.append("\n## Tables\n")

    for table_id, table_info in sorted(data["tables"].items()):
        # Anchor as invisible span, table name as regular heading
        md.append(f'\n<span id="{table_id}"></span>\n')
        md.append(f"### {table_info['label']}\n")
        md.append(f"{table_info['description']}\n")

        if table_info["fields"]:
            md.append("\n#### Fields\n")
            md.append(
                "| Field | SQL Type | Value Set | Required | Description | Constraints |"
            )
            md.append(
                "|-------|----------|-----------|----------|-------------|-------------|"
            )

            for field in table_info["fields"]:
                field_name = field["label"]
                field_id = field["part_id"]

                # SQL Type column
                sql_type = field["sql_data_type"] if field["sql_data_type"] else "-"
                if field["part_type"] in [
                    "key",
                    "compositeKeyFirst",
                    "compositeKeySecond",
                ]:
                    if field["part_type"] == "key":
                        sql_type += " **(PK)**"
                    elif field["part_type"] == "compositeKeyFirst":
                        sql_type += " **(CK-1)**"
                    elif field["part_type"] == "compositeKeySecond":
                        sql_type += " **(CK-2)**"
                    else:
                        raise ValueError(
                            f"Found unknown part type: {field['part_type']}. Correct dictionary OR update documentation generation code."
                        )

                # Value Set column - link to value set definition
                value_set = (
                    f"[{field['value_set']}](valuesets.md#{field['value_set']})"
                    if field["value_set"]
                    else "-"
                )

                required = "✓" if field["is_required"] else ""

                # Anchor description with Part_ID
                description = f'<span id="{field_id}"></span>{field["description"]}'

                # Build constraints column
                constraints = []
                if field["fk_to"]:
                    # Link to FK target table when available, otherwise fall back to field anchor
                    fk_ref_table = field.get("fk_ref_table", "")
                    if fk_ref_table:
                        constraints.append(f"FK → [{fk_ref_table}.{field['fk_to']}](#{fk_ref_table})")
                    else:
                        constraints.append(f"FK → [{field['fk_to']}](#{field['fk_to']})")
                if field["default_value"]:
                    constraints.append(f"Default: `{field['default_value']}`")

                constraints_str = "<br>".join(constraints) if constraints else "-"

                md.append(
                    f"| {field_name} | {sql_type} | {value_set} | {required} | {description} | {constraints_str} |"
                )

    return "\n".join(md)


def generate_value_sets_markdown(data):
    """
    Generate value set documentation with proper anchoring.
    """
    md = ["# Value Sets\n"]
    md.append("Controlled vocabularies used throughout database.\n")

    if data["value_sets"]:
        for value_set_id, value_set_info in sorted(data["value_sets"].items()):
            # Anchor as invisible span, value set name as regular heading
            md.append(f'\n<span id="{value_set_id}"></span>\n')
            md.append(f"## {value_set_info['label']}\n")
            md.append(f"{value_set_info['description']}\n")

            if value_set_info["members"]:
                md.append("\n| Value | Description |")
                md.append("|-------|-------------|")

                for member in value_set_info["members"]:
                    member_id = member["part_id"]
                    # Anchor each member with its Part_ID
                    md.append(
                        f'| <span id="{member_id}"></span>`{member_id}` | {member["description"]} |'
                    )
    else:
        md.append("No value sets currently appear in dictionary.")

    return "\n".join(md)


def generate_views_markdown(data):
    """
    Generate view documentation with proper anchoring.
    """
    md = ["# Database Views\n"]
    md.append("Virtual tables defined by SQL queries.\n")

    if data.get("views"):
        for view_id, view_info in sorted(data["views"].items()):
            # Anchor as invisible span, view name as regular heading
            md.append(f'\n<span id="{view_id}"></span>\n')
            md.append(f"## {view_info['label']}\n")
            md.append(f"{view_info['description']}\n")

            md.append("\n**View Definition:**\n")
            md.append(f"```sql\n{view_info['view_definition']}\n```\n")

            if view_info["columns"]:
                md.append("\n#### Columns\n")
                md.append("| Column | SQL Type | Source Field | Description |")
                md.append("|--------|----------|--------------|-------------|")

                for col in view_info["columns"]:
                    col_name = col["label"]
                    col_id = col["part_id"]
                    sql_type = col["sql_data_type"] if col["sql_data_type"] else "-"
                    source_field = col.get("source_field_part_id", "-")
                    description = col["description"]

                    md.append(
                        f"| {col_name} | {sql_type} | `{source_field}` | {description} |"
                    )
    else:
        md.append("No views currently appear in dictionary.")

    return "\n".join(md)


def main():
    """Main entry point for script."""
    if len(sys.argv) != 3:
        print(
            "Usage: python generate_dictionary_reference.py <json_path> <output_path>"
        )
        print(
            "Example: python generate_dictionary_reference.py dictionary.json docs/reference"
        )
        sys.exit(1)

    json_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2])

    # Ensure output directory exists
    output_path.mkdir(parents=True, exist_ok=True)

    # Parse JSON
    parts_data = parse_parts_json(json_path)

    # Generate markdown
    tables = generate_tables_markdown(parts_data)
    value_sets = generate_value_sets_markdown(parts_data)
    views = generate_views_markdown(parts_data)

    # Write to files
    (output_path / "tables.md").write_text(tables, encoding="utf-8")
    (output_path / "valuesets.md").write_text(value_sets, encoding="utf-8")
    (output_path / "views.md").write_text(views, encoding="utf-8")

    print(f"Generated dictionary reference documentation:")
    print(f"  Tables: {output_path / 'tables.md'}")
    print(f"  Value sets: {output_path / 'valuesets.md'}")
    print(f"  Views: {output_path / 'views.md'}")


if __name__ == "__main__":
    main()
