"""Schema differ: computes a structured diff between two schema versions."""

from dataclasses import dataclass, field


@dataclass
class SchemaDiff:
    """Structured description of changes between two schema versions."""

    new_tables: list[str] = field(default_factory=list)
    dropped_tables: list[str] = field(default_factory=list)
    new_columns: dict[str, list[dict]] = field(default_factory=dict)
    altered_columns: dict[str, list[dict]] = field(default_factory=dict)
    dropped_columns: dict[str, list[str]] = field(default_factory=dict)
    new_indexes: dict[str, list[dict]] = field(default_factory=dict)
    dropped_indexes: dict[str, list[dict]] = field(default_factory=dict)
    new_fks: dict[str, list[dict]] = field(default_factory=dict)
    dropped_fks: dict[str, list[dict]] = field(default_factory=dict)
    new_unique_constraints: dict[str, list[dict]] = field(default_factory=dict)
    dropped_unique_constraints: dict[str, list[dict]] = field(default_factory=dict)
    new_check_constraints: dict[str, list[dict]] = field(default_factory=dict)
    dropped_check_constraints: dict[str, list[dict]] = field(default_factory=dict)
    new_views: list[str] = field(default_factory=list)
    dropped_views: list[str] = field(default_factory=list)
    altered_views: list[str] = field(default_factory=list)
    new_seed_rows: dict[str, list[dict]] = field(default_factory=dict)
    dropped_seed_rows: dict[str, list[dict]] = field(default_factory=dict)

    def is_empty(self) -> bool:
        """Return True when there are no detected differences."""
        return not any([
            self.new_tables,
            self.dropped_tables,
            self.new_columns,
            self.altered_columns,
            self.dropped_columns,
            self.new_indexes,
            self.dropped_indexes,
            self.new_fks,
            self.dropped_fks,
            self.new_unique_constraints,
            self.dropped_unique_constraints,
            self.new_check_constraints,
            self.dropped_check_constraints,
            self.new_views,
            self.dropped_views,
            self.altered_views,
            self.new_seed_rows,
            self.dropped_seed_rows,
        ])


def _column_map(table_dict: dict) -> dict[str, dict]:
    """Return {column_name: column_dict} for all columns in a table."""
    return {
        col["name"]: col
        for col in table_dict.get("table", {}).get("columns", [])
    }


def _index_map(table_dict: dict) -> dict[str, dict]:
    """Return {index_name: index_dict} for all indexes in a table."""
    return {
        idx["name"]: idx
        for idx in table_dict.get("table", {}).get("indexes", []) or []
    }


def _fk_list(table_dict: dict) -> list[dict]:
    """Return a list of FK descriptor dicts for every FK column in a table."""
    fks: list[dict] = []
    for col in table_dict.get("table", {}).get("columns", []) or []:
        fk = col.get("foreign_key")
        if fk:
            fks.append(
                {
                    "column": col["name"],
                    "ref_table": fk["table"],
                    "ref_column": fk["column"],
                }
            )
    return fks


def _fk_map(table_dict: dict) -> dict[str, dict]:
    """Return {column_name: fk_dict} for all FK columns."""
    return {fk["column"]: fk for fk in _fk_list(table_dict)}


def _fk_target(fk: dict) -> tuple:
    """Return the (ref_table, ref_column) an FK points at."""
    return (fk["ref_table"], fk["ref_column"])


def _unique_constraint_map(table_dict: dict) -> dict[str, dict]:
    """Return {constraint_name: constraint_dict} for a table's unique constraints.

    Covers both the dedicated ``unique_constraints`` list and any entries in
    the generic ``constraints`` list with ``type: unique``.
    """
    tbl = table_dict.get("table", {})
    constraints = list(tbl.get("unique_constraints", []) or [])
    constraints += [c for c in (tbl.get("constraints", []) or []) if c.get("type") == "unique"]
    return {c["name"]: c for c in constraints}


def _check_constraint_map(table_dict: dict) -> dict[str, dict]:
    """Return {constraint_name: constraint_dict} for a table's check constraints."""
    return {
        c["name"]: c
        for c in table_dict.get("table", {}).get("check_constraints", []) or []
    }


def _seed_pk(table_dict: dict) -> str | None:
    """Return the primary-key column name used to key a table's seed_data rows."""
    pk = table_dict.get("table", {}).get("primary_key") or []
    return pk[0] if pk else None


def _seed_map(table_dict: dict) -> dict:
    """Return {pk_value: row} for a table's seed_data, keyed by its primary key."""
    pk = _seed_pk(table_dict)
    if not pk:
        return {}
    rows = table_dict.get("table", {}).get("seed_data") or []
    return {row[pk]: row for row in rows if pk in row}


def _column_type_sig(col: dict) -> tuple:
    """Return a hashable signature of type-relevant column attributes."""
    return (
        col.get("logical_type"),
        col.get("max_length"),
        col.get("precision"),
        col.get("scale"),
        col.get("nullable"),
        col.get("identity"),
        col.get("default"),
    )


def diff_schemas(old: dict[str, dict], new: dict[str, dict]) -> SchemaDiff:
    """Compare two schema dicts and return the diff.

    Args:
        old: Schema dict returned by ``load_schema`` for the previous version.
        new: Schema dict returned by ``load_schema`` for the new version.

    Returns:
        A :class:`SchemaDiff` describing every detected change.
    """
    diff = SchemaDiff()

    old_tables = set(old.keys())
    new_tables = set(new.keys())

    diff.new_tables = sorted(new_tables - old_tables)
    diff.dropped_tables = sorted(old_tables - new_tables)

    # Examine tables present in both versions.
    common_tables = old_tables & new_tables
    for table_name in sorted(common_tables):
        old_cols = _column_map(old[table_name])
        new_cols = _column_map(new[table_name])

        added_cols = [new_cols[c] for c in new_cols if c not in old_cols]
        if added_cols:
            diff.new_columns[table_name] = added_cols

        removed_cols = [c for c in old_cols if c not in new_cols]
        if removed_cols:
            diff.dropped_columns[table_name] = removed_cols

        altered: list[dict] = []
        for col_name in old_cols:
            if col_name not in new_cols:
                continue
            old_sig = _column_type_sig(old_cols[col_name])
            new_sig = _column_type_sig(new_cols[col_name])
            if old_sig != new_sig:
                altered.append(
                    {
                        "column": col_name,
                        "old": old_cols[col_name],
                        "new": new_cols[col_name],
                    }
                )
        if altered:
            diff.altered_columns[table_name] = altered

        # Indexes
        old_idx = _index_map(old[table_name])
        new_idx = _index_map(new[table_name])

        added_idx = [new_idx[i] for i in new_idx if i not in old_idx]
        if added_idx:
            diff.new_indexes[table_name] = added_idx

        dropped_idx = [old_idx[i] for i in old_idx if i not in new_idx]
        if dropped_idx:
            diff.dropped_indexes[table_name] = dropped_idx

        # Foreign keys (tracked per column; a re-pointed target on the same
        # column — e.g. Channel_ID moving from Channel.Channel_ID to
        # Channel.Stream_ID — is a drop-old + add-new, not a no-op)
        old_fk = _fk_map(old[table_name])
        new_fk = _fk_map(new[table_name])

        added_fks = [
            new_fk[c] for c in new_fk
            if c not in old_fk or _fk_target(old_fk[c]) != _fk_target(new_fk[c])
        ]
        if added_fks:
            diff.new_fks[table_name] = added_fks

        dropped_fks = [
            old_fk[c] for c in old_fk
            if c not in new_fk or _fk_target(old_fk[c]) != _fk_target(new_fk[c])
        ]
        if dropped_fks:
            diff.dropped_fks[table_name] = dropped_fks

        # Unique constraints (a changed column list is a drop-old + add-new)
        old_uq = _unique_constraint_map(old[table_name])
        new_uq = _unique_constraint_map(new[table_name])

        added_uq = [
            new_uq[name] for name in new_uq
            if name not in old_uq or old_uq[name].get("columns") != new_uq[name].get("columns")
        ]
        if added_uq:
            diff.new_unique_constraints[table_name] = added_uq

        dropped_uq = [
            old_uq[name] for name in old_uq
            if name not in new_uq or old_uq[name].get("columns") != new_uq[name].get("columns")
        ]
        if dropped_uq:
            diff.dropped_unique_constraints[table_name] = dropped_uq

        # Check constraints (a changed expression is a drop-old + add-new)
        old_ck = _check_constraint_map(old[table_name])
        new_ck = _check_constraint_map(new[table_name])

        added_ck = [
            new_ck[name] for name in new_ck
            if name not in old_ck or old_ck[name].get("expression") != new_ck[name].get("expression")
        ]
        if added_ck:
            diff.new_check_constraints[table_name] = added_ck

        dropped_ck = [
            old_ck[name] for name in old_ck
            if name not in new_ck or old_ck[name].get("expression") != new_ck[name].get("expression")
        ]
        if dropped_ck:
            diff.dropped_check_constraints[table_name] = dropped_ck

    return diff


def diff_seed_data(
    old: dict[str, dict], new: dict[str, dict]
) -> tuple[dict[str, list[dict]], dict[str, list[dict]]]:
    """Compare ``seed_data`` rows (keyed by each table's primary key) between two schemas.

    Args:
        old: Schema dict returned by ``load_schema`` for the previous version.
        new: Schema dict returned by ``load_schema`` for the new version.

    Returns:
        ``(new_seed_rows, dropped_seed_rows)``. ``new_seed_rows`` covers rows
        added to tables present in both versions plus the full seed_data of
        brand-new tables. ``dropped_seed_rows`` covers rows removed from
        tables present in both versions plus the full seed_data of dropped
        tables (so a rollback can restore them after recreating the table).
    """
    new_rows: dict[str, list[dict]] = {}
    dropped_rows: dict[str, list[dict]] = {}

    for table_name, table_dict in new.items():
        if table_name not in old:
            seed = table_dict.get("table", {}).get("seed_data") or []
            if seed:
                new_rows[table_name] = list(seed)
            continue

        if not _seed_pk(table_dict):
            continue

        old_seed = _seed_map(old[table_name])
        new_seed = _seed_map(table_dict)

        added = [new_seed[k] for k in new_seed if k not in old_seed]
        if added:
            new_rows[table_name] = added

        removed = [old_seed[k] for k in old_seed if k not in new_seed]
        if removed:
            dropped_rows[table_name] = removed

    for table_name in set(old) - set(new):
        seed = old[table_name].get("table", {}).get("seed_data") or []
        if seed:
            dropped_rows[table_name] = list(seed)

    return new_rows, dropped_rows


def diff_views(old: dict[str, dict], new: dict[str, dict]) -> tuple[list[str], list[str], list[str]]:
    """Compare two view dicts and return (new_views, dropped_views, altered_views).

    A view is considered altered if its ``view_definition`` or column list changes.

    Args:
        old: Views dict returned by ``load_views`` for the previous version.
        new: Views dict returned by ``load_views`` for the new version.

    Returns:
        Tuple of (new_view_names, dropped_view_names, altered_view_names).
    """
    old_names = set(old.keys())
    new_names = set(new.keys())

    new_views = sorted(new_names - old_names)
    dropped_views = sorted(old_names - new_names)

    altered: list[str] = []
    for name in sorted(old_names & new_names):
        old_v = old[name].get("view", {})
        new_v = new[name].get("view", {})
        if old_v.get("view_definition") != new_v.get("view_definition"):
            altered.append(name)
        elif old_v.get("columns") != new_v.get("columns"):
            altered.append(name)

    return new_views, dropped_views, altered
