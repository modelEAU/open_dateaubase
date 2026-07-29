"""Column mapping: which catalogue field each sheet column feeds.

A mapping specification says, per **source column index** — never per header
text, which a sheet may repeat — what that column holds. Two independent
properties describe every assignment, per the field catalogue:

- **scope** — what the value attaches to (file / row / measurement) — comes
  from the field and is never chosen;
- **source** — where the value comes from (a column, a constant, or nothing).
  This module ships the column source; constants land in the next slice.

Measurement-scoped assignments carry a **group** tag: columns sharing a group
compose one measurement. Without an explicit group an assignment normalizes to
a singleton group — one measurement per value column by default.

Pure: no Streamlit, no database.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from app.components.field_catalogue import Catalogue, FieldMeta
from app.components.sheet_block import SheetBlock

#: The display string for an unmapped column.
IGNORE = "— ignore —"

#: A required measurement-scoped field is satisfied when its row-scoped
#: equivalent is sourced — the builder inherits it (the measurement's location
#: defaults to the sample's).
_SATISFIED_BY = {"measurement.sampling_point_id": "sample.sampling_point_id"}


@dataclass(frozen=True)
class ColumnMapping:
    column: int  # source column index
    field: str | None = None  # catalogue key; None = ignored
    group: int | None = None  # measurement group tag (measurement scope only)


@dataclass(frozen=True)
class MappingSpec:
    mappings: tuple[ColumnMapping, ...]

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
    """The state the mapping table starts from: every column ignored."""
    return MappingSpec(tuple(ColumnMapping(column=c) for c in block.columns))


def build_spec(
    block: SheetBlock,
    catalogue: Catalogue,
    assignments: dict[int, str | None],
    groups: dict[int, int] | None = None,
) -> MappingSpec:
    """Assemble a spec from ``{column: catalogue key or None}``.

    Columns absent from ``assignments`` stay ignored. Measurement-scoped
    assignments take their group from ``groups``; without one they normalize
    to a singleton group (their own column index) — one measurement per value
    column by default.
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
    return MappingSpec(tuple(mappings))


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
        if field.scope in ("file", "row") and len(assignments) > 1:
            cols = tuple(m.column for m in assignments)
            errors.append(
                MappingError(
                    f"Columns {_join(name(c) for c in cols)} both map to "
                    f"'{field.label}' — a {field.scope}-scoped field takes one "
                    "column.",
                    cols,
                )
            )
        if field.scope == "measurement":
            by_group: dict[int, list[int]] = {}
            for m in assignments:
                group = m.group if m.group is not None else m.column
                by_group.setdefault(group, []).append(m.column)
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
    return errors


def missing_required(spec: MappingSpec, catalogue: Catalogue) -> list[FieldMeta]:
    """Required fields with no source yet, honouring row→measurement fallback."""
    sourced = {m.field for m in spec.mapped()}
    missing = []
    for f in catalogue.fields:
        if not f.required or f.key in sourced:
            continue
        fallback = _SATISFIED_BY.get(f.key)
        if fallback and fallback in sourced:
            continue
        missing.append(f)
    return missing


def mapping_frame(block: SheetBlock, catalogue: Catalogue, spec: MappingSpec) -> pd.DataFrame:
    """One row per sheet column, **indexed by source column index**.

    The frame is what the mapping editor edits; because its index is the
    column index, editor state can never collapse repeated header names into
    one mapping. Header and banner are read-only context.
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
            }
        )
    return pd.DataFrame(rows, index=pd.Index(list(block.columns), name="column"))


def spec_from_frame(block: SheetBlock, catalogue: Catalogue, frame: pd.DataFrame) -> MappingSpec:
    """Read an edited mapping frame back into a spec, by column index."""
    options = catalogue.option_labels()
    assignments: dict[int, str | None] = {}
    for col in block.columns:
        picked = frame.loc[col, "Maps to"]
        assignments[col] = None if picked in (None, IGNORE) else options[picked]
    return build_spec(block, catalogue, assignments)


def _join(parts) -> str:
    parts = list(parts)
    if len(parts) <= 2:
        return " and ".join(parts)
    return ", ".join(parts[:-1]) + f" and {parts[-1]}"
