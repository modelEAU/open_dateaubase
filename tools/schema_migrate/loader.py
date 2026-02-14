"""Loader for schema dictionary YAML table and view files."""

from pathlib import Path

import yaml


class SchemaLoadError(Exception):
    """Raised when a YAML table file fails validation during load."""


def load_views(views_dir: Path) -> dict[str, dict]:
    """Load all *.yaml files from views_dir; return {view_name: view_dict}.

    Args:
        views_dir: Path to the directory containing view YAML files.

    Returns:
        A dict mapping view name (str) to the parsed view dict.
        Returns an empty dict if the directory does not exist.

    Raises:
        SchemaLoadError: If any file is missing ``_format_version`` or the
            ``view.name`` value does not match the filename stem.
    """
    views_dir = Path(views_dir)
    if not views_dir.exists():
        return {}

    views: dict[str, dict] = {}

    for yaml_path in sorted(views_dir.glob("*.yaml")):
        try:
            with yaml_path.open(encoding="utf-8") as fh:
                data: dict = yaml.safe_load(fh)
        except yaml.YAMLError as exc:
            raise SchemaLoadError(
                f"{yaml_path.name}: YAML parse error — {exc}"
            ) from exc

        if not isinstance(data, dict):
            raise SchemaLoadError(
                f"{yaml_path.name}: file did not parse to a YAML mapping."
            )

        if "_format_version" not in data:
            raise SchemaLoadError(
                f"{yaml_path.name}: missing required key '_format_version'."
            )

        view_dict = data.get("view")
        if not isinstance(view_dict, dict):
            raise SchemaLoadError(
                f"{yaml_path.name}: missing or invalid 'view' key."
            )

        view_name: str | None = view_dict.get("name")
        stem = yaml_path.stem

        if view_name != stem:
            raise SchemaLoadError(
                f"{yaml_path.name}: view.name '{view_name}' does not match "
                f"filename stem '{stem}' (case-sensitive)."
            )

        views[view_name] = data

    return views


def load_schema(tables_dir: Path) -> dict[str, dict]:
    """Load all *.yaml files from tables_dir; return {table_name: table_dict}.

    Args:
        tables_dir: Path to the directory containing table YAML files.

    Returns:
        A dict mapping table name (str) to the parsed table dict.

    Raises:
        SchemaLoadError: If any file is missing ``_format_version`` or the
            ``table.name`` value does not match the filename stem.
    """
    tables_dir = Path(tables_dir)
    schema: dict[str, dict] = {}

    for yaml_path in sorted(tables_dir.glob("*.yaml")):
        try:
            with yaml_path.open(encoding="utf-8") as fh:
                data: dict = yaml.safe_load(fh)
        except yaml.YAMLError as exc:
            raise SchemaLoadError(
                f"{yaml_path.name}: YAML parse error — {exc}"
            ) from exc

        if not isinstance(data, dict):
            raise SchemaLoadError(
                f"{yaml_path.name}: file did not parse to a YAML mapping."
            )

        if "_format_version" not in data:
            raise SchemaLoadError(
                f"{yaml_path.name}: missing required key '_format_version'."
            )

        table_dict = data.get("table")
        if not isinstance(table_dict, dict):
            raise SchemaLoadError(
                f"{yaml_path.name}: missing or invalid 'table' key."
            )

        table_name: str | None = table_dict.get("name")
        stem = yaml_path.stem  # filename without extension

        if table_name != stem:
            raise SchemaLoadError(
                f"{yaml_path.name}: table.name '{table_name}' does not match "
                f"filename stem '{stem}' (case-sensitive)."
            )

        schema[table_name] = data

    return schema
