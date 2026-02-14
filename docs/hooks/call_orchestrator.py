import sys
from pathlib import Path

from importlib.metadata import version

package_version = version("open-dateaubase")

# Make scripts and project root importable
_project_root = Path(__file__).parent.parent.parent
_scripts_dir = _project_root / "scripts"
for _p in [str(_project_root), str(_scripts_dir)]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

import yaml as _yaml
from generate_from_yaml import generate_all_from_yaml
from legacy.generate_dictionary_reference import (
    parse_parts_json,
    generate_value_sets_markdown,
)


def _read_schema_version(schema_dir: Path) -> str:
    version_yaml = schema_dir / "version.yaml"
    if version_yaml.exists():
        with version_yaml.open(encoding="utf-8") as fh:
            return str(_yaml.safe_load(fh).get("schema_version", "0.1.0"))
    return "0.1.0"


def _copy_assets(assets_dir: Path) -> None:
    erd_path = assets_dir / "erd_interactive.html"
    if not erd_path.exists():
        print(f"Warning: {erd_path} not found, skipping asset copy.")
        return
    try:
        import mkdocs_gen_files

        content = erd_path.read_text(encoding="utf-8")
        with mkdocs_gen_files.open("assets/erd_interactive.html", "w") as fh:
            fh.write(content)
        print("Copied erd_interactive.html -> assets/erd_interactive.html")
    except ImportError:
        print("Warning: mkdocs_gen_files not available, skipping asset copy.")


def on_pre_build(config):
    """MkDocs hook: generate all docs from YAML schema before the build."""
    project_root = Path(config["config_file_path"]).parent
    docs_dir = Path(config["docs_dir"])
    output_path = docs_dir / "reference"
    assets_path = docs_dir / "assets"
    sql_path = project_root / "sql_generation_scripts"
    json_path = project_root / "src" / "open_dateaubase" / "dictionary.json"

    yaml_tables_dir = project_root / "schema_dictionary" / "tables"
    yaml_views_dir = project_root / "schema_dictionary" / "views"
    schema_version = _read_schema_version(project_root / "schema_dictionary")

    print(f"Generating docs from YAML schema v{schema_version}...")

    # Tables, views, ERD, SQL — all from YAML
    generate_all_from_yaml(
        tables_dir=yaml_tables_dir,
        views_dir=yaml_views_dir,
        docs_dir=output_path,
        assets_dir=assets_path,
        sql_dir=sql_path,
        platform="mssql",
        version=schema_version,
    )

    # Value sets — still from dictionary.json
    parts_data = parse_parts_json(json_path)
    value_sets_md = generate_value_sets_markdown(parts_data)
    (output_path / "valuesets.md").write_text(value_sets_md, encoding="utf-8")
    print(f"Generated value sets: {output_path / 'valuesets.md'}")

    # Copy ERD asset into MkDocs virtual filesystem
    _copy_assets(assets_path)

    print("Documentation generation complete.")
