#!/usr/bin/env python3
"""
Generate all documentation and SQL artifacts from the YAML schema dictionary.

Usage:
    python scripts/generate_from_yaml.py <tables_dir> <views_dir> <docs_dir> <assets_dir> <sql_dir> [platform] [version]

Example:
    python scripts/generate_from_yaml.py \\
        schema_dictionary/tables \\
        schema_dictionary/views \\
        docs/reference \\
        docs/assets \\
        sql_generation_scripts \\
        mssql \\
        0.2.0
"""

import sys
from pathlib import Path
from typing import Any

# Add project root to path for tool imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from tools.schema_migrate.loader import load_schema, load_views
from tools.schema_migrate.render import render_column_type, render_create_script_with_views

# Add scripts dir to path for doc generators
scripts_dir = Path(__file__).parent
sys.path.insert(0, str(scripts_dir))

from legacy.generate_dictionary_reference import generate_tables_markdown, generate_views_markdown
from legacy.generate_erd import generate_erd_data, generate_erd_html


def parse_yaml_for_docs(
    tables_dir: Path,
    views_dir: Path,
    platform: str = "mssql",
) -> dict[str, Any]:
    """Parse YAML schema files into the parts_data dict format expected by doc generators.

    Reads all table and view YAML files from the given directories and transforms
    them into the legacy parts_data structure consumed by ``generate_tables_markdown``,
    ``generate_views_markdown``, ``generate_erd_data``, etc.

    Args:
        tables_dir: Path to directory containing one ``.yaml`` file per table.
        views_dir: Path to directory containing one ``.yaml`` file per view.
        platform: SQL platform for type rendering (``'mssql'`` or ``'postgres'``).

    Returns:
        A dict with keys ``"tables"``, ``"views"``, ``"value_sets"``,
        ``"id_field_locations"``, and ``"metadata"``.
    """
    schema = load_schema(tables_dir)
    views = load_views(views_dir)

    parts_data: dict[str, Any] = {
        "tables": {},
        "value_sets": {},
        "views": {},
        "id_field_locations": {},
        "metadata": {},
    }

    # Build tables
    for table_name, table_doc in schema.items():
        table = table_doc["table"]
        primary_keys: list[str] = table.get("primary_key", [])
        columns: list[dict] = table.get("columns", [])

        fields: list[dict[str, Any]] = []
        for sort_order, col in enumerate(columns):
            col_name: str = col["name"]
            is_pk = col_name in primary_keys
            part_type = "key" if is_pk else "property"

            fk_info = col.get("foreign_key")
            fk_to = fk_info["column"] if fk_info else ""
            fk_ref_table = fk_info["table"] if fk_info else ""

            sql_data_type = render_column_type(col, platform)

            field: dict[str, Any] = {
                "part_id": col_name,
                "label": col_name,
                "description": col.get("description", ""),
                "part_type": part_type,
                "sql_data_type": sql_data_type,
                "is_required": not col.get("nullable", True),
                "default_value": str(col["default"]) if col.get("default") is not None else "",
                "fk_to": fk_to,
                "fk_ref_table": fk_ref_table,
                "relationship_type": None,
                "value_set": "",
                "sort_order": sort_order,
            }
            fields.append(field)

        parts_data["tables"][table_name] = {
            "label": table_name,
            "description": table.get("description", ""),
            "fields": fields,
        }

    # Build views
    for view_name, view_doc in views.items():
        view = view_doc["view"]
        view_columns: list[dict] = view.get("columns", [])

        columns_out: list[dict[str, Any]] = []
        for sort_order, col in enumerate(view_columns):
            col_out: dict[str, Any] = {
                "part_id": col["name"],
                "label": col["name"],
                "description": col.get("description", ""),
                "source_field_part_id": col.get("source_column", col["name"]),
                "sql_data_type": col.get("sql_data_type", ""),
                "sort_order": sort_order,
            }
            columns_out.append(col_out)

        parts_data["views"][view_name] = {
            "label": view_name,
            "description": view.get("description", ""),
            "view_definition": view.get("view_definition", ""),
            "columns": columns_out,
        }

    return parts_data


def parse_yaml_for_erd(
    tables_dir: Path,
    views_dir: Path,
    platform: str = "mssql",
) -> dict[str, Any]:
    """Parse YAML schema files into parts_data for ERD generation.

    This is an alias for ``parse_yaml_for_docs``; both use the same format.

    Args:
        tables_dir: Path to directory containing table YAML files.
        views_dir: Path to directory containing view YAML files.
        platform: SQL platform for type rendering.

    Returns:
        parts_data dict compatible with ``generate_erd_data``.
    """
    return parse_yaml_for_docs(tables_dir, views_dir, platform)


def _generate_erd_markdown(parts_data: dict[str, Any], erd_data: dict[str, Any]) -> str:
    return f"""# Entity Relationship Diagram (ERD)

This interactive diagram shows all tables, views, and their relationships in datEAUbase schema.

## Interactive ERD

The interactive version allows you to:
- 🖱️ **Drag tables/views** to rearrange layout
- 🔍 **Zoom in/out** for better visibility
- 📐 **Auto-layout** to reorganize tables automatically
- 💾 **Export** diagram as PNG

<iframe src="../../assets/erd_interactive.html" width="100%" height="800px" frameborder="0" style="border: 2px solid #e2e8f0; border-radius: 8px;"></iframe>

[Open in new window](../assets/erd_interactive.html){{: target="_blank" .md-button .md-button--primary}}

## Legend

### Entity Types

| Marker | Description |
|--------|-------------|
| **Table** | Physical database table with primary keys, foreign keys, and properties |
| **View** | Virtual table defined by a SQL query (shown with distinct styling) |

### Field Markers
- **PK** badge: Primary Key - Unique identifier for each record
- **FK** badge: Foreign Key - Reference to another table's primary key
- **\\*** Required field (NOT NULL)

### Relationship Notation
Relationships use standard crow's foot notation:
- **Single line (|)**: "One" side of relationship
- **Crow's foot (⟨)**: "Many" side of relationship

**Relationship Types:**
- **One-to-One**: Single line on both ends (e.g., watershed ↔ hydrological_characteristics)
- **One-to-Many**: Crow's foot on child side, single line on parent (e.g., site ↔ sampling_points)
- **Many-to-Many**: Crow's foot on both ends (via junction tables like project_has_contact)

## Statistics

The current schema contains:
- **{len(parts_data["tables"])}** tables
- **{len(parts_data.get("views", {}))}** views
- **{len(erd_data["relationships"])}** relationships
"""


def generate_all_from_yaml(
    tables_dir: Path,
    views_dir: Path,
    docs_dir: Path,
    assets_dir: Path,
    sql_dir: Path,
    platform: str = "mssql",
    version: str = "0.1.0",
) -> None:
    """Orchestrate generation of all documentation and SQL artifacts from YAML sources.

    Steps performed:
    1. Parse all table and view YAML files into ``parts_data``.
    2. Write ``docs_dir/tables.md`` via ``generate_tables_markdown``.
    3. Write ``docs_dir/views.md`` via ``generate_views_markdown``.
    4. Write ``assets_dir/erd_interactive.html`` via ``generate_erd_html``.
    5. Write ``docs_dir/erd.md`` - the ERD documentation page.
    6. Write ``sql_dir/v{version}_create_{platform}.sql`` via
       ``render_create_script_with_views``.

    Args:
        tables_dir: Directory containing table YAML files.
        views_dir: Directory containing view YAML files.
        docs_dir: Directory to write Markdown reference pages into.
        assets_dir: Directory to write ``erd_interactive.html`` into.
        sql_dir: Directory to write the generated SQL CREATE script into.
        platform: Target SQL platform (``'mssql'`` or ``'postgres'``).
        version: Schema version string used in the SQL filename.
    """
    tables_dir = Path(tables_dir)
    views_dir = Path(views_dir)
    docs_dir = Path(docs_dir)
    assets_dir = Path(assets_dir)
    sql_dir = Path(sql_dir)

    docs_dir.mkdir(parents=True, exist_ok=True)
    assets_dir.mkdir(parents=True, exist_ok=True)
    sql_dir.mkdir(parents=True, exist_ok=True)

    # Step 1: parse YAML into parts_data
    parts_data = parse_yaml_for_docs(tables_dir, views_dir, platform)

    # Step 2: tables.md
    tables_md = generate_tables_markdown(parts_data)
    tables_path = docs_dir / "tables.md"
    tables_path.write_text(tables_md, encoding="utf-8")
    print(f"Generated tables documentation: {tables_path}")

    # Step 3: views.md
    views_md = generate_views_markdown(parts_data)
    views_path = docs_dir / "views.md"
    views_path.write_text(views_md, encoding="utf-8")
    print(f"Generated views documentation: {views_path}")

    # Step 4: interactive ERD HTML
    erd_data = generate_erd_data(parts_data)
    erd_html_path = assets_dir / "erd_interactive.html"
    generate_erd_html(erd_data, erd_html_path, library="jointjs")
    print(f"Generated interactive ERD: {erd_html_path}")

    # Step 5: erd.md
    erd_md = _generate_erd_markdown(parts_data, erd_data)
    erd_md_path = docs_dir / "erd.md"
    erd_md_path.write_text(erd_md, encoding="utf-8")
    print(f"Generated ERD documentation page: {erd_md_path}")

    # Step 6: SQL CREATE script
    schema = load_schema(tables_dir)
    views = load_views(views_dir)
    sql_script = render_create_script_with_views(schema, views, version, platform)
    sql_path = sql_dir / f"v{version}_create_{platform}.sql"
    sql_path.write_text(sql_script, encoding="utf-8")
    print(f"Generated SQL CREATE script: {sql_path}")


def main() -> None:
    """CLI entry point.

    Usage:
        python generate_from_yaml.py <tables_dir> <views_dir> <docs_dir> <assets_dir> <sql_dir> [platform] [version]
    """
    if len(sys.argv) < 6:
        print(
            "Usage: python generate_from_yaml.py "
            "<tables_dir> <views_dir> <docs_dir> <assets_dir> <sql_dir> "
            "[platform] [version]"
        )
        print(
            "Example: python scripts/generate_from_yaml.py "
            "schema_dictionary/tables schema_dictionary/views "
            "docs/reference docs/assets sql_generation_scripts "
            "mssql 0.1.0"
        )
        sys.exit(1)

    tables_dir = Path(sys.argv[1])
    views_dir = Path(sys.argv[2])
    docs_dir = Path(sys.argv[3])
    assets_dir = Path(sys.argv[4])
    sql_dir = Path(sys.argv[5])
    platform = sys.argv[6] if len(sys.argv) > 6 else "mssql"
    version = sys.argv[7] if len(sys.argv) > 7 else "0.1.0"

    generate_all_from_yaml(
        tables_dir=tables_dir,
        views_dir=views_dir,
        docs_dir=docs_dir,
        assets_dir=assets_dir,
        sql_dir=sql_dir,
        platform=platform,
        version=version,
    )


if __name__ == "__main__":
    main()
