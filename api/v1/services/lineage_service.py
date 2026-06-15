"""Service wrapping open_dateaubase.lineage and meteaudata_bridge.

Provides HTTP-friendly error handling around the low-level lineage functions.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pyodbc
from fastapi import HTTPException

from open_dateaubase.lineage import (
    get_full_lineage_tree,
    get_lineage_backward,
    get_lineage_forward,
    get_processing_step_detail,
    get_traits_for_stream,
)
from open_dateaubase.meteaudata_bridge import record_processing

from ..repositories import channel_repository, ingestion_repository


def forward_lineage(conn: pyodbc.Connection, channel_id: int) -> list[dict]:
    return get_lineage_forward(channel_id, conn)


def backward_lineage(conn: pyodbc.Connection, channel_id: int) -> list[dict]:
    return get_lineage_backward(channel_id, conn)


def full_lineage_tree(conn: pyodbc.Connection, channel_id: int) -> dict:
    return get_full_lineage_tree(channel_id, conn)


def _resolve_node(conn: pyodbc.Connection, stream_id: int, root_id: int) -> dict | None:
    """Resolve a Stream_ID into a display- and plot-ready node dict.

    Routes Channel vs AnalysisSeries by trying the channel resolver first: a lab
    series Stream_ID is absent from the Channel table, so a None result means it
    is an AnalysisSeries. Keeps the original id under the key the Explorer expects
    per kind (``channel_id`` / ``analysis_series_id``) so the node doubles as the
    meta dict stashed when the stream is added to the plot.
    """
    ch = channel_repository.get_channel_by_id(conn, stream_id)
    traits = get_traits_for_stream(stream_id, conn)
    if ch is not None:
        is_derived = ch.get("produced_by_step_id") is not None
        param = ch.get("parameter_name")
        equip = ch.get("equipment_identifier")
        tag = ch.get("tag_name")
        label = f"{param or tag or 'Channel'}" + (f" ({equip})" if equip else "")
        return {
            "stream_id": stream_id,
            "kind": "channel",
            "label": label,
            "parameter_name": param,
            "unit_name": ch.get("unit_name"),
            "value_kind_id": ch.get("value_kind_id"),
            "equipment_identifier": equip,
            "sampling_point_label": None,
            "campaign_name": None,
            "provenance_kind_name": ch.get("data_provenance_kind_name"),
            "traits": traits,
            "is_derived": is_derived,
            "is_root": stream_id == root_id,
            "channel_id": stream_id,
            "analysis_series_id": None,
        }

    series = ingestion_repository.get_analysis_series_by_id(conn, stream_id)
    if series is not None:
        param = series.get("parameter_name")
        loc = series.get("sampling_point_label")
        return {
            "stream_id": stream_id,
            "kind": "series",
            "label": f"{param or series.get('name') or 'Lab series'} @ {loc or '?'}",
            "parameter_name": param,
            "unit_name": series.get("unit_name"),
            "value_kind_id": series.get("value_kind_id"),
            "equipment_identifier": None,
            "sampling_point_label": loc,
            "campaign_name": series.get("campaign_name"),
            "provenance_kind_name": "Laboratory",
            "traits": traits,
            "is_derived": False,
            "is_root": stream_id == root_id,
            "channel_id": None,
            "analysis_series_id": stream_id,
        }

    return None


def resolved_provenance(conn: pyodbc.Connection, stream_id: int) -> dict:
    """Return a fully-resolved provenance graph rooted at ``stream_id``.

    Composes the raw lineage DAG (``get_full_lineage_tree``) with per-node label
    resolution and per-step detail so the frontend needs a single round trip and
    no N+1 lookups. Returns ``{root_id, nodes, ancestors, descendants}``.
    """
    tree = get_full_lineage_tree(stream_id, conn)

    stream_ids: set[int] = {stream_id}
    step_ids: set[int] = set()
    for edge in tree.get("parents", []):
        stream_ids.add(edge["channel_id"])
        stream_ids.add(edge["child_channel_id"])
        step_ids.add(edge["processing_step_id"])
    for edge in tree.get("children", []):
        stream_ids.add(edge["channel_id"])
        stream_ids.add(edge["parent_channel_id"])
        step_ids.add(edge["processing_step_id"])

    nodes = []
    for sid in sorted(stream_ids):
        node = _resolve_node(conn, sid, stream_id)
        if node is not None:
            nodes.append(node)

    ancestor_step_ids = {e["processing_step_id"] for e in tree.get("parents", [])}
    descendant_step_ids = {e["processing_step_id"] for e in tree.get("children", [])}

    ancestors = []
    for sid in sorted(ancestor_step_ids):
        detail = get_processing_step_detail(sid, conn)
        if detail is not None:
            ancestors.append(detail)

    descendants = []
    for sid in sorted(descendant_step_ids):
        detail = get_processing_step_detail(sid, conn)
        if detail is not None:
            descendants.append(detail)

    return {
        "root_id": stream_id,
        "nodes": nodes,
        "ancestors": ancestors,
        "descendants": descendants,
    }


def persist_processing(
    conn: pyodbc.Connection,
    *,
    source_metadata_ids: list[int],
    method_name: str,
    method_version: str | None,
    operation_kind_id: int,
    method_parameters: dict,
    executed_at: datetime | None,
    executed_by_person_id: int | None,
) -> int:
    """Insert ProcessingStep + ProcessingLineage input edges.

    Returns the ProcessingStep_ID.
    The caller is responsible for creating the output Channel with
    ProducedByStep_ID pointing to the returned step_id.
    Raises HTTPException(500) on unexpected DB error.
    """
    effective_executed_at = executed_at or datetime.now(tz=timezone.utc)
    try:
        return record_processing(
            source_metadata_ids=source_metadata_ids,
            method_name=method_name,
            method_version=method_version,
            operation_kind_id=operation_kind_id,
            method_parameters=method_parameters,
            executed_at=effective_executed_at,
            executed_by_person_id=executed_by_person_id,
            conn=conn,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to record processing lineage: {exc}",
        ) from exc
