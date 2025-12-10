#!/usr/bin/env python3
"""
Documentation generation orchestrator.

This script coordinates the generation of all documentation components:
- Dictionary reference (tables and value sets)
- ERD diagrams
- SQL schemas
- Asset copying

Usage:
    python generate_docs.py <json_path> <docs_dir> <sql_dir> <assets_dir> [target_dbs]
"""

import sys
import subprocess
from pathlib import Path

# Add scripts to path to import our modules
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from generate_dictionary_reference import (
    parse_parts_json,
    generate_tables_markdown,
    generate_value_sets_markdown,
)
from generate_erd import parse_erd_json, generate_erd_files
from generate_sql import parse_parts_json as parse_sql_json, generate_sql_schemas


def copy_generated_assets(assets_dir):
    """Copy generated HTML assets to be served by MkDocs."""

    # Files to copy - specifically the generated ERD files
    generated_files = ["erd_interactive.html"]

    print(f"Checking for assets in {assets_dir.absolute()}")

    for filename in generated_files:
        source_path = assets_dir / filename
        if source_path.exists():
            # Target path in built site (assets/filename)
            target_path = f"assets/{filename}"

            print(f"Copying {filename} -> {target_path}")

            # Use mkdocs_gen_files to register the file with MkDocs
            try:
                import mkdocs_gen_files

                content = source_path.read_text(encoding="utf-8")
                with mkdocs_gen_files.open(target_path, "w") as f:
                    f.write(content)
            except ImportError:
                print(
                    "Warning: mkdocs_gen_files not available, assets may not be included in build"
                )
            except Exception as e:
                print(f"Error copying {filename}: {e}")
        else:
            print(f"Warning: Expected asset {filename} not found in {assets_dir}")


def main():
    """Main entry point for orchestrator."""
    if len(sys.argv) < 5:
        print(
            "Usage: python generate_docs.py <json_path> <docs_dir> <sql_dir> <assets_dir> [target_dbs]"
        )
        print(
            "Example: python generate_docs.py src/dictionary.json docs/reference sql_generation_scripts docs/assets mssql"
        )
        sys.exit(1)

    json_path = Path(sys.argv[1])
    docs_dir = Path(sys.argv[2])
    sql_dir = Path(sys.argv[3])
    assets_dir = Path(sys.argv[4])

    # Default to mssql if no databases specified
    target_dbs = sys.argv[5].split(",") if len(sys.argv) > 5 else ["mssql"]

    # Ensure directories exist
    docs_dir.mkdir(parents=True, exist_ok=True)
    sql_dir.mkdir(parents=True, exist_ok=True)
    assets_dir.mkdir(parents=True, exist_ok=True)

    print(f"Generating documentation from {json_path}")
    print(f"Output directories:")
    print(f"  Docs: {docs_dir}")
    print(f"  SQL: {sql_dir}")
    print(f"  Assets: {assets_dir}")
    print(f"  Target databases: {target_dbs}")

    # Parse JSON once (each script can parse independently)
    parts_data = parse_parts_json(json_path)

    # Generate dictionary reference
    print("\n=== Generating Dictionary Reference ===")
    tables = generate_tables_markdown(parts_data)
    value_sets = generate_value_sets_markdown(parts_data)

    (docs_dir / "tables.md").write_text(tables, encoding="utf-8")
    print(f"Generated tables documentation: {docs_dir / 'tables.md'}")

    (docs_dir / "valuesets.md").write_text(value_sets, encoding="utf-8")
    print(f"Generated value sets documentation: {docs_dir / 'valuesets.md'}")

    # Generate ERD
    print("\n=== Generating ERD ===")
    erd_parts_data = parse_erd_json(json_path)
    generate_erd_files(erd_parts_data, assets_dir, docs_dir)

    # Generate SQL schemas
    print("\n=== Generating SQL Schemas ===")
    sql_parts_data = parse_sql_json(json_path)
    generate_sql_schemas(sql_parts_data, sql_dir, target_dbs)

    # Copy assets
    print("\n=== Copying Assets ===")
    copy_generated_assets(assets_dir)

    print("\n=== Documentation Generation Complete ===")
    print("All components generated successfully!")


if __name__ == "__main__":
    main()
