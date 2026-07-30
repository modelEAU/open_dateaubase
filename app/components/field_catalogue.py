"""The mappable-field catalogue, derived from the ingest payload schemas.

The catalogue is the vocabulary the user describes their columns with. It is
*derived*, not hand-maintained: every field the lab ingest payloads accept is
walked from the pydantic models, so a field added to a payload schema appears
here without a UI edit. What the schemas cannot say for themselves comes from
two places:

- the **YAML schema dictionary** — column description (help), foreign-key
  target and the exact ``table.column`` reference, looked up by name;
- a small **presentation map** in this module — the plain-language label and
  the activity group, the two things that are genuinely presentation.

**Scope is inferred from the field, never chosen.** Which payload model owns a
field decides what its value attaches to: the batch (``LabIngestRequest`` →
file), the sample (``SampleCreateRequest`` → row) or the measurement
(``LabMeasurementItem`` → measurement). Catalogue keys are namespaced
(``sample.replicate`` vs ``measurement.replicate``) because the same payload
name at two scopes is two different fields.

Pure: no Streamlit, no database.
"""

from __future__ import annotations

import datetime as dt
import re
import types
import typing
from dataclasses import dataclass, field as dataclass_field
from functools import lru_cache

from pydantic import BaseModel

from open_dateaubase.ingestion_schemas import (
    LabIngestRequest,
    LabMeasurementItem,
    SampleCreateRequest,
)
from app.components.schema_registry import load_table

#: The five activity groups, in render order.
GROUPS = (
    "When & where",
    "The sample",
    "The measurement",
    "Who & how",
    "The batch",
)

_FALLBACK_GROUP = {
    "batch": "The batch",
    "sample": "The sample",
    "measurement": "The measurement",
}


@dataclass(frozen=True)
class FieldMeta:
    """One mappable field — everything the UI may say about it."""

    key: str  # "{namespace}.{payload field}", e.g. "sample.sample_datetime_start"
    scope: str  # "file" | "row" | "measurement" — inferred, never editable
    value_type: str  # "integer" | "number" | "text" | "datetime"
    fk_table: str | None  # lookup table an id field references, if any
    required: bool
    label: str  # plain language
    help: str  # the YAML column description
    ref: str  # "Table.Column" for traceability
    group: str  # one of GROUPS


@dataclass(frozen=True)
class Catalogue:
    fields: tuple[FieldMeta, ...]

    def by_key(self, key: str) -> FieldMeta:
        for f in self.fields:
            if f.key == key:
                return f
        raise KeyError(f"no such catalogue field: {key}")

    def in_group(self, group: str) -> tuple[FieldMeta, ...]:
        return tuple(f for f in self.fields if f.group == group)

    def option_labels(self) -> dict[str, str]:
        """Display option → key for pickers, prefixed by activity group."""
        out: dict[str, str] = {}
        for f in self.fields:
            label = f"{f.group} · {f.label}"
            if label in out:  # never silently collapse two fields into one option
                label = f"{label} [{f.key}]"
            out[label] = f.key
        return out


@dataclass(frozen=True)
class CatalogueSource:
    """One payload model the catalogue walks.

    ``table`` is the YAML dictionary table the model's fields bind to by name;
    ``field_tables`` overrides it per field for models whose fields span
    several tables; ``exclude`` lists page-managed fields the user never maps.
    """

    model: type[BaseModel]
    namespace: str
    scope: str
    table: str | None
    field_tables: dict[str, str] = dataclass_field(default_factory=dict)
    exclude: frozenset[str] = frozenset()


_MEASUREMENT_TABLES = {
    "parameter_id": "AnalysisSeries",
    "sampling_point_id": "AnalysisSeries",
    "unit_id": "AnalysisSeries",
    "laboratory_id": "LabAnalysis",
    "value": "Value",
    "analyst_person_id": "LabAnalysis",
    "procedure_id": "LabAnalysis",
    "analysis_datetime": "LabAnalysis",
    "replicate": "LabAnalysis",
    "quality_code_id": "LabAnalysis",
    "notes": "LabAnalysis",
}

_SOURCES = (
    CatalogueSource(
        model=LabIngestRequest,
        namespace="batch",
        scope="file",
        table="LabExperiment",
        # the page owns the experiment id, the panel link and the list itself
        exclude=frozenset({"experiment_id", "measurements", "lab_panel_id"}),
    ),
    CatalogueSource(
        model=SampleCreateRequest,
        namespace="sample",
        scope="row",
        table="Sample",
    ),
    CatalogueSource(
        model=LabMeasurementItem,
        namespace="measurement",
        scope="measurement",
        table=None,
        field_tables=_MEASUREMENT_TABLES,
        # the builder resolves the sample and composes the series name; the
        # value shape is scalar-only until the vector slice
        exclude=frozenset({"sample_id", "series_name", "value_kind_id"}),
    ),
)

#: The only presentation the schemas cannot provide: plain-language label and
#: activity group, per catalogue key. A field absent from this map still
#: appears, with a humanized label and its namespace's fallback group.
_PRESENTATION: dict[str, tuple[str, str]] = {
    "batch.name": ("Experiment name", "The batch"),
    "batch.experiment_datetime": ("Experiment date/time", "The batch"),
    "batch.campaign_id": ("Campaign", "The batch"),
    "batch.description": ("Batch notes", "The batch"),
    "batch.created_by_person_id": ("Recorded by", "The batch"),
    "sample.sample_datetime_start": ("Sampling start", "When & where"),
    "sample.sample_datetime_end": ("Sampling end", "When & where"),
    "sample.sampling_point_id": ("Sampling location", "When & where"),
    "sample.sample_kind_id": ("Sample kind", "The sample"),
    "sample.sample_material_kind_id": ("Sample material", "The sample"),
    "sample.sample_collection_kind_id": ("Collection method", "The sample"),
    "sample.sample_equipment_id": ("Sampling equipment", "The sample"),
    "sample.sampled_by_person_id": ("Collected by", "The sample"),
    "sample.replicate": ("Field replicate", "The sample"),
    "sample.campaign_id": ("Sample campaign", "The sample"),
    "sample.description": ("Sample notes", "The sample"),
    "measurement.parameter_id": ("Parameter", "The measurement"),
    "measurement.value": ("Value", "The measurement"),
    "measurement.unit_id": ("Unit", "The measurement"),
    "measurement.quality_code_id": ("Quality flag", "The measurement"),
    "measurement.analysis_datetime": ("Analysis date/time", "The measurement"),
    "measurement.replicate": ("Analytical replicate", "The measurement"),
    "measurement.notes": ("Analysis notes", "The measurement"),
    "measurement.sampling_point_id": ("Location (per measurement)", "The measurement"),
    "measurement.laboratory_id": ("Laboratory", "Who & how"),
    "measurement.analyst_person_id": ("Analyst", "Who & how"),
    "measurement.procedure_id": ("Procedure", "Who & how"),
}

#: Required only conditionally in the payload (a new experiment needs them),
#: but unconditionally required from the user's point of view.
_REQUIRED_OVERRIDES = {"batch.name", "batch.experiment_datetime"}


def _value_type(annotation) -> str:
    if typing.get_origin(annotation) in (typing.Union, types.UnionType):
        args = [a for a in typing.get_args(annotation) if a is not type(None)]
        annotation = args[0] if args else str
    if annotation is dt.datetime:
        return "datetime"
    if annotation is int:
        return "integer"
    if annotation is float:
        return "number"
    return "text"


def _humanize(name: str) -> str:
    """``favourite_colour`` → ``Favourite colour``; ``unit_id`` → ``Unit``."""
    return re.sub(r"_id$", "", name).replace("_", " ").capitalize()


def _column(table: str, field_name: str):
    """The YAML dictionary's column for a payload field, or None.

    Compared with underscores stripped: the dictionary's snake-casing splits
    ``SampleDateTimeStart`` as ``sample_date_time_start`` while the payload
    says ``sample_datetime_start`` — the same column either way.
    """
    try:
        meta = load_table(table)
    except (FileNotFoundError, KeyError):
        return None
    want = field_name.replace("_", "")
    return next((c for c in meta.columns if c.field.replace("_", "") == want), None)


def build_catalogue(sources=_SOURCES) -> Catalogue:
    """Walk the payload models and assemble the catalogue.

    Fields come out grouped by activity, in ``GROUPS`` order.
    """
    fields: list[FieldMeta] = []
    for src in sources:
        for name, model_field in src.model.model_fields.items():
            if name in src.exclude:
                continue
            key = f"{src.namespace}.{name}"
            table = src.field_tables.get(name, src.table)
            col = _column(table, name) if table else None
            label, group = _PRESENTATION.get(
                key, (_humanize(name), _FALLBACK_GROUP[src.namespace])
            )
            fields.append(
                FieldMeta(
                    key=key,
                    scope=src.scope,
                    value_type=_value_type(model_field.annotation),
                    fk_table=col.fk_table if col else None,
                    required=model_field.is_required() or key in _REQUIRED_OVERRIDES,
                    label=label,
                    help=col.description if col else "",
                    ref=f"{table}.{col.name}" if col else f"{src.model.__name__}.{name}",
                    group=group,
                )
            )
    order = {group: i for i, group in enumerate(GROUPS)}
    fields.sort(key=lambda f: order[f.group])  # stable: declaration order within a group
    return Catalogue(tuple(fields))


@lru_cache(maxsize=1)
def catalogue() -> Catalogue:
    """The process-wide catalogue, built once."""
    return build_catalogue()
