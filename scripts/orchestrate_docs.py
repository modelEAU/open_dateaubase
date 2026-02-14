#!/usr/bin/env python3
"""
Documentation generation orchestrator.

Generates all documentation and SQL artifacts from the YAML schema dictionary.
Value sets are still sourced from dictionary.json (not yet in YAML).

Usage:
    python orchestrate_docs.py <json_path> <docs_dir> <sql_dir> <assets_dir> [platform]
"""

import sys
from pathlib import Path

import yaml

# Add scripts to path
project_root = Path(__file__).parent.parent
scripts_dir = Path(__file__).parent
sys.path.insert(0, str(scripts_dir))

from generate_from_yaml import generate_all_from_yaml
from legacy.generate_dictionary_reference import (
    parse_parts_json,
    generate_value_sets_markdown,
)


def copy_generated_assets(assets_dir: Path) -> None:
    """Copy generated HTML assets to be served by MkDocs."""
    generated_files = ["erd_interactive.html"]
    print(f"Checking for assets in {assets_dir.absolute()}")
    for filename in generated_files:
        source_path = assets_dir / filename
        if source_path.exists():
            target_path = f"assets/{filename}"
            print(f"Copying {filename} -> {target_path}")
            try:
                import mkdocs_gen_files

                content = source_path.read_text(encoding="utf-8")
                with mkdocs_gen_files.open(target_path, "w") as f:
                    f.write(content)
            except ImportError:
                print("Warning: mkdocs_gen_files not available")
            except Exception as e:
                print(f"Error copying {filename}: {e}")
        else:
            print(f"Warning: Expected asset {filename} not found in {assets_dir}")


def _read_schema_version(schema_dir: Path) -> str:
    version_yaml = schema_dir / "version.yaml"
    if version_yaml.exists():
        with version_yaml.open(encoding="utf-8") as fh:
            return str(yaml.safe_load(fh).get("schema_version", "0.1.0"))
    return "0.1.0"


def main() -> None:
    if len(sys.argv) < 5:
        print("Usage: python orchestrate_docs.py <json_path> <docs_dir> <sql_dir> <assets_dir> [platform]")
        sys.exit(1)

    json_path = Path(sys.argv[1])
    docs_dir = Path(sys.argv[2])
    sql_dir = Path(sys.argv[3])
    assets_dir = Path(sys.argv[4])
    platform = sys.argv[5] if len(sys.argv) > 5 else "mssql"

    docs_dir.mkdir(parents=True, exist_ok=True)
    sql_dir.mkdir(parents=True, exist_ok=True)
    assets_dir.mkdir(parents=True, exist_ok=True)

    yaml_tables_dir = project_root / "schema_dictionary" / "tables"
    yaml_views_dir = project_root / "schema_dictionary" / "views"
    schema_version = _read_schema_version(project_root / "schema_dictionary")

    print(f"Schema version: {schema_version}")
    print(f"Platform: {platform}")

    # Generate tables, views, ERD, and SQL from YAML schema
    print("\n=== Generating from YAML Schema ===")
    generate_all_from_yaml(
        tables_dir=yaml_tables_dir,
        views_dir=yaml_views_dir,
        docs_dir=docs_dir,
        assets_dir=assets_dir,
        sql_dir=sql_dir,
        platform=platform,
        version=schema_version,
    )

    # Generate value sets from dictionary.json (not yet in YAML)
    print("\n=== Generating Value Sets (from dictionary.json) ===")
    parts_data = parse_parts_json(json_path)
    value_sets_md = generate_value_sets_markdown(parts_data)
    (docs_dir / "valuesets.md").write_text(value_sets_md, encoding="utf-8")
    print(f"Generated value sets: {docs_dir / 'valuesets.md'}")

    # Copy assets for MkDocs
    print("\n=== Copying Assets ===")
    copy_generated_assets(assets_dir)

    print("\n=== Documentation Generation Complete ===")


if __name__ == "__main__":
    main()
