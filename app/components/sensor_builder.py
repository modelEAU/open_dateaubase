"""Composing sensor ingest requests from a mapping spec.

Sensor ingest is one channel and a list of points, so each measurement group
becomes one request: a wide sheet of ten tag columns is ten posts, not one.
Which endpoint a group uses follows from how it names its channel — a SCADA tag,
or a piece of equipment on a declared signal interface — and naming it both ways
or neither is refused here rather than by the server.

The server resolves reference data by name, but not uniformly: a parameter or a
unit it does not have is a 422 before anything is written, while a system,
interface or piece of equipment is created for you. So an unknown name is an
error in the first case and a warning in the second, said before the post.

Pure: no Streamlit, no database — ``lookup`` is the only side-effecting
callable, and it is passed in.
"""

from __future__ import annotations

import zoneinfo
from dataclasses import dataclass

import pandas as pd

from app.components.column_mapping import (
    MappingSpec,
    binding_for,
    group_series,
    groups_of,
    row_series,
)
from app.components.datetime_parse import dst_gaps, parse_values, to_utc
from app.components.field_catalogue import Catalogue
from app.components.measurement_builder import BuildError, LookupFn, label_key
from app.components.schema_registry import load_table
from app.components.sheet_block import SheetBlock

TAGGED = "/ingest/sensor"
TAGLESS = "/ingest/sensor-tagless"

#: The tables sensor ingest creates on the fly when strict=False. Everything
#: else it resolves by name must already be there.
_SERVER_CREATES = {"DataAcquisitionSystem", "Equipment", "SignalInterface"}

#: The channel kinds the API accepts; anything else is a 422.
CHANNEL_KINDS = ("value", "status", "alarm", "uncertainty")

_TAGGED_ONLY = ("channel.tag",)
_TAGLESS_ONLY = ("channel.equipment_name", "channel.signal_interface_name")


@dataclass(frozen=True)
class SensorRequest:
    """One channel's worth of points, addressed to the endpoint that fits it."""

    group: int
    endpoint: str
    payload: dict


@dataclass(frozen=True)
class SensorBuildResult:
    requests: tuple[SensorRequest, ...]
    errors: tuple[BuildError, ...]
    warnings: tuple[str, ...]

    @property
    def ok(self) -> bool:
        return not self.errors

    def counts(self) -> dict[str, int]:
        return {
            "channels": len(self.requests),
            "points": sum(len(r.payload["values"]) for r in self.requests),
        }


def build_sensor(
    spec: MappingSpec,
    block: SheetBlock,
    catalogue: Catalogue,
    lookup: LookupFn,
    tz: zoneinfo.ZoneInfo,
    column_formats: dict[int, str | None],
) -> SensorBuildResult:
    """Build one request per measurement group, or explain why not."""
    errors: list[BuildError] = []
    warnings: list[str] = []

    timestamps = _timestamps(spec, block, catalogue, tz, column_formats, errors)
    groups = groups_of(spec, catalogue)
    if not groups:
        errors.append(BuildError("No column holds a reading — map one to 'Reading'."))
    if errors or timestamps is None:
        return SensorBuildResult((), tuple(errors), tuple(warnings))

    cache: dict[str, set[str]] = {}
    by_id: dict[str, dict[int, str]] = {}
    requests: list[SensorRequest] = []
    for group in groups:
        identity = {
            key: _bound_name(
                spec,
                catalogue,
                lookup,
                by_id,
                key,
                _one_value(spec, block, catalogue, group, key, errors),
            )
            for key in catalogue.identity_keys + ("channel.channel_kind", "channel.parent_tag")
        }
        endpoint = _endpoint(catalogue, group, identity, errors)
        _check_names(catalogue, group, identity, lookup, cache, errors, warnings)
        kind = identity.get("channel.channel_kind") or "value"
        if kind not in CHANNEL_KINDS:
            errors.append(
                BuildError(
                    f"Group {group} calls its channel kind {kind!r}; the import "
                    f"accepts {', '.join(CHANNEL_KINDS)}."
                )
            )
        if endpoint is None:
            continue
        values = _points(spec, block, catalogue, group, timestamps)
        if not values:
            continue  # nothing was reported on this channel
        requests.append(
            SensorRequest(group, endpoint, _payload(endpoint, identity, kind, values))
        )

    if errors:
        return SensorBuildResult((), tuple(dict.fromkeys(errors)), tuple(warnings))
    return SensorBuildResult(tuple(requests), (), tuple(dict.fromkeys(warnings)))


def _payload(endpoint: str, identity: dict, kind: str, values: list[dict]) -> dict:
    """The request body, carrying only the fields its endpoint accepts."""
    payload = {
        "das_name": identity["channel.das_name"],
        "parameter_name": identity["channel.parameter_name"],
        "unit_name": identity["channel.unit_name"],
        "strict": False,  # the page says up front what will be created
        "values": values,
    }
    if endpoint == TAGGED:
        payload["tag"] = identity["channel.tag"]
        payload["channel_kind"] = kind
        if identity.get("channel.parent_tag"):
            payload["parent_tag"] = identity["channel.parent_tag"]
    else:
        payload["equipment_name"] = identity["channel.equipment_name"]
        payload["signal_interface_name"] = identity["channel.signal_interface_name"]
    return payload


def _endpoint(catalogue: Catalogue, group: int, identity: dict, errors: list[BuildError]) -> str | None:
    """Which shape names this group's channel — exactly one of the two."""
    tagged = [k for k in _TAGGED_ONLY if identity.get(k)]
    tagless = [k for k in _TAGLESS_ONLY if identity.get(k)]
    if tagged and tagless:
        errors.append(
            BuildError(
                f"Group {group} names its channel by "
                f"{_names(catalogue, tagged)} and by {_names(catalogue, tagless)} — "
                "a channel is named one way or the other, never both."
            )
        )
        return None
    if tagged:
        return TAGGED
    if len(tagless) == len(_TAGLESS_ONLY):
        return TAGLESS
    if tagless:
        missing = [k for k in _TAGLESS_ONLY if not identity.get(k)]
        errors.append(
            BuildError(
                f"Group {group} names {_names(catalogue, tagless)} but not "
                f"{_names(catalogue, missing)}, so its channel cannot be found."
            )
        )
        return None
    errors.append(
        BuildError(
            f"Group {group} does not name its channel: give it a "
            f"{_names(catalogue, _TAGGED_ONLY)}, or an "
            f"{_names(catalogue, _TAGLESS_ONLY)}."
        )
    )
    return None


def _check_names(
    catalogue: Catalogue,
    group: int,
    identity: dict,
    lookup: LookupFn,
    cache: dict[str, set[str]],
    errors: list[BuildError],
    warnings: list[str],
) -> None:
    """Say now what the server would say — 422, or 'created for you'."""
    for key, text in identity.items():
        if not text:
            continue
        field = catalogue.by_key(key)
        if not field.fk_table or field.emits != "name":
            continue
        table = field.fk_table
        if table not in cache:
            name_key = label_key(table)
            cache[table] = {
                str(row[name_key]).casefold() for row in lookup(table) if row.get(name_key)
            }
        if str(text).casefold() in cache[table]:
            continue
        if table in _SERVER_CREATES:
            warnings.append(
                f"Group {group}: no {table} called '{text}' — it will be created."
            )
        else:
            errors.append(
                BuildError(
                    f"Group {group}: '{text}' is not a {table} on record. Sensor "
                    f"ingest refuses an unknown {field.label.lower()} rather than "
                    "inventing one — add it first."
                )
            )


def _timestamps(
    spec: MappingSpec,
    block: SheetBlock,
    catalogue: Catalogue,
    tz: zoneinfo.ZoneInfo,
    column_formats: dict[int, str | None],
    errors: list[BuildError],
) -> pd.Series | None:
    """Every row's instant in UTC — the one thing every point needs."""
    values = row_series(spec, block, catalogue, "point.timestamp")
    if values is None:
        errors.append(BuildError("No column holds the timestamp of each reading."))
        return None
    mapped = next((m for m in spec.mapped() if m.field == "point.timestamp"), None)
    column = mapped.column if mapped else None
    fmt = None if column is None or column in block.datetime_columns else column_formats.get(column)
    if column is not None and column not in block.datetime_columns and fmt is None:
        errors.append(BuildError("No date format chosen for the timestamp column."))
        return None
    parsed = parse_values(values, fmt)
    utc = to_utc(parsed.wall_clock, tz)
    gaps = dst_gaps(parsed.wall_clock, utc)
    if gaps:
        quoted = ", ".join(f"row {row} ({text})" for row, text in gaps[:3])
        errors.append(
            BuildError(
                f"{len(gaps)} time(s) do not exist, or happen twice, in {tz.key} — "
                f"the clocks changed: {quoted}{'…' if len(gaps) > 3 else ''}."
            )
        )
        return None
    return utc


def _points(
    spec: MappingSpec,
    block: SheetBlock,
    catalogue: Catalogue,
    group: int,
    timestamps: pd.Series,
) -> list[dict]:
    """One group's readings, skipping rows where the channel reported nothing."""
    readings = group_series(spec, block, catalogue, catalogue.value_key, group)
    quality = group_series(spec, block, catalogue, "point.quality_code", group)
    points = []
    for row in block.data.index:
        moment = timestamps.loc[row]
        value = readings.loc[row] if readings is not None else None
        if pd.isna(moment) or not _present(value):
            continue
        try:
            reading = float(value)
        except (TypeError, ValueError):
            continue
        flag = quality.loc[row] if quality is not None else None
        points.append(
            {
                "timestamp": moment.isoformat(),
                "value": reading,
                "quality_code": int(flag) if _present(flag) else None,
            }
        )
    return points


def _one_value(
    spec: MappingSpec,
    block: SheetBlock,
    catalogue: Catalogue,
    group: int,
    key: str,
    errors: list[BuildError],
) -> str | None:
    """A group's single value for one identity field.

    A channel's identity is one thing per group, so a column feeding it must
    hold one value throughout — several is several channels, which one request
    cannot say.
    """
    values = group_series(spec, block, catalogue, key, group)
    if values is None:
        return None
    distinct = sorted({str(v).strip() for v in values if _present(v)})
    if not distinct:
        return None
    if len(distinct) > 1:
        shown = ", ".join(repr(d) for d in distinct[:3])
        errors.append(
            BuildError(
                f"'{catalogue.by_key(key).label}' varies inside group {group} "
                f"({shown}{'…' if len(distinct) > 3 else ''}) — that is "
                "several channels, so give each its own group."
            )
        )
        return None
    return distinct[0]


def _bound_name(
    spec: MappingSpec,
    catalogue: Catalogue,
    lookup: LookupFn,
    by_id: dict[str, dict[int, str]],
    key: str,
    text: str | None,
) -> str | None:
    """The name of the entity a text was bound to, when the user bound one.

    Sensor ingest resolves by name, so a binding made in a column's panel is
    honoured by sending the chosen row's name instead of the sheet's word for it.
    """
    if not text:
        return text
    entity_id = binding_for(spec, key, text)
    table = catalogue.by_key(key).fk_table
    if entity_id is None or table is None:
        return text
    if table not in by_id:
        name_key, pk = label_key(table), load_table(table).pk_field
        by_id[table] = {row[pk]: str(row.get(name_key)) for row in lookup(table) if pk in row}
    return by_id[table].get(entity_id, text)


def _names(catalogue: Catalogue, keys) -> str:
    parts = [catalogue.by_key(k).label for k in keys]
    return " and ".join(parts) if len(parts) <= 2 else ", ".join(parts)


def _present(value) -> bool:
    if value is None:
        return False
    try:
        if pd.isna(value):
            return False
    except (TypeError, ValueError):
        pass
    return bool(str(value).strip())
