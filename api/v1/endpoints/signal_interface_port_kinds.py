"""SignalInterfacePortKind vocab endpoints.

Covers:
  GET  /signal-interface-port-kinds   — list all (read-only; IDs are seeded)
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from api.database import get_db
from ..repositories import lookup_repository
from ..schemas.signal_interface import SignalInterfacePortKindLookupOut

router = APIRouter()


@router.get("", response_model=list[SignalInterfacePortKindLookupOut])
def list_signal_interface_port_kinds(conn=Depends(get_db)):
    return lookup_repository.get_signal_interface_port_kinds(conn)
