#!/usr/bin/env python3
"""
Generate SQL schema from dictionary.

This script extracts SQL generation logic from the main generate_docs hook
to create a modular, testable component.

Usage:
    python generate_sql.py <json_path> <output_path> <target_dbs>
"""

import sys
import json
from pathlib import Path
from datetime import datetime
from importlib.metadata import version

# Add src to path to import models
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from open_dateaubase.data_model.models import Dictionary

package_version = version("open-dateaubase")


def parse_parts_json(json_path):
    """
    Parse dictionary.json using Pydantic validation.
    Returns same dict structure as parse_parts_table() for compatibility.
    """
    # Load and validate
    with open(json_path, "r", encoding="utf-8") as f:
        raw_data = json.load(f)

    # Pydantic validation
    dictionary = Dictionary.model_validate(raw_data)

    # Transform to legacy format for generators
    data = {"tables": {}, "value_sets": {}, "metadata": {}, "id_field_locations": {}}

    # Process tables
    for part in dictionary.parts:
        if part.part_type == "table":
            data["tables"][part.part_id] = {
                "label": part.label,
                "description": part.description,
                "fields": [],
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

    return data


def generate_sql_schemas(parts_data, output_path, db_list):
    """Generate SQL schemas for multiple database types."""
    for target_db in db_list:
        sql_schema = generate_sql_schema(parts_data, target_db=target_db)
        version_str = package_version
        filename = f"v{version_str}_as-designed_{target_db}.sql"
        (output_path / filename).write_text(sql_schema, encoding="utf-8")
        print(f"Generated SQL schema for {target_db} at {output_path / filename}")


def generate_sql_schema(data, target_db="mssql", include_timestamp=True):
    """
    Generate SQL CREATE statements from parsed metadata.

    Args:
        data: Parsed parts table data
        target_db: Target database flavor ('mssql', 'postgres', 'mysql' - future)
        include_timestamp: Whether to include generation timestamp (default: True)

    Returns:
        SQL DDL as a string

    Raises:
        ValueError: If circular foreign key dependencies detected
    """
    # Validate no circular FK dependencies
    validate_no_circular_fks(data)

    sql = ["-- Auto-generated SQL schema from dictionary.json"]
    sql.append(f"-- Target database: {target_db.upper()}")
    if include_timestamp:
        sql.append(f"-- Generated: {datetime.now().isoformat()}")
    sql.append("\n")

    # Get DB-specific config
    db_config = get_db_config(target_db)

    # First pass: Create all tables without foreign keys
    for table_id, table_info in sorted(data["tables"].items()):
        sql.append(f"\n-- {table_info['description']}")
        sql.append(f"CREATE TABLE {db_config['quote'](table_id)} (")

        field_definitions = []
        pk_fields = []

        for field in table_info["fields"]:
            field_def = generate_field_definition(field, data, db_config)
            field_definitions.append(field_def)

            # Track primary key fields
            if field["part_type"] in ["key", "compositeKeyFirst", "compositeKeySecond"]:
                field_name = extract_field_name(field["part_id"])
                pk_fields.append(f"{db_config['quote'](field_name)}")

        # Add primary key constraint
        if pk_fields:
            pk_name = "PK_" + table_id
            pk_constraint = f"    CONSTRAINT {db_config['quote'](pk_name)} PRIMARY KEY ({', '.join(pk_fields)})"
            field_definitions.append(pk_constraint)

        sql.append(",\n".join(field_definitions))
        sql.append(");\n")

    # Second pass: Add foreign key constraints
    sql.append("\n-- Foreign Key Constraints\n")
    for table_id, table_info in sorted(data["tables"].items()):
        for field in table_info["fields"]:
            if field["fk_to"]:
                fk_sql = generate_foreign_key_constraint(table_id, field, data, db_config)
                if fk_sql:
                    sql.append(fk_sql)

    return "\n".join(sql)


def get_db_config(target_db):
    """
    Get database-specific configuration.

    Args:
        target_db: Database flavor string

    Returns:
        Dict with DB-specific settings
    """
    configs = {
        "mssql": {
            "quote_char": "[",
            "quote_char_end": "]",
            "type_mappings": {
                "nvarchar": "nvarchar",
                "ntext": "nvarchar(max)",  # ntext deprecated in modern MSSQL
                "int": "int",
                "float": "float",
                "real": "real",
                "numeric": "numeric",
                "bit": "bit",
            },
            "supports_check_constraints": True,
            "supports_deferred_constraints": False,
        },
        # Future: postgres, mysql, sqlite configs
    }

    if target_db not in configs:
        raise ValueError(
            f"Unsupported database: {target_db}. Supported: {list(configs.keys())}"
        )

    config = configs[target_db]

    # Add convenience method for quoting identifiers
    if config["quote_char_end"]:
        config["quote"] = (
            lambda name: f"{config['quote_char']}{name}{config['quote_char_end']}"
        )
    else:
        config["quote"] = (
            lambda name: f"{config['quote_char']}{name}{config['quote_char_end']}"
        )

    return config


def extract_field_name(part_id):
    """
    Extract field name from Part_ID.

    NEW FORMAT handling:
    - ID fields (e.g., 'Equipment_ID', 'Project_ID'): Use as-is (these are actual SQL field names)
    - Table-prefixed fields (e.g., 'site_City', 'purpose_Description'): Remove table prefix
    - Non-prefixed fields: Use as-is

    Args:
        part_id: Part_ID from dictionary

    Returns:
        Field name to use in SQL
    """
    # ID fields are used as-is in SQL
    if part_id.endswith("_ID"):
        return part_id

    # Table-prefixed non-ID fields: remove prefix
    # Format is lowercase_table_MixedCaseField (e.g., 'site_City', 'contact_City')
    if "_" in part_id:
        # Check if first part looks like a table name (lowercase)
        parts = part_id.split("_", 1)
        if len(parts) == 2 and parts[0].islower():
            # This is likely a table-prefixed field, remove prefix
            return parts[1]

    # Otherwise use as-is
    return part_id


def validate_no_circular_fks(data):
    """
    Check for circular foreign key dependencies between tables.

    Args:
        data: Parsed parts table data

    Raises:
        ValueError: If circular FK dependencies found
    """
    # Build adjacency list of FK relationships
    fk_graph = {table_id: set() for table_id in data["tables"]}

    for table_id, table_info in data["tables"].items():
        for field in table_info["fields"]:
            if field["fk_to"] and "_" in field["fk_to"]:
                target_table = field["fk_to"].split("_", 1)[0]
                if target_table in fk_graph:
                    fk_graph[table_id].add(target_table)

    # Check for bidirectional relationships (A->B and B->A)
    circular_deps = []
    for table_a, targets in fk_graph.items():
        for table_b in targets:
            if table_b == table_a:
                # self-referential FKs are allowed
                continue
            if table_a in fk_graph.get(table_b, set()):
                # Found circular dependency
                pair = tuple(sorted([table_a, table_b]))
                if pair not in circular_deps:
                    circular_deps.append(pair)

    if circular_deps:
        error_msg = "Circular foreign key dependencies detected:\n"
        for table_a, table_b in circular_deps:
            error_msg += f"  - {table_a} ↔ {table_b}\n"
        error_msg += "\nEach pair of tables has FKs pointing to each other, which creates ambiguity in table creation order."
        raise ValueError(error_msg)


def generate_field_definition(field, data, db_config):
    """
    Generate SQL field definition with constraints.

    Args:
        field: Field metadata dict
        data: Full parsed data (for value set lookups)
        db_config: Database-specific configuration

    Returns:
        SQL field definition string
    """
    field_name = extract_field_name(field["part_id"])

    quote = db_config["quote"]

    parts = [f"    {quote(field_name)}"]

    # Data type with mapping
    sql_type = field["sql_data_type"] if field["sql_data_type"] else "nvarchar(255)"
    # Apply type mapping for target DB
    base_type = sql_type.split("(")[
        0
    ]  # Extract base type (e.g., 'nvarchar' from 'nvarchar(255)')
    if base_type in db_config["type_mappings"]:
        # Preserve parameters if they exist
        if "(" in sql_type:
            params = sql_type[sql_type.index("(") :]
            sql_type = db_config["type_mappings"][base_type].split("(")[0] + params
        else:
            sql_type = db_config["type_mappings"][base_type]

    parts.append(sql_type)

    # NULL constraint
    if field["is_required"]:
        parts.append("NOT NULL")
    else:
        parts.append("NULL")

    # Default value
    if field["default_value"]:
        default_val = field["default_value"]
        # Handle boolean defaults
        if default_val in ["True", "False"]:
            default_val = "1" if default_val == "True" else "0"
        # Handle numeric vs string defaults
        if field["sql_data_type"] and field["sql_data_type"].split("(")[0] in [
            "int",
            "float",
            "real",
            "numeric",
            "bit",
        ]:
            parts.append(f"DEFAULT {default_val}")
        else:
            parts.append(f"DEFAULT '{default_val}'")

    # Note: Value set CHECK constraints removed per requirement #3
    # Future: could add back conditionally based on target_db config

    return " ".join(parts)


def generate_foreign_key_constraint(table_id, field, data, db_config):
    """
    Generate ALTER TABLE statement for foreign key.

    NEW FORMAT: fk_to is Part_ID of target field (e.g., 'TestTable_ID')
    We need to find which table has this field as a primary key by looking up
    the table Part_ID from the data model.

    Args:
        table_id: Source table ID
        field: Field metadata with FK reference
        data: Full parsed data (for id_field_locations lookup)
        db_config: Database-specific configuration

    Returns:
        SQL ALTER TABLE statement or None
    """
    if not field["fk_to"]:
        return None

    # fk_to is Part_ID of target (e.g., 'TestTable_ID')
    fk_target = field["fk_to"]
    source_field = extract_field_name(field["part_id"])

    # For ID fields like 'TestTable_ID', extract table name from FK field
    # This preserves the capitalization pattern from the data model
    if fk_target.endswith("_ID"):
        target_field = fk_target  # e.g., 'TestTable_ID'
        # Extract table name from FK field name (e.g., 'Equipment_model_ID' -> 'Equipment_model')
        # This matches the capitalization used in the original data model design
        target_table = fk_target[:-3]  # Remove '_ID'
    else:
        # Non-ID FK (shouldn't happen in new format, but fallback)
        return None

    quote = db_config["quote"]
    constraint_name = f"FK_{table_id}_{source_field}"

    sql = f"""ALTER TABLE {quote(table_id)}
    ADD CONSTRAINT {quote(constraint_name)}
    FOREIGN KEY ({quote(source_field)})
    REFERENCES {quote(target_table)} ({quote(target_field)});
"""

    return sql


def main():
    """Main entry point for script."""
    if len(sys.argv) != 4:
        print("Usage: python generate_sql.py <json_path> <output_path> <target_dbs>")
        print(
            "Example: python generate_sql.py dictionary.json sql_generation_scripts mssql"
        )
        sys.exit(1)

    json_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2])
    db_list = sys.argv[3].split(",")  # Comma-separated list of databases

    # Ensure output directory exists
    output_path.mkdir(parents=True, exist_ok=True)

    # Parse JSON
    parts_data = parse_parts_json(json_path)

    # Generate SQL schemas
    generate_sql_schemas(parts_data, output_path, db_list)


if __name__ == "__main__":
    main()
