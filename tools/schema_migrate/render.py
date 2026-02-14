"""SQL migration script renderer for MSSQL and PostgreSQL."""

from datetime import datetime, timezone

from .diff import SchemaDiff

LOGICAL_TYPE_MAP: dict[str, dict[str, str]] = {
    "mssql": {
        "integer": "INT",
        "biginteger": "BIGINT",
        "smallinteger": "SMALLINT",
        "float64": "FLOAT",
        "float32": "REAL",
        "boolean": "BIT",
        "timestamp": "DATETIME2",
        "date": "DATE",
        "text": "NVARCHAR(MAX)",
        "binary": "VARBINARY",
        "binary_large": "VARBINARY(MAX)",
        "decimal": "NUMERIC",
        "string": "NVARCHAR",
    },
    "postgres": {
        "integer": "INTEGER",
        "biginteger": "BIGINT",
        "smallinteger": "SMALLINT",
        "float64": "DOUBLE PRECISION",
        "float32": "REAL",
        "boolean": "BOOLEAN",
        "timestamp": "TIMESTAMP",
        "date": "DATE",
        "text": "TEXT",
        "binary": "BYTEA",
        "binary_large": "BYTEA",
        "decimal": "NUMERIC",
        "string": "VARCHAR",
    },
}


def _q(identifier: str, platform: str) -> str:
    """Quote an SQL identifier for the target platform.

    Args:
        identifier: The raw identifier (table or column name).
        platform: ``'mssql'`` or ``'postgres'``.

    Returns:
        Quoted identifier string.
    """
    if platform == "mssql":
        return f"[{identifier}]"
    return f'"{identifier}"'


def render_column_type(col: dict, platform: str) -> str:
    """Convert logical type + modifiers to platform SQL type string.

    Args:
        col: Column definition dict from the schema YAML.
        platform: ``'mssql'`` or ``'postgres'``.

    Returns:
        SQL type string (e.g. ``NVARCHAR(255)``, ``NUMERIC(10,2)``).
    """
    logical = col.get("logical_type") or ""
    type_map = LOGICAL_TYPE_MAP[platform]
    base = type_map.get(logical, logical.upper() if logical else "/* UNMAPPED TYPE */")

    if logical == "string":
        max_length = col.get("max_length", "MAX")
        if str(max_length).lower() == "max":
            if platform == "mssql":
                return "NVARCHAR(MAX)"
            return "VARCHAR(MAX)"
        return f"{base}({max_length})"

    if logical == "decimal":
        precision = col.get("precision")
        scale = col.get("scale")
        if precision is not None and scale is not None:
            return f"NUMERIC({precision},{scale})"
        return "NUMERIC"

    if logical == "timestamp":
        precision = col.get("precision")
        if precision is not None:
            return f"{base}({precision})"
        return base

    if logical == "binary":
        max_length = col.get("max_length")
        if max_length is not None:
            if platform == "mssql":
                return f"VARBINARY({max_length})"
            return "BYTEA"
        return base

    return base


def render_column_def(col: dict, platform: str) -> str:
    """Render a full column definition for CREATE TABLE or ADD COLUMN.

    Args:
        col: Column definition dict from the schema YAML.
        platform: ``'mssql'`` or ``'postgres'``.

    Returns:
        SQL fragment suitable for use inside CREATE TABLE or ALTER TABLE ADD.
    """
    parts: list[str] = [_q(col["name"], platform), render_column_type(col, platform)]

    nullable = col.get("nullable", True)
    identity = col.get("identity", False)

    if identity:
        if platform == "mssql":
            parts.append("IDENTITY(1,1)")
        else:
            # For PostgreSQL replace type with SERIAL/BIGSERIAL when identity
            logical = col.get("logical_type", "")
            if logical == "biginteger":
                parts[1] = "BIGSERIAL"
            else:
                parts[1] = "SERIAL"
            # Remove the IDENTITY marker — handled by type replacement
            identity = False  # no extra keyword needed

    if not nullable:
        parts.append("NOT NULL")

    default = col.get("default")
    if default is not None:
        if str(default).upper() == "CURRENT_TIMESTAMP":
            parts.append("DEFAULT CURRENT_TIMESTAMP")
        else:
            parts.append(f"DEFAULT {default}")

    return " ".join(parts)


def _render_create_table(table_name: str, table_dict: dict, platform: str) -> str:
    """Render a CREATE TABLE statement for a table definition.

    Args:
        table_name: Name of the table.
        table_dict: Full file-level dict (including ``_format_version`` key).
        platform: ``'mssql'`` or ``'postgres'``.

    Returns:
        Complete CREATE TABLE SQL statement string (no trailing newline).
    """
    tbl = table_dict["table"]
    schema = tbl.get("schema", "dbo")
    columns: list[dict] = tbl.get("columns", [])
    primary_key: list[str] = tbl.get("primary_key", [])
    check_constraints: list[dict] = tbl.get("check_constraints", []) or []

    col_defs: list[str] = [f"    {render_column_def(col, platform)}" for col in columns]

    if primary_key:
        pk_cols = ", ".join(_q(c, platform) for c in primary_key)
        pk_name = f"PK_{table_name}"
        col_defs.append(f"    CONSTRAINT {_q(pk_name, platform)} PRIMARY KEY ({pk_cols})")

    for ck in check_constraints:
        ck_name = ck.get("name", "")
        expr = ck.get("expression", "")
        col_defs.append(f"    CONSTRAINT {_q(ck_name, platform)} CHECK ({expr})")

    body = ",\n".join(col_defs)
    full_table = _q(f"{schema}.{table_name}", platform) if platform == "postgres" else f"{_q(schema, platform)}.{_q(table_name, platform)}"
    return f"CREATE TABLE {full_table} (\n{body}\n);"


def _render_drop_table(table_name: str, table_dict: dict, platform: str) -> str:
    tbl = table_dict["table"]
    schema = tbl.get("schema", "dbo")
    if platform == "postgres":
        full_table = f'"{schema}"."{table_name}"'
    else:
        full_table = f"[{schema}].[{table_name}]"
    return f"DROP TABLE {full_table};"


def _render_add_fk(table_name: str, fk: dict, table_dict: dict, platform: str) -> str:
    tbl = table_dict["table"]
    schema = tbl.get("schema", "dbo")
    child_col = fk["column"]
    ref_table = fk["ref_table"]
    ref_col = fk["ref_column"]
    fk_name = f"FK_{table_name}_{ref_table}"

    if platform == "mssql":
        return (
            f"ALTER TABLE [{schema}].[{table_name}] "
            f"ADD CONSTRAINT [{fk_name}] "
            f"FOREIGN KEY ([{child_col}]) "
            f"REFERENCES [{schema}].[{ref_table}] ([{ref_col}]);"
        )
    return (
        f'ALTER TABLE "{schema}"."{table_name}" '
        f'ADD CONSTRAINT "{fk_name}" '
        f'FOREIGN KEY ("{child_col}") '
        f'REFERENCES "{schema}"."{ref_table}" ("{ref_col}");'
    )


def _render_drop_fk(table_name: str, fk: dict, table_dict: dict, platform: str) -> str:
    tbl = table_dict["table"]
    schema = tbl.get("schema", "dbo")
    ref_table = fk["ref_table"]
    fk_name = f"FK_{table_name}_{ref_table}"

    if platform == "mssql":
        return (
            f"ALTER TABLE [{schema}].[{table_name}] "
            f"DROP CONSTRAINT [{fk_name}];"
        )
    return (
        f'ALTER TABLE "{schema}"."{table_name}" '
        f'DROP CONSTRAINT "{fk_name}";'
    )


def _render_create_index(table_name: str, idx: dict, table_dict: dict, platform: str) -> str:
    tbl = table_dict["table"]
    schema = tbl.get("schema", "dbo")
    idx_name = idx["name"]
    cols = ", ".join(_q(c, platform) for c in idx["columns"])
    unique = "UNIQUE " if idx.get("unique") else ""

    if platform == "mssql":
        return (
            f"CREATE {unique}INDEX [{idx_name}] "
            f"ON [{schema}].[{table_name}] ({cols});"
        )
    return (
        f'CREATE {unique}INDEX "{idx_name}" '
        f'ON "{schema}"."{table_name}" ({cols});'
    )


def _render_drop_index(table_name: str, idx: dict, table_dict: dict, platform: str) -> str:
    tbl = table_dict["table"]
    schema = tbl.get("schema", "dbo")
    idx_name = idx["name"]
    if platform == "mssql":
        return f"DROP INDEX [{idx_name}] ON [{schema}].[{table_name}];"
    return f'DROP INDEX "{schema}"."{idx_name}";'


def _table_fks(table_dict: dict) -> list[dict]:
    """Collect all FK dicts from a table definition."""
    fks: list[dict] = []
    for col in table_dict.get("table", {}).get("columns", []) or []:
        fk = col.get("foreign_key")
        if fk:
            fks.append({"column": col["name"], "ref_table": fk["table"], "ref_column": fk["column"]})
    return fks


def _sort_tables_fk_safe(table_names: list[str], schema: dict[str, dict]) -> list[str]:
    """Return table_names sorted so tables with no FKs come first."""
    no_fk = [t for t in table_names if not _table_fks(schema.get(t, {}))]
    has_fk = [t for t in table_names if _table_fks(schema.get(t, {}))]
    return no_fk + has_fk


def _header(from_version: str, to_version: str, platform: str, is_rollback: bool = False) -> str:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    if is_rollback:
        rollback_ref = f"v{to_version}_to_v{from_version}_{platform}_rollback.sql"
        direction = f"v{to_version} -> v{from_version} (ROLLBACK)"
    else:
        rollback_ref = f"v{from_version}_to_v{to_version}_{platform}_rollback.sql"
        direction = f"v{from_version} -> v{to_version}"

    return (
        f"-- Migration: {direction}\n"
        f"-- Platform: {platform}\n"
        f"-- Generated: {now}\n"
        f"-- Rollback: {rollback_ref}\n"
    )


def render_migration(
    diff: SchemaDiff,
    new_schema: dict[str, dict],
    from_version: str,
    to_version: str,
    platform: str,
) -> tuple[str, str]:
    """Render forward migration and rollback SQL scripts.

    Args:
        diff: The :class:`~tools.schema_migrate.diff.SchemaDiff` describing changes.
        new_schema: The new (target) schema dict, needed for CREATE TABLE bodies.
        from_version: Source schema version string (e.g. ``'1.0.0'``).
        to_version: Target schema version string (e.g. ``'1.0.1'``).
        platform: ``'mssql'`` or ``'postgres'``.

    Returns:
        A tuple ``(migration_sql, rollback_sql)`` — both as plain strings.
    """
    fwd: list[str] = [_header(from_version, to_version, platform, is_rollback=False)]
    rbk: list[str] = [_header(from_version, to_version, platform, is_rollback=True)]

    # ── CREATE new tables (no-FK tables first) ──────────────────────────────
    sorted_new = _sort_tables_fk_safe(diff.new_tables, new_schema)
    for table_name in sorted_new:
        fwd.append(_render_create_table(table_name, new_schema[table_name], platform))
        rbk.append(_render_drop_table(table_name, new_schema[table_name], platform))

    # ── ADD COLUMN ───────────────────────────────────────────────────────────
    for table_name, cols in diff.new_columns.items():
        tbl = new_schema[table_name]["table"]
        schema = tbl.get("schema", "dbo")
        for col in cols:
            col_def = render_column_def(col, platform)
            if platform == "mssql":
                fwd.append(f"ALTER TABLE [{schema}].[{table_name}] ADD {col_def};")
                rbk.append(f"ALTER TABLE [{schema}].[{table_name}] DROP COLUMN [{col['name']}];")
            else:
                fwd.append(f'ALTER TABLE "{schema}"."{table_name}" ADD COLUMN {col_def};')
                rbk.append(f'ALTER TABLE "{schema}"."{table_name}" DROP COLUMN "{col["name"]}";')

    # ── ALTER COLUMN ─────────────────────────────────────────────────────────
    for table_name, alterations in diff.altered_columns.items():
        tbl = new_schema[table_name]["table"]
        schema = tbl.get("schema", "dbo")
        for alt in alterations:
            col_name = alt["column"]
            new_type = render_column_type(alt["new"], platform)
            old_type = render_column_type(alt["old"], platform)
            if platform == "mssql":
                fwd.append(
                    f"ALTER TABLE [{schema}].[{table_name}] "
                    f"ALTER COLUMN [{col_name}] {new_type};"
                )
                rbk.append(
                    f"ALTER TABLE [{schema}].[{table_name}] "
                    f"ALTER COLUMN [{col_name}] {old_type};"
                )
            else:
                fwd.append(
                    f'ALTER TABLE "{schema}"."{table_name}" '
                    f'ALTER COLUMN "{col_name}" TYPE {new_type};'
                )
                rbk.append(
                    f'ALTER TABLE "{schema}"."{table_name}" '
                    f'ALTER COLUMN "{col_name}" TYPE {old_type};'
                )

    # ── DROP COLUMN ──────────────────────────────────────────────────────────
    for table_name, col_names in diff.dropped_columns.items():
        tbl = new_schema.get(table_name, {}).get("table", {})
        schema = tbl.get("schema", "dbo")
        for col_name in col_names:
            if platform == "mssql":
                fwd.append(f"ALTER TABLE [{schema}].[{table_name}] DROP COLUMN [{col_name}];")
            else:
                fwd.append(f'ALTER TABLE "{schema}"."{table_name}" DROP COLUMN "{col_name}";')
            # rollback: re-add the column (we need the old definition — stored in diff)
            # find it in altered_columns' old dicts — but dropped_columns only has names.
            # We store rollback as a comment since we don't carry the old col dict here.
            rbk.append(f"-- TODO: restore dropped column {col_name} on {table_name} manually.")

    # ── DROP TABLE ───────────────────────────────────────────────────────────
    for table_name in diff.dropped_tables:
        # We don't have the old table body in new_schema; emit a comment.
        fwd.append(f"-- DROP TABLE {table_name} (was removed from schema)")
        rbk.append(f"-- TODO: restore dropped table {table_name} manually.")

    # ── CREATE INDEX ─────────────────────────────────────────────────────────
    for table_name, indexes in diff.new_indexes.items():
        for idx in indexes:
            fwd.append(_render_create_index(table_name, idx, new_schema[table_name], platform))
            rbk.append(_render_drop_index(table_name, idx, new_schema[table_name], platform))

    # ── DROP INDEX ───────────────────────────────────────────────────────────
    for table_name, indexes in diff.dropped_indexes.items():
        for idx in indexes:
            fwd.append(_render_drop_index(table_name, idx, new_schema[table_name], platform))
            rbk.append(_render_create_index(table_name, idx, new_schema[table_name], platform))

    # ── ADD FK ───────────────────────────────────────────────────────────────
    for table_name, fks in diff.new_fks.items():
        for fk in fks:
            fwd.append(_render_add_fk(table_name, fk, new_schema[table_name], platform))
            rbk.append(_render_drop_fk(table_name, fk, new_schema[table_name], platform))

    # ── DROP FK ──────────────────────────────────────────────────────────────
    for table_name, fks in diff.dropped_fks.items():
        for fk in fks:
            fwd.append(_render_drop_fk(table_name, fk, new_schema[table_name], platform))
            rbk.append(_render_add_fk(table_name, fk, new_schema[table_name], platform))

    return "\n\n".join(fwd) + "\n", "\n\n".join(rbk) + "\n"


def render_create_script(
    schema: dict[str, dict],
    version: str,
    platform: str,
) -> str:
    """Render a full CREATE script for all tables in schema (baseline).

    Args:
        schema: Full schema dict from ``load_schema``.
        version: Schema version string.
        platform: ``'mssql'`` or ``'postgres'``.

    Returns:
        SQL string containing all CREATE TABLE and CREATE INDEX statements,
        plus ALTER TABLE ADD CONSTRAINT for all foreign keys.
    """
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    lines: list[str] = [
        f"-- Baseline CREATE script for schema v{version}",
        f"-- Platform: {platform}",
        f"-- Generated: {now}",
        "",
    ]

    sorted_tables = _sort_tables_fk_safe(sorted(schema.keys()), schema)

    for table_name in sorted_tables:
        lines.append(_render_create_table(table_name, schema[table_name], platform))
        lines.append("")

    # Indexes
    for table_name in sorted_tables:
        tbl = schema[table_name]["table"]
        for idx in tbl.get("indexes", []) or []:
            lines.append(_render_create_index(table_name, idx, schema[table_name], platform))
        lines.append("")

    # Foreign keys (after all tables exist)
    for table_name in sorted_tables:
        for fk in _table_fks(schema[table_name]):
            lines.append(_render_add_fk(table_name, fk, schema[table_name], platform))

    return "\n".join(lines) + "\n"


def render_create_view(view_name: str, view_dict: dict, platform: str) -> str:
    """Render a CREATE OR ALTER VIEW (MSSQL) or CREATE OR REPLACE VIEW (PostgreSQL).

    Args:
        view_name: Name of the view.
        view_dict: Full file-level dict (including ``_format_version`` key).
        platform: ``'mssql'`` or ``'postgres'``.

    Returns:
        Complete CREATE VIEW SQL statement string.
    """
    v = view_dict["view"]
    schema = v.get("schema", "dbo")
    definition = (v.get("view_definition") or "").strip()

    full_view = (
        f"[{schema}].[{view_name}]" if platform == "mssql"
        else f'"{schema}"."{view_name}"'
    )

    if platform == "mssql":
        return f"CREATE OR ALTER VIEW {full_view} AS\n{definition};"
    return f"CREATE OR REPLACE VIEW {full_view} AS\n{definition};"


def render_drop_view(view_name: str, view_dict: dict, platform: str) -> str:
    """Render a DROP VIEW statement.

    Args:
        view_name: Name of the view.
        view_dict: Full file-level dict.
        platform: ``'mssql'`` or ``'postgres'``.

    Returns:
        DROP VIEW SQL statement string.
    """
    v = view_dict["view"]
    schema = v.get("schema", "dbo")

    full_view = (
        f"[{schema}].[{view_name}]" if platform == "mssql"
        else f'"{schema}"."{view_name}"'
    )
    return f"DROP VIEW {full_view};"


def render_create_script_with_views(
    schema: dict[str, dict],
    views: dict[str, dict],
    version: str,
    platform: str,
) -> str:
    """Render a full CREATE script for all tables and views (baseline).

    Args:
        schema: Full schema dict from ``load_schema``.
        views: Full views dict from ``load_views``.
        version: Schema version string.
        platform: ``'mssql'`` or ``'postgres'``.

    Returns:
        SQL string containing all CREATE TABLE, CREATE INDEX, ALTER TABLE FK,
        and CREATE VIEW statements.
    """
    # Reuse existing table CREATE script
    sql = render_create_script(schema, version, platform).rstrip("\n")

    if views:
        view_lines: list[str] = ["", "-- Views"]
        for view_name in sorted(views.keys()):
            view_lines.append(render_create_view(view_name, views[view_name], platform))
            view_lines.append("")
        sql += "\n" + "\n".join(view_lines)

    return sql + "\n"
