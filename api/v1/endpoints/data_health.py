"""Data-health endpoints — surface the broken-link views (consistency audit F5, F11).

  GET /data-health/unlinked-channels            — raw channels needing wiring (F5)
  GET /data-health/inactive-parent-references   — live wiring on soft-deleted parents (F11)

Both read the reconciling views added in schema 2.1.0; they are reports, not
mutations, so the app can show a "N channels need wiring" banner or confirm
before deactivating a parent that still has live children.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from api.database import get_db
from ..schemas.data_health import (
    InactiveParentReference,
    InactiveParentReferencesResponse,
    UnlinkedChannel,
    UnlinkedChannelsResponse,
)

router = APIRouter()


@router.get("/unlinked-channels", response_model=UnlinkedChannelsResponse)
def unlinked_channels(conn=Depends(get_db)):
    """Raw channels that carry observations but have no active wiring (F5)."""
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT ChannelID, TagName, SignalInterfaceID, SignalInterfaceName,
               ObservationCount, FirstObservation, LastObservation
        FROM [dbo].[vw_UnlinkedChannels]
        ORDER BY ObservationCount DESC
        """
    )
    channels = [
        UnlinkedChannel(
            channel_id=r[0],
            tag_name=r[1],
            signal_interface_id=r[2],
            signal_interface_name=r[3],
            observation_count=r[4],
            first_observation=r[5],
            last_observation=r[6],
        )
        for r in cursor.fetchall()
    ]
    return UnlinkedChannelsResponse(count=len(channels), channels=channels)


@router.get(
    "/inactive-parent-references",
    response_model=InactiveParentReferencesResponse,
)
def inactive_parent_references(
    signal_interface_id: int | None = Query(default=None),
    signal_interface_port_id: int | None = Query(default=None),
    conn=Depends(get_db),
):
    """Active wiring rows still pointing at a soft-deleted interface/port (F11).

    Optionally filter to a single parent — the deactivation flow passes the
    interface/port about to be set inactive to ask "does this still have live
    children?" before committing.
    """
    sql = """
        SELECT ReferenceType, WiringHistoryID, EquipmentID, ParentID, ParentLabel
        FROM [dbo].[vw_InactiveParentReferences]
    """
    clauses, params = [], []
    if signal_interface_id is not None:
        clauses.append("(ReferenceType = N'active-wiring->interface' AND ParentID = ?)")
        params.append(signal_interface_id)
    if signal_interface_port_id is not None:
        clauses.append("(ReferenceType = N'active-wiring->port' AND ParentID = ?)")
        params.append(signal_interface_port_id)
    if clauses:
        sql += " WHERE " + " OR ".join(clauses)

    cursor = conn.cursor()
    cursor.execute(sql, *params)
    refs = [
        InactiveParentReference(
            reference_type=r[0],
            wiring_history_id=r[1],
            equipment_id=r[2],
            parent_id=r[3],
            parent_label=r[4],
        )
        for r in cursor.fetchall()
    ]
    return InactiveParentReferencesResponse(count=len(refs), references=refs)
