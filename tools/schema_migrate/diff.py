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
    new_views: list[str] = field(default_factory=list)
    dropped_views: list[str] = field(default_factory=list)
    altered_views: list[str] = field(default_factory=list)

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
            self.new_views,
            self.dropped_views,
            self.altered_views,
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

        # Foreign keys (tracked per column)
        old_fk = _fk_map(old[table_name])
        new_fk = _fk_map(new[table_name])

        added_fks = [new_fk[c] for c in new_fk if c not in old_fk]
        if added_fks:
            diff.new_fks[table_name] = added_fks

        dropped_fks = [old_fk[c] for c in old_fk if c not in new_fk]
        if dropped_fks:
            diff.dropped_fks[table_name] = dropped_fks

    return diff


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
