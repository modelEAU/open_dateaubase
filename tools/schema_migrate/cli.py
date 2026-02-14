"""CLI entry point for the schema migration script generator.

Usage examples::

    # Generate a migration between two schema versions
    python -m tools.schema_migrate \\
        --from-dir schema_dictionary/tables \\
        --from-version 1.0.0 \\
        --to-version 1.0.1 \\
        --to-dir schema_dictionary/tables \\
        --platform mssql \\
        --output-dir migrations/

    # Validate a tables directory
    python -m tools.schema_migrate --validate schema_dictionary/tables/

    # Generate the baseline CREATE script (as if diffing from empty)
    python -m tools.schema_migrate --create schema_dictionary/tables/ \\
        --platform mssql --output-dir migrations/
"""

import argparse
import sys
from pathlib import Path

import yaml

from .diff import diff_schemas
from .loader import load_schema, SchemaLoadError
from .render import render_create_script, render_migration
from .validate import validate_schema


def _load_version(version_yaml: Path) -> str:
    """Read schema_version from a version.yaml file."""
    with version_yaml.open(encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    return str(data.get("schema_version", "unknown"))


def cmd_validate(tables_dir: Path) -> int:
    """Run schema validation and print results.

    Args:
        tables_dir: Path to the directory containing table YAML files.

    Returns:
        Exit code (0 = success, 1 = errors found, 2 = load failure).
    """
    print(f"Loading schema from: {tables_dir}")
    try:
        schema = load_schema(tables_dir)
    except SchemaLoadError as exc:
        print(f"ERROR loading schema: {exc}", file=sys.stderr)
        return 2

    print(f"Loaded {len(schema)} table(s): {', '.join(sorted(schema))}")
    errors = validate_schema(schema)

    if errors:
        print(f"\nFound {len(errors)} validation error(s):")
        for err in errors:
            print(f"  - {err}")
        return 1

    print("Schema is valid.")
    return 0


def cmd_create(tables_dir: Path, platform: str, output_dir: Path) -> int:
    """Generate a baseline CREATE script for the full schema.

    Args:
        tables_dir: Path to the directory containing table YAML files.
        platform: Target SQL platform (``'mssql'`` or ``'postgres'``).
        output_dir: Directory where the output SQL file will be written.

    Returns:
        Exit code.
    """
    print(f"Loading schema from: {tables_dir}")
    try:
        schema = load_schema(tables_dir)
    except SchemaLoadError as exc:
        print(f"ERROR loading schema: {exc}", file=sys.stderr)
        return 2

    # Attempt to read version from the sibling version.yaml
    version_yaml = tables_dir.parent / "version.yaml"
    version = _load_version(version_yaml) if version_yaml.exists() else "0.0.0"

    sql = render_create_script(schema, version, platform)

    output_dir.mkdir(parents=True, exist_ok=True)
    out_file = output_dir / f"v{version}_create_{platform}.sql"
    out_file.write_text(sql, encoding="utf-8")
    print(f"Written: {out_file}")
    return 0


def cmd_migrate(
    from_dir: Path,
    from_version: str,
    to_dir: Path,
    to_version: str,
    platform: str,
    output_dir: Path,
) -> int:
    """Generate forward migration and rollback scripts.

    Args:
        from_dir: Tables directory for the old (source) schema version.
        from_version: Version string for the old schema.
        to_dir: Tables directory for the new (target) schema version.
        to_version: Version string for the new schema.
        platform: Target SQL platform (``'mssql'`` or ``'postgres'``).
        output_dir: Directory where output SQL files will be written.

    Returns:
        Exit code.
    """
    print(f"Loading old schema from: {from_dir}")
    try:
        old_schema = load_schema(from_dir)
    except SchemaLoadError as exc:
        print(f"ERROR loading old schema: {exc}", file=sys.stderr)
        return 2

    print(f"Loading new schema from: {to_dir}")
    try:
        new_schema = load_schema(to_dir)
    except SchemaLoadError as exc:
        print(f"ERROR loading new schema: {exc}", file=sys.stderr)
        return 2

    diff = diff_schemas(old_schema, new_schema)

    if diff.is_empty():
        print("No schema changes detected; no migration scripts generated.")
        return 0

    migration_sql, rollback_sql = render_migration(
        diff, new_schema, from_version, to_version, platform
    )

    output_dir.mkdir(parents=True, exist_ok=True)

    fwd_name = f"v{from_version}_to_v{to_version}_{platform}.sql"
    rbk_name = f"v{from_version}_to_v{to_version}_{platform}_rollback.sql"

    fwd_file = output_dir / fwd_name
    rbk_file = output_dir / rbk_name

    fwd_file.write_text(migration_sql, encoding="utf-8")
    rbk_file.write_text(rollback_sql, encoding="utf-8")

    print(f"Written: {fwd_file}")
    print(f"Written: {rbk_file}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    """Build and return the argument parser."""
    parser = argparse.ArgumentParser(
        prog="python -m tools.schema_migrate",
        description="Schema migration script generator for open_dateaubase.",
    )

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--validate",
        metavar="TABLES_DIR",
        help="Validate a tables directory and exit.",
    )
    group.add_argument(
        "--create",
        metavar="TABLES_DIR",
        help="Generate a full CREATE script (baseline, diff against empty schema).",
    )
    group.add_argument(
        "--from-dir",
        metavar="OLD_TABLES_DIR",
        help="Tables directory for the old (source) schema version.",
    )

    # Migration-specific arguments
    parser.add_argument("--from-version", metavar="VER", help="Old schema version string.")
    parser.add_argument("--to-version", metavar="VER", help="New schema version string.")
    parser.add_argument(
        "--to-dir",
        metavar="NEW_TABLES_DIR",
        help="Tables directory for the new (target) schema version.",
    )
    parser.add_argument(
        "--platform",
        choices=["mssql", "postgres"],
        default="mssql",
        help="Target SQL platform (default: mssql).",
    )
    parser.add_argument(
        "--output-dir",
        metavar="DIR",
        default="migrations",
        help="Directory to write generated SQL files (default: migrations/).",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI main entry point.

    Args:
        argv: Argument list (defaults to ``sys.argv[1:]``).

    Returns:
        Exit code.
    """
    parser = build_parser()
    args = parser.parse_args(argv)

    output_dir = Path(args.output_dir)
    platform = args.platform

    if args.validate:
        return cmd_validate(Path(args.validate))

    if args.create:
        return cmd_create(Path(args.create), platform, output_dir)

    # Migration mode
    if not args.from_version:
        parser.error("--from-version is required when using --from-dir.")
    if not args.to_version:
        parser.error("--to-version is required when using --from-dir.")
    if not args.to_dir:
        parser.error("--to-dir is required when using --from-dir.")

    return cmd_migrate(
        from_dir=Path(args.from_dir),
        from_version=args.from_version,
        to_dir=Path(args.to_dir),
        to_version=args.to_version,
        platform=platform,
        output_dir=output_dir,
    )


if __name__ == "__main__":
    sys.exit(main())
