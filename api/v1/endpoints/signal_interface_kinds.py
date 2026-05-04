"""SignalInterfaceKind vocab CRUD endpoints.

Covers:
  GET  /signal-interface-kinds              — list all
  POST /signal-interface-kinds              — create
  PUT  /signal-interface-kinds/{id}         — update
  DELETE /signal-interface-kinds/{id}       — delete
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from api.database import get_db
from ..repositories import lookup_repository
from ..schemas.signal_interface import (
    SignalInterfaceKindIn,
    SignalInterfaceKindLookupOut,
)

router = APIRouter()


@router.get("", response_model=list[SignalInterfaceKindLookupOut])
def list_signal_interface_types(conn=Depends(get_db)):
    return lookup_repository.get_signal_interface_kinds(conn)


@router.post("", response_model=SignalInterfaceKindLookupOut, status_code=201)
def create_signal_interface_type(body: SignalInterfaceKindIn, conn=Depends(get_db)):
    return lookup_repository.insert_signal_interface_kind(
        conn, body.name, body.description
    )


@router.put("/{signal_interface_kind_id}", response_model=SignalInterfaceKindLookupOut)
def update_signal_interface_kind(
    signal_interface_kind_id: int, body: SignalInterfaceKindIn, conn=Depends(get_db)
):
    updated = lookup_repository.update_signal_interface_kind(
        conn, signal_interface_kind_id, body.name, body.description
    )
    if updated is None:
        raise HTTPException(
            status_code=404,
            detail=f"SignalInterfaceKind {signal_interface_kind_id} not found.",
        )
    return updated


@router.delete("/{signal_interface_kind_id}", status_code=204)
def delete_signal_interface_kind(signal_interface_kind_id: int, conn=Depends(get_db)):
    deleted = lookup_repository.delete_signal_interface_kind(
        conn, signal_interface_kind_id
    )
    if not deleted:
        raise HTTPException(
            status_code=404,
            detail=f"SignalInterfaceKind {signal_interface_kind_id} not found.",
        )
