"""Composing per-row sample and measurement payloads from a mapping spec.

A source row expands into as many measurements as it has value columns — one
per measurement group. Row-scoped values are shared across every measurement
on their row; file-scoped values apply to every row. Foreign-key fields carry
the name the user typed; this is where that name is resolved to a database
id — exactly, case aside, or through a binding the user made. An unmatched
name aborts the whole build and names itself and its column, never guessing
and never creating.

Two measurements collapse onto one database row when they share a sample
identity, a series identity and an analytical replicate — the same key the
database itself refuses a duplicate of. That collision is reported before
anything is submitted, naming the offending rows and groups.

Pure: no Streamlit, no database — ``lookup`` is the only side-effecting
callable, and it is passed in.
"""

from __future__ import annotations

import datetime as dt
import zoneinfo
from collections.abc import Callable
from dataclasses import dataclass
from difflib import get_close_matches

import pandas as pd

from app.components.column_mapping import (
    MappingSpec,
    bindings_of,
    constant_for,
    group_series,
    groups_of,
    missing_required,
    row_series,
    source_for,
)
from app.components.datetime_parse import dst_gaps, parse_values, to_utc
from app.components.field_catalogue import Catalogue, FieldMeta
from app.components.sheet_block import SheetBlock

#: Per fk_table, the lookup dict key holding the display name — the lookup
#: endpoints are not consistent about this (unit vs name vs label vs
#: parameter_name), so it cannot be guessed.
_LABEL_KEYS = {
    "SamplingPoint": "label",
    "Parameter": "parameter_name",
    "Unit": "unit",
    "Laboratory": "name",
    "SampleKind": "name",
    "SampleMaterialKind": "name",
    "SampleCollectionKind": "name",
    "Equipment": "identifier",
    "Campaign": "name",
    "Person": "label",
    "Procedure": "procedure_name",
    "QualityCode": "name",
}

#: table name -> its candidate rows (id + display name dicts), e.g. via
#: ``api_client.list_sampling_point_lookup``.
LookupFn = Callable[[str], list[dict]]


def label_key(table: str) -> str:
    """The key holding the display name in one table's lookup rows."""
    return _LABEL_KEYS.get(table, "name")


@dataclass(frozen=True)
class BuildError:
    message: str
    row: object | None = None
    column: int | None = None


@dataclass(frozen=True)
class MeasurementCandidate:
    group: int
    parameter_id: int
    sampling_point_id: int
    unit_id: int
    laboratory_id: int | None
    series_name: str
    value: float
    replicate: int
    analyst_person_id: int | None
    procedure_id: int | None
    analysis_datetime: dt.datetime | None
    quality_code_id: int | None
    notes: str | None


@dataclass(frozen=True)
class RowPlan:
    row: object  # the source row's label in block.data
    sample: dict  # SampleCreateRequest-shaped
    measurements: tuple[MeasurementCandidate, ...]


@dataclass(frozen=True)
class BuildResult:
    experiment: dict | None  # LabIngestRequest file-scope fields
    rows: tuple[RowPlan, ...]
    errors: tuple[BuildError, ...]
    collisions: tuple[BuildError, ...]

    @property
    def ok(self) -> bool:
        return not self.errors and not self.collisions

    def counts(self) -> dict[str, int]:
        measurements = sum(len(r.measurements) for r in self.rows)
        series = {
            (m.parameter_id, m.sampling_point_id, m.laboratory_id)
            for r in self.rows
            for m in r.measurements
        }
        return {
            "experiments": 1 if self.rows else 0,
            "samples": len({sample_key(r.sample) for r in self.rows}),
            "series": len(series),
            "measurements": measurements,
        }


def sample_key(sample: dict) -> tuple:
    """A sample payload's database identity — the columns of UQ_Sample_Identity.

    Several source rows may describe one physical sample (a long-format sheet
    puts one parameter per row), so this is what counts a sample and what is
    submitted once.
    """
    return (
        sample["sampling_point_id"],
        sample["sample_datetime_start"],
        sample.get("sample_kind_id"),
        sample.get("replicate", 1),
    )


def build(
    spec: MappingSpec,
    block: SheetBlock,
    catalogue: Catalogue,
    lookup: LookupFn,
    tz: zoneinfo.ZoneInfo,
    column_formats: dict[int, str | None],
) -> BuildResult:
    """Build every row's sample and candidate measurements, or explain why not.

    ``column_formats`` gives the strptime format chosen for each non-native
    date/time column that is actually mapped or constant-sourced by a
    datetime field; a column missing from it (and not already a native
    datetime column) is an unresolved date format, reported like any other
    unmatched name. Errors abort the whole build — no partial result.
    """
    labels = block.labels()
    columns = list(block.columns)
    errors = [
        BuildError(f"'{f.label}' has no source — required before this can be submitted.")
        for f in missing_required(spec, catalogue)
    ]
    if errors:
        return BuildResult(None, (), tuple(errors), ())

    for column in _unresolved_datetime_columns(spec, catalogue, block, column_formats):
        errors.append(
            BuildError(
                f"No date format chosen for '{labels[columns.index(column)]}' "
                f"(column {column})."
            )
        )
    if errors:
        return BuildResult(None, (), tuple(errors), ())

    cache: dict[str, list[dict]] = {}
    batch_fields = [f for f in catalogue.fields if f.scope == "file"]
    sample_fields = [f for f in catalogue.fields if f.scope == "row"]
    measurement_fields = [f for f in catalogue.fields if f.scope == "measurement"]
    groups = groups_of(spec, catalogue)

    batch_values = {
        f.key: _resolve_field(spec, block, catalogue, f, tz, column_formats, cache, lookup, errors, labels, columns)
        for f in batch_fields
    }
    sample_values = {
        f.key: _resolve_field(spec, block, catalogue, f, tz, column_formats, cache, lookup, errors, labels, columns)
        for f in sample_fields
    }
    group_values = {
        group: {
            f.key: _resolve_field(
                spec, block, catalogue, f, tz, column_formats, cache, lookup, errors, labels, columns, group=group
            )
            for f in measurement_fields
        }
        for group in groups
    }
    if errors:
        # a scope-wide constant is resolved once per group — dedupe its errors
        return BuildResult(None, (), tuple(dict.fromkeys(errors)), ())

    # raw (unresolved) identity text, for a human-readable series name
    sample_sampling_point_text = row_series(spec, block, catalogue, "sample.sampling_point_id")
    identity_text = {
        group: {
            "measurement.parameter_id": group_series(spec, block, catalogue, "measurement.parameter_id", group),
            "measurement.sampling_point_id": (
                group_series(spec, block, catalogue, "measurement.sampling_point_id", group)
                if source_for(spec, catalogue, group, "measurement.sampling_point_id")
                else sample_sampling_point_text
            ),
            "measurement.laboratory_id": group_series(spec, block, catalogue, "measurement.laboratory_id", group),
        }
        for group in groups
    }

    experiment = {
        f.key.split(".", 1)[1]: _scalar(batch_values[f.key])
        for f in batch_fields
        if _scalar(batch_values[f.key]) is not None
    }

    rows: list[RowPlan] = []
    for row in block.data.index:
        sample = {
            f.key.split(".", 1)[1]: _at(sample_values[f.key], row)
            for f in sample_fields
            if _at(sample_values[f.key], row) is not None
        }
        if "sampling_point_id" not in sample or "sample_datetime_start" not in sample:
            continue  # this row's required data is genuinely absent
        sample.setdefault("replicate", 1)

        measurements = []
        for group in groups:
            gv = group_values[group]
            try:
                value = _as_float(_at(gv.get("measurement.value"), row))
            except (TypeError, ValueError):
                value = None
            if value is None:
                continue  # sparse sheet: nothing reported here for this group
            parameter_id = _as_int(_at(gv.get("measurement.parameter_id"), row))
            unit_id = _as_int(_at(gv.get("measurement.unit_id"), row))
            if parameter_id is None or unit_id is None:
                continue  # a source data hole, not a mapping gap (already checked scope-wide)
            sampling_point_id = _as_int(_at(gv.get("measurement.sampling_point_id"), row)) or _as_int(
                sample["sampling_point_id"]
            )
            assert sampling_point_id is not None
            measurements.append(
                MeasurementCandidate(
                    group=group,
                    parameter_id=parameter_id,
                    sampling_point_id=sampling_point_id,
                    unit_id=unit_id,
                    laboratory_id=_as_int(_at(gv.get("measurement.laboratory_id"), row)),
                    series_name=_series_name(identity_text[group], row),
                    value=value,
                    replicate=_as_int(_at(gv.get("measurement.replicate"), row)) or 1,
                    analyst_person_id=_as_int(_at(gv.get("measurement.analyst_person_id"), row)),
                    procedure_id=_as_int(_at(gv.get("measurement.procedure_id"), row)),
                    analysis_datetime=_as_datetime(_at(gv.get("measurement.analysis_datetime"), row)),
                    quality_code_id=_as_int(_at(gv.get("measurement.quality_code_id"), row)),
                    notes=_as_text(_at(gv.get("measurement.notes"), row)),
                )
            )
        if measurements:
            rows.append(RowPlan(row=row, sample=sample, measurements=tuple(measurements)))

    value_column = {
        (m.group if m.group is not None else m.column): m.column
        for m in spec.mapped()
        if m.field == "measurement.value"
    }
    return BuildResult(experiment, tuple(rows), (), tuple(_collisions(rows, value_column, labels, columns)))


def _collisions(
    rows: list[RowPlan], value_column: dict[int, int], labels: list[str], columns: list[int]
) -> list[BuildError]:
    """Measurements sharing a sample, series and replicate — the database's own key."""
    seen: dict[tuple, list[str]] = {}
    for r in rows:
        for m in r.measurements:
            series_key = (m.parameter_id, m.sampling_point_id, m.laboratory_id)
            col = value_column.get(m.group)
            column_ref = f"'{labels[columns.index(col)]}' (column {col})" if col is not None else f"group {m.group}"
            where = f"row {r.row}: {column_ref}"
            seen.setdefault((sample_key(r.sample), series_key, m.replicate), []).append(where)
    return [
        BuildError(
            f"{len(wheres)} measurements collapse onto the same sample, series and "
            f"replicate ({'; '.join(wheres)}) — differentiate them by replicate, "
            "sample or laboratory."
        )
        for wheres in seen.values()
        if len(wheres) > 1
    ]


def _series_name(identity_text: dict[str, pd.Series | None], row) -> str:
    """A readable series label, laboratory-aware so two labs never share a name."""
    parameter = _at(identity_text["measurement.parameter_id"], row)
    sampling_point = _at(identity_text["measurement.sampling_point_id"], row)
    laboratory = _at(identity_text["measurement.laboratory_id"], row)
    name = f"{parameter} @ {sampling_point}" if sampling_point else str(parameter)
    return f"{name} ({laboratory})" if laboratory else name


def _resolve_field(
    spec: MappingSpec,
    block: SheetBlock,
    catalogue: Catalogue,
    field: FieldMeta,
    tz: zoneinfo.ZoneInfo,
    column_formats: dict[int, str | None],
    cache: dict[str, list[dict]],
    lookup: LookupFn,
    errors: list[BuildError],
    labels: list[str],
    columns: list[int],
    *,
    group: int | None = None,
) -> pd.Series | None:
    """One field's per-row values: datetimes converted to UTC, FK names resolved to ids."""
    if group is not None:
        source = source_for(spec, catalogue, group, field.key)
        values = group_series(spec, block, catalogue, field.key, group)
    else:
        mapped_col = next((m.column for m in spec.mapped() if m.field == field.key), None)
        if mapped_col is not None:
            source = ("column", mapped_col)
        else:
            const = constant_for(spec, field.key)
            source = ("constant", const) if const is not None else None
        values = row_series(spec, block, catalogue, field.key)
    if values is None or source is None:
        return values

    if field.value_type == "datetime":
        kind, ref = source
        col = int(ref) if kind == "column" else None  # type: ignore[arg-type]
        fmt = None if col is None or col in block.datetime_columns else column_formats.get(col)
        parsed = parse_values(values, fmt)
        utc = to_utc(parsed.wall_clock, tz)
        gaps = dst_gaps(parsed.wall_clock, utc)
        if gaps:
            where = (
                f"column '{labels[columns.index(col)]}' (column {col})"
                if col is not None
                else f"'{field.label}'"
            )
            quoted = ", ".join(f"row {row} ({text})" for row, text in gaps[:3])
            errors.append(
                BuildError(
                    f"{len(gaps)} time(s) in {where} do not exist, or happen "
                    f"twice, in {tz.key} — the clocks changed: {quoted}"
                    f"{'…' if len(gaps) > 3 else ''}.",
                    column=col,
                )
            )
        return utc

    if not field.fk_table:
        return values

    kind, ref = source
    column = int(ref) if kind == "column" else None  # type: ignore[arg-type]
    where = (
        f"column '{labels[columns.index(column)]}' (column {column})"
        if column is not None
        else f"'{field.label}'"
    )
    id_key = field.key.rsplit(".", 1)[-1]
    bound = bindings_of(spec, field.key)
    raw_texts = sorted({str(v).strip() for v in values if _present(v)})
    resolved = {
        t: bound.get(t, _resolve_name(cache, lookup, field.fk_table, id_key, t))
        for t in raw_texts
    }
    for text, rid in resolved.items():
        if rid is None:
            errors.append(
                BuildError(f"'{text}' in {where} does not match any {field.fk_table} on record.", column=column)
            )
    return pd.Series(
        [resolved.get(str(v).strip()) if _present(v) else None for v in values],
        index=values.index,
    )


def _resolve_name(cache: dict[str, list[dict]], lookup: LookupFn, table: str, id_key: str, text: str) -> int | None:
    """One name's id, matched exactly and then case-insensitively, or None.

    Never approximately: ``"COD tot"`` is not ``COD``, and writing data against
    the wrong entity is worse than refusing to write it.
    """
    pool = cache.setdefault(table, lookup(table))
    key = label_key(table)
    names = {str(c[key]): c for c in pool if c.get(key)}
    hit = names.get(text) or next(
        (c for name, c in names.items() if name.casefold() == text.casefold()), None
    )
    return hit.get(id_key) if hit else None


def suggest(pool: list[dict], key: str, text: str) -> str | None:
    """The closest name in a lookup pool to a source text, or None.

    A guess belongs where the user can see and accept it — this feeds the
    entity picker, never the resolution above.
    """
    names = [str(c[key]) for c in pool if c.get(key)]
    hit = get_close_matches(text, names, n=1, cutoff=0.6)
    return hit[0] if hit else None


def _unresolved_datetime_columns(
    spec: MappingSpec, catalogue: Catalogue, block: SheetBlock, column_formats: dict[int, str | None]
) -> list[int]:
    """Text columns feeding a datetime field with no chosen format yet."""
    columns: set[int] = set()

    def check(source: tuple[str, object] | None) -> None:
        if source and source[0] == "column":
            col = int(source[1])  # type: ignore[arg-type]
            if col not in block.datetime_columns and col not in column_formats:
                columns.add(col)

    for f in catalogue.fields:
        if f.value_type != "datetime":
            continue
        if f.scope == "measurement":
            for group in groups_of(spec, catalogue):
                check(source_for(spec, catalogue, group, f.key))
            continue
        mapped = next((m for m in spec.mapped() if m.field == f.key), None)
        if mapped is not None:
            check(("column", mapped.column))
    return sorted(columns)


def _at(series: pd.Series | None, row) -> object:
    """One row's value from a resolved series, ``None`` for missing/NaN."""
    if series is None:
        return None
    value = series.loc[row]
    return None if not _present(value) else _native(value)


def _scalar(series: pd.Series | None) -> object:
    """A file-scoped field's one value — its first non-null entry."""
    if series is None:
        return None
    present = [v for v in series if _present(v)]
    return _native(present[0]) if present else None


def _native(value):
    """A plain Python scalar — never a numpy int64/float64, unfit for JSON."""
    if isinstance(value, pd.Timestamp):
        return value.to_pydatetime()
    if hasattr(value, "item"):
        return value.item()
    return value


def _present(value) -> bool:
    if value is None:
        return False
    try:
        if pd.isna(value):
            return False
    except (TypeError, ValueError):
        pass
    return bool(str(value).strip())


def _as_int(value: object) -> int | None:
    return None if value is None else int(value)  # type: ignore[call-overload]


def _as_float(value: object) -> float | None:
    return None if value is None else float(value)  # type: ignore[arg-type]


def _as_datetime(value: object) -> dt.datetime | None:
    return None if value is None else value  # type: ignore[return-value]


def _as_text(value: object) -> str | None:
    return None if value is None else str(value)
