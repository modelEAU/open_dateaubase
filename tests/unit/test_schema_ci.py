"""CI tests for schema dictionary integrity.

These tests run without a database and validate:
1. All YAML table definitions pass the schema validator (no broken FK references).
2. Every forward migration has a corresponding rollback script.
3. The schema_dictionary version.yaml version matches the latest migration target.
"""

from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).parent.parent.parent
TABLES_DIR = REPO_ROOT / "schema_dictionary" / "tables"
VERSION_YAML = REPO_ROOT / "schema_dictionary" / "version.yaml"
MIGRATIONS_DIR = REPO_ROOT / "migrations"


# ---------------------------------------------------------------------------
# Test 1: All YAML definitions are structurally valid
# ---------------------------------------------------------------------------


def test_yaml_schema_validates_cleanly() -> None:
    """Load every table YAML and run the schema validator — must return no errors."""
    from tools.schema_migrate.loader import load_schema
    from tools.schema_migrate.validate import validate_schema

    schema = load_schema(TABLES_DIR)
    errors = validate_schema(schema)
    assert errors == [], "\n".join(errors)


def test_all_yaml_files_have_format_version() -> None:
    """Every .yaml file in tables/ must declare _format_version."""
    for yaml_file in TABLES_DIR.glob("*.yaml"):
        with yaml_file.open(encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
        assert "_format_version" in data, f"{yaml_file.name} missing _format_version"


def test_yaml_table_name_matches_filename() -> None:
    """table.name in each YAML file must match the filename stem."""
    for yaml_file in TABLES_DIR.glob("*.yaml"):
        with yaml_file.open(encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
        table_name = data.get("table", {}).get("name")
        assert table_name == yaml_file.stem, (
            f"{yaml_file.name}: table.name '{table_name}' does not match filename stem '{yaml_file.stem}'"
        )


# ---------------------------------------------------------------------------
# Test 2: Every forward migration has a rollback
# ---------------------------------------------------------------------------


def _forward_migrations() -> list[Path]:
    """Return all forward migration SQL files (exclude rollbacks and create scripts)."""
    if not MIGRATIONS_DIR.exists():
        return []
    return [
        f
        for f in MIGRATIONS_DIR.glob("v*_to_v*.sql")
        if "_rollback" not in f.name
    ]


def test_every_migration_has_a_rollback() -> None:
    """For each v{from}_to_v{to}_{platform}.sql, a rollback counterpart must exist."""
    forward = _forward_migrations()
    if not forward:
        pytest.skip("No migration scripts found — skipping rollback check.")

    missing = []
    for fwd in forward:
        # e.g. v1.0.0_to_v1.0.1_mssql.sql  → v1.0.0_to_v1.0.1_mssql_rollback.sql
        rollback_name = fwd.stem + "_rollback" + fwd.suffix
        rollback_path = fwd.parent / rollback_name
        if not rollback_path.exists():
            missing.append(fwd.name)

    assert missing == [], "Migrations missing a rollback script:\n" + "\n".join(missing)


def test_migration_files_have_header_comment() -> None:
    """Every migration SQL file must start with a -- Migration: header comment."""
    all_sql = list(MIGRATIONS_DIR.glob("*.sql")) if MIGRATIONS_DIR.exists() else []
    if not all_sql:
        pytest.skip("No migration SQL files found.")

    for sql_file in all_sql:
        content = sql_file.read_text(encoding="utf-8")
        assert content.startswith("--"), (
            f"{sql_file.name} does not start with a comment header"
        )


# ---------------------------------------------------------------------------
# Test 3: version.yaml version matches the latest migration target
# ---------------------------------------------------------------------------


def _latest_migration_target_version() -> str | None:
    """Return the highest 'to' version found in migration filenames, or None."""
    forward = _forward_migrations()
    if not forward:
        return None

    versions: list[tuple[int, ...]] = []
    for f in forward:
        # filename pattern: v{from}_to_v{to}_{platform}.sql
        parts = f.stem.split("_to_v")
        if len(parts) == 2:
            to_part = parts[1].split("_")[0]  # strip platform suffix
            try:
                versions.append(tuple(int(x) for x in to_part.split(".")))
            except ValueError:
                pass

    if not versions:
        return None
    return ".".join(str(x) for x in max(versions))


def test_version_yaml_matches_latest_migration_target() -> None:
    """schema_dictionary/version.yaml schema_version should equal the highest migration target."""
    latest = _latest_migration_target_version()
    if latest is None:
        pytest.skip("No migration scripts found — skipping version check.")

    with VERSION_YAML.open(encoding="utf-8") as fh:
        version_data = yaml.safe_load(fh)

    current = str(version_data.get("schema_version", ""))
    assert current == latest, (
        f"version.yaml declares schema_version '{current}' but latest migration target is '{latest}'. "
        "Update schema_dictionary/version.yaml to match."
    )
