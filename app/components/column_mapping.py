"""Column mapping: where every field of the import gets its value.

A mapping specification says, per **source column index** — never per header
text, which a sheet may repeat — what that column holds. Two independent
properties describe every assignment, per the field catalogue:

- **scope** — what the value attaches to (file / row / measurement) — comes
  from the field and is never chosen;
- **source** — where the value comes from: a **column**, a **constant**
  applied across the field's whole scope, or nothing. Measurement-scoped
  fields may also take a **group constant** — a constant for one group only,
  which is how each measurement group carries its own identity.

Measurement-scoped assignments carry a **group** tag: columns sharing a group
compose one measurement. Without an explicit group an assignment normalizes to
a singleton group — one measurement per value column by default.

Resolution precedence for a measurement field in group g: the group constant,
then a column mapped to the field in g, then the global constant. For a
file/row field the source is a column XOR a constant — having both is an
incoherence the validation names.

Constants on foreign-key fields hold the **name the user typed** (``"Field"``,
``"VdQ"``): names are resolved to ids at submit time, loudly, exactly like the
values in a mapped column. Non-FK constants hold the typed value. A name the
database does not hold takes a **value binding** — the user saying which entity
one source text means — since only they can settle that.

Pure: no Streamlit, no database.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

import pandas as pd

from app.components.field_catalogue import Catalogue, FieldMeta
from app.components.sheet_block import SheetBlock

#: The display string for an unmapped column.
IGNORE = "— ignore —"

#: The bulk actions a multi-column selection drives.
BULK_IGNORE = "ignore"
BULK_VALUE_EACH = "value_each"
BULK_VALUE_SAME = "value_same"
BULK_SET_FIELD = "set_field"
BULK_ACTIONS = (BULK_IGNORE, BULK_VALUE_EACH, BULK_VALUE_SAME, BULK_SET_FIELD)

#: One field's effective source inside a group: ("group_constant", value) /
#: ("column", column index) / ("constant", value).
Source = tuple[str, object]


@dataclass(frozen=True)
class ColumnMapping:
    column: int  # source column index
    field: str | None = None  # catalogue key; None = ignored
    group: int | None = None  # measurement group tag (measurement scope only)


@dataclass(frozen=True)
class ConstantMapping:
    """One field taking the same value across its whole scope."""

    field: str  # catalogue key
    value: object  # typed value; the *name* for an FK field


@dataclass(frozen=True)
class GroupConstant:
    """One measurement-scoped field's constant for one group only."""

    group: int
    field: str  # catalogue key (measurement scope)
    value: object


@dataclass(frozen=True)
class ValueBinding:
    """One source text bound to one database entity, decided by the user.

    A sheet names its entities in its own words. When the name is not the one
    the database holds, only the user can say which row was meant — a binding
    is that answer, remembered per field and per text.
    """

    field: str  # catalogue key
    text: str  # the value as it appears in the sheet
    entity_id: int


@dataclass(frozen=True)
class MappingSpec:
    mappings: tuple[ColumnMapping, ...]
    constants: tuple[ConstantMapping, ...] = ()
    group_constants: tuple[GroupConstant, ...] = ()
    bindings: tuple[ValueBinding, ...] = ()

    def mapped(self) -> tuple[ColumnMapping, ...]:
        """The assignments only — ignored columns dropped."""
        return tuple(m for m in self.mappings if m.field is not None)

    def for_column(self, column: int) -> ColumnMapping:
        for m in self.mappings:
            if m.column == column:
                return m
        raise KeyError(f"column {column} is not part of this mapping")


@dataclass(frozen=True)
class MappingError:
    """One incoherence in a spec. ``columns`` names the offenders."""

    message: str
    columns: tuple[int, ...]


def empty_spec(block: SheetBlock) -> MappingSpec:
    """The state the mapping table starts from: every column ignored.

    The field replicate defaults to the constant 1 — a routine single-sample
    sheet needs no extra thought.
    """
    return MappingSpec(
        tuple(ColumnMapping(column=c) for c in block.columns),
        constants=(ConstantMapping("sample.replicate", 1),),
    )


def build_spec(
    block: SheetBlock,
    catalogue: Catalogue,
    assignments: dict[int, str | None],
    groups: dict[int, int] | None = None,
    *,
    constants: dict[str, object] | tuple[ConstantMapping, ...] | None = None,
    group_constants: dict[tuple[int, str], object] | tuple[GroupConstant, ...] | None = None,
    bindings: tuple[ValueBinding, ...] | None = None,
) -> MappingSpec:
    """Assemble a spec from ``{column: catalogue key or None}``.

    Columns absent from ``assignments`` stay ignored. Measurement-scoped
    assignments take their group from ``groups``; without one they normalize
    to a singleton group (their own column index) — one measurement per value
    column by default. ``constants`` is ``{field: value}`` (or ready-made
    ``ConstantMapping``); ``group_constants`` is ``{(group, field): value}``.
    """
    groups = groups or {}
    mappings = []
    for col in block.columns:
        key = assignments.get(col)
        if key is None:
            mappings.append(ColumnMapping(column=col))
            continue
        try:
            scope = catalogue.by_key(key).scope
        except KeyError:
            scope = None  # unknown field: kept so validate() can name the column
        group = groups.get(col, col) if scope == "measurement" else None
        mappings.append(ColumnMapping(column=col, field=key, group=group))
    return MappingSpec(
        tuple(mappings),
        constants=_as_constants(constants),
        group_constants=_as_group_constants(group_constants),
        bindings=tuple(bindings or ()),
    )


def _as_constants(items) -> tuple[ConstantMapping, ...]:
    if items is None:
        return ()
    if isinstance(items, dict):
        return tuple(ConstantMapping(k, v) for k, v in items.items())
    return tuple(items)


def _as_group_constants(items) -> tuple[GroupConstant, ...]:
    if items is None:
        return ()
    if isinstance(items, dict):
        return tuple(GroupConstant(g, f, v) for (g, f), v in items.items())
    return tuple(items)


# --- constants and group constants ------------------------------------------


def with_constant(spec: MappingSpec, field: str, value: object) -> MappingSpec:
    """Set (or replace) a field's scope-wide constant."""
    rest = tuple(c for c in spec.constants if c.field != field)
    return replace(spec, constants=(*rest, ConstantMapping(field, value)))


def without_constant(spec: MappingSpec, field: str) -> MappingSpec:
    return replace(spec, constants=tuple(c for c in spec.constants if c.field != field))


def constant_for(spec: MappingSpec, field: str) -> object | None:
    """A field's scope-wide constant value, or None."""
    for c in spec.constants:
        if c.field == field:
            return c.value
    return None


def with_group_constant(spec: MappingSpec, group: int, field: str, value: object) -> MappingSpec:
    """Set (or replace) one field's constant for one group."""
    rest = tuple(c for c in spec.group_constants if (c.group, c.field) != (group, field))
    return replace(spec, group_constants=(*rest, GroupConstant(group, field, value)))


def without_group_constant(spec: MappingSpec, group: int, field: str) -> MappingSpec:
    return replace(
        spec,
        group_constants=tuple(
            c for c in spec.group_constants if (c.group, c.field) != (group, field)
        ),
    )


# --- value bindings ----------------------------------------------------------


def with_binding(spec: MappingSpec, field: str, text: str, entity_id: int) -> MappingSpec:
    """Bind (or re-bind) one source text of one field to a database entity."""
    rest = tuple(b for b in spec.bindings if (b.field, b.text) != (field, text))
    return replace(spec, bindings=(*rest, ValueBinding(field, text, entity_id)))


def without_binding(spec: MappingSpec, field: str, text: str) -> MappingSpec:
    return replace(
        spec, bindings=tuple(b for b in spec.bindings if (b.field, b.text) != (field, text))
    )


def binding_for(spec: MappingSpec, field: str, text: str) -> int | None:
    """The entity a source text is bound to for one field, or None."""
    for b in spec.bindings:
        if (b.field, b.text) == (field, text):
            return b.entity_id
    return None


def bindings_of(spec: MappingSpec, field: str) -> dict[str, int]:
    """Every binding made for one field, by source text."""
    return {b.text: b.entity_id for b in spec.bindings if b.field == field}


# --- groups and resolution ---------------------------------------------------


def _group_of(mapping: ColumnMapping) -> int:
    """A measurement mapping's effective group — the singleton when unset."""
    return mapping.group if mapping.group is not None else mapping.column


def groups_of(spec: MappingSpec, catalogue: Catalogue) -> tuple[int, ...]:
    """The spec's measurement groups, sorted — one per composed measurement."""
    groups = set()
    for m in spec.mapped():
        try:
            scope = catalogue.by_key(m.field).scope
        except KeyError:
            continue  # unknown fields are validate()'s business
        if scope == "measurement":
            groups.add(_group_of(m))
    return tuple(sorted(groups))


def source_for(
    spec: MappingSpec, catalogue: Catalogue, group: int, field: str
) -> Source | None:
    """One measurement field's effective source inside one group.

    Group constant, then a column mapped to the field in this group, then the
    scope-wide constant. None when the field has no source for the group.
    """
    for c in spec.group_constants:
        if c.group == group and c.field == field:
            return ("group_constant", c.value)
    for m in spec.mapped():
        if m.field == field and _group_of(m) == group:
            return ("column", m.column)
    value = constant_for(spec, field)
    return ("constant", value) if value is not None else None


def identity_for_group(
    spec: MappingSpec, catalogue: Catalogue, group: int
) -> dict[str, Source | None]:
    """A group's full identity, in the terms this kind of import uses."""
    return {key: source_for(spec, catalogue, group, key) for key in catalogue.identity_keys}


def row_series(
    spec: MappingSpec, block: SheetBlock, catalogue: Catalogue, key: str
) -> pd.Series | None:
    """A file/row-scoped field's value on every data row.

    A constant applies its value to every row; a column source yields the
    column's values. None when the field has no source.
    """
    field = catalogue.by_key(key)
    if field.scope == "measurement":
        raise ValueError(f"{key} is measurement-scoped — use group_series")
    for m in spec.mapped():
        if m.field == key:
            return block.data[m.column]
    value = constant_for(spec, key)
    if value is None:
        return None
    return pd.Series([value] * len(block.data), index=block.data.index, name=key)


def group_series(
    spec: MappingSpec, block: SheetBlock, catalogue: Catalogue, key: str, group: int
) -> pd.Series | None:
    """A measurement-scoped field's value on every data row for one group.

    A group constant or scope-wide constant applies its value to every row of
    the group's measurement; a column source yields the column's values. None
    when the field has no source for this group.
    """
    source = source_for(spec, catalogue, group, key)
    if source is None:
        return None
    kind, value = source
    if kind == "column":
        return block.data[value]
    return pd.Series([value] * len(block.data), index=block.data.index, name=key)


# --- bulk actions -------------------------------------------------------------


def apply_bulk(
    spec: MappingSpec,
    block: SheetBlock,
    catalogue: Catalogue,
    columns,
    action: str,
    *,
    field: str | None = None,
) -> MappingSpec:
    """Apply one action to every selected column, by column index.

    Unselected columns are returned untouched. The four actions:

    - ``ignore`` — clear the selection's mappings;
    - ``value_each`` — every selected column is a Value in its own group;
    - ``value_same`` — every selected column is a Value in one shared group
      (the smallest group already present in the selection, else its smallest
      column — re-applying the same selection is a no-op);
    - ``set_field`` — every selected column maps to ``field`` (a measurement
      field keeps the column's existing group, else takes a singleton).
    """
    selected = {c for c in columns if c in set(block.columns)}
    if not selected:
        return spec
    if action not in BULK_ACTIONS:
        raise ValueError(f"unknown bulk action: {action!r}")
    if action == BULK_SET_FIELD and field is None:
        raise ValueError("set_field needs a catalogue field")

    shared = None
    if action == BULK_VALUE_SAME:
        existing = [
            _group_of(m)
            for m in spec.mapped()
            if m.column in selected and m.field == catalogue.value_key
        ]
        shared = min(existing) if existing else min(selected)

    def replacement(m: ColumnMapping) -> ColumnMapping:
        if action == BULK_IGNORE:
            return ColumnMapping(column=m.column)
        if action == BULK_VALUE_EACH:
            return ColumnMapping(column=m.column, field=catalogue.value_key, group=m.column)
        if action == BULK_VALUE_SAME:
            return ColumnMapping(column=m.column, field=catalogue.value_key, group=shared)
        try:
            scope = catalogue.by_key(field).scope
        except KeyError:
            scope = None  # unknown field: kept so validate() can name the column
        group = (m.group if m.group is not None else m.column) if scope == "measurement" else None
        return ColumnMapping(column=m.column, field=field, group=group)

    return replace(
        spec,
        mappings=tuple(replacement(m) if m.column in selected else m for m in spec.mappings),
    )


# --- validation and completeness ---------------------------------------------


def validate(spec: MappingSpec, block: SheetBlock, catalogue: Catalogue) -> list[MappingError]:
    """Reject an incoherent specification, naming the offending columns."""
    errors: list[MappingError] = []
    labels = block.labels()

    def name(column: int) -> str:
        return f"'{labels[list(block.columns).index(column)]}' (column {column})"

    known = {f.key for f in catalogue.fields}
    by_field: dict[str, list[ColumnMapping]] = {}
    for m in spec.mapped():
        if m.field not in known:
            errors.append(
                MappingError(
                    f"Column {name(m.column)} maps to '{m.field}', which the "
                    "import does not accept.",
                    (m.column,),
                )
            )
            continue
        by_field.setdefault(m.field, []).append(m)

    for key, assignments in by_field.items():
        field = catalogue.by_key(key)
        if field.scope in ("file", "row"):
            if len(assignments) > 1:
                cols = tuple(m.column for m in assignments)
                errors.append(
                    MappingError(
                        f"Columns {_join(name(c) for c in cols)} both map to "
                        f"'{field.label}' — a {field.scope}-scoped field takes one "
                        "column.",
                        cols,
                    )
                )
            if constant_for(spec, key) is not None:
                cols = tuple(m.column for m in assignments)
                errors.append(
                    MappingError(
                        f"Column {_join(name(c) for c in cols)} maps to "
                        f"'{field.label}' and a constant is set for it too — "
                        "keep one source.",
                        cols,
                    )
                )
        if field.scope == "measurement":
            by_group: dict[int, list[int]] = {}
            for m in assignments:
                by_group.setdefault(_group_of(m), []).append(m.column)
            for group, cols_list in by_group.items():
                if len(cols_list) > 1:
                    cols = tuple(cols_list)
                    errors.append(
                        MappingError(
                            f"Columns {_join(name(c) for c in cols)} both map to "
                            f"'{field.label}' in measurement group {group} — one "
                            f"'{field.label}' per group.",
                            cols,
                        )
                    )

    seen_constants: set[str] = set()
    for c in spec.constants:
        if c.field not in known:
            errors.append(
                MappingError(
                    f"A constant is set for '{c.field}', which the import does "
                    "not accept.",
                    (),
                )
            )
        elif c.field in seen_constants:
            errors.append(
                MappingError(
                    f"'{catalogue.by_key(c.field).label}' has two constants — "
                    "keep one.",
                    (),
                )
            )
        seen_constants.add(c.field)

    for gc in spec.group_constants:
        if gc.field not in known:
            errors.append(
                MappingError(
                    f"Group {gc.group} sets '{gc.field}', which the import does "
                    "not accept.",
                    (),
                )
            )
            continue
        field = catalogue.by_key(gc.field)
        if field.scope != "measurement":
            errors.append(
                MappingError(
                    f"Group {gc.group} sets '{field.label}', which is "
                    f"{field.scope}-scoped — groups only carry measurement fields.",
                    (),
                )
            )
            continue
        clash = [
            m.column
            for m in spec.mapped()
            if m.field == gc.field and _group_of(m) == gc.group
        ]
        if clash:
            errors.append(
                MappingError(
                    f"Group {gc.group} takes '{field.label}' from column "
                    f"{_join(name(c) for c in clash)} and from a group constant — "
                    "keep one source.",
                    tuple(clash),
                )
            )
    return errors


def missing_required(spec: MappingSpec, catalogue: Catalogue) -> list[FieldMeta]:
    """Required fields with no source yet, honouring the row→measurement fallback.

    A required measurement field is satisfied only when *every* group has a
    source for it — a group column, a group constant, or a scope-wide
    constant. Constants count as sources at every scope.
    """
    column_sourced = {m.field for m in spec.mapped()}
    constant_sourced = {c.field for c in spec.constants}
    groups = groups_of(spec, catalogue)
    missing = []
    for f in catalogue.fields:
        if not f.required:
            continue
        if f.scope in ("file", "row"):
            if f.key not in column_sourced and f.key not in constant_sourced:
                missing.append(f)
            continue
        # measurement scope: every group needs a source
        if groups and all(source_for(spec, catalogue, g, f.key) for g in groups):
            continue
        # a required measurement field can be answered by its row-scoped
        # equivalent — the builder inherits it (a measurement's location
        # defaults to its sample's)
        fallback = catalogue.satisfied_by.get(f.key)
        if fallback and (fallback in column_sourced or fallback in constant_sourced):
            continue
        missing.append(f)
    return missing


def groups_lacking(spec: MappingSpec, catalogue: Catalogue, key: str) -> tuple[int, ...]:
    """The groups with no source for a measurement field — for partial coverage."""
    return tuple(
        g for g in groups_of(spec, catalogue) if not source_for(spec, catalogue, g, key)
    )


# --- the editor frame ----------------------------------------------------------


def mapping_frame(block: SheetBlock, catalogue: Catalogue, spec: MappingSpec) -> pd.DataFrame:
    """One row per sheet column, **indexed by source column index**.

    The frame is what the mapping editor edits; because its index is the
    column index, editor state can never collapse repeated header names into
    one mapping. Header and banner are read-only context. ``Group`` is
    editable and meaningful only for measurement-scoped assignments.
    """
    key_to_option = {key: label for label, key in catalogue.option_labels().items()}
    rows = []
    for i, col in enumerate(block.columns):
        m = spec.for_column(col)
        rows.append(
            {
                "Header": block.headers[i],
                "Banner": block.banner_path(col),
                "Maps to": IGNORE if m.field is None else key_to_option[m.field],
                "Group": m.group if m.field is not None and m.group is not None else pd.NA,
            }
        )
    frame = pd.DataFrame(rows, index=pd.Index(list(block.columns), name="column"))
    frame["Group"] = frame["Group"].astype("Int64")
    return frame


def spec_from_frame(
    block: SheetBlock,
    catalogue: Catalogue,
    frame: pd.DataFrame,
    previous: MappingSpec | None = None,
) -> MappingSpec:
    """Read an edited mapping frame back into a spec, by column index.

    Constants, group constants and value bindings live outside the frame; they
    carry over from ``previous`` so editing the table can never silently drop
    them.
    """
    options = catalogue.option_labels()
    assignments: dict[int, str | None] = {}
    groups: dict[int, int] = {}
    for col in block.columns:
        picked = frame.loc[col, "Maps to"]
        assignments[col] = None if picked in (None, IGNORE) else options[picked]
        group = frame.loc[col, "Group"] if "Group" in frame.columns else None
        if group is not None and pd.notna(group):
            groups[col] = int(group)
    return build_spec(
        block,
        catalogue,
        assignments,
        groups,
        constants=previous.constants if previous else None,
        group_constants=previous.group_constants if previous else None,
        bindings=previous.bindings if previous else None,
    )


def _join(parts) -> str:
    parts = list(parts)
    if len(parts) <= 2:
        return " and ".join(parts)
    return ", ".join(parts[:-1]) + f" and {parts[-1]}"
