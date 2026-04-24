"""SignalInterfaceType vocab CRUD endpoints.

Covers:
  GET  /signal-interface-types              — list all
  POST /signal-interface-types              — create
  PUT  /signal-interface-types/{id}         — update
  DELETE /signal-interface-types/{id}       — delete
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from api.database import get_db
from ..repositories import lookup_repository
from ..schemas.signal_interface import (
    SignalInterfaceTypeIn,
    SignalInterfaceTypeLookupOut,
)

router = APIRouter()


@router.get("", response_model=list[SignalInterfaceTypeLookupOut])
def list_signal_interface_types(conn=Depends(get_db)):
    return lookup_repository.get_signal_interface_types(conn)


@router.post("", response_model=SignalInterfaceTypeLookupOut, status_code=201)
def create_signal_interface_type(body: SignalInterfaceTypeIn, conn=Depends(get_db)):
    return lookup_repository.insert_signal_interface_type(
        conn, body.name, body.description
    )


@router.put("/{signal_interface_type_id}", response_model=SignalInterfaceTypeLookupOut)
def update_signal_interface_type(
    signal_interface_type_id: int, body: SignalInterfaceTypeIn, conn=Depends(get_db)
):
    updated = lookup_repository.update_signal_interface_type(
        conn, signal_interface_type_id, body.name, body.description
    )
    if updated is None:
        raise HTTPException(
            status_code=404,
            detail=f"SignalInterfaceType {signal_interface_type_id} not found.",
        )
    return updated


@router.delete("/{signal_interface_type_id}", status_code=204)
def delete_signal_interface_type(signal_interface_type_id: int, conn=Depends(get_db)):
    deleted = lookup_repository.delete_signal_interface_type(
        conn, signal_interface_type_id
    )
    if not deleted:
        raise HTTPException(
            status_code=404,
            detail=f"SignalInterfaceType {signal_interface_type_id} not found.",
        )
