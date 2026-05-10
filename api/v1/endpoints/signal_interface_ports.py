"""SignalInterfacePort CRUD endpoints.

Covers:
  GET  /signal-interface-ports                     — paginated list with filters
  GET  /signal-interface-ports/{id}                — get single port
  POST /signal-interface-ports                     — create port
  PATCH /signal-interface-ports/{id}               — partial update
  DELETE /signal-interface-ports/{id}              — delete
"""

from __future__ import annotations

import pyodbc
from fastapi import APIRouter, Depends, HTTPException, Query

from api.database import get_db
from ..repositories import signal_interface_repository
from ..schemas.common import PaginatedResponse
from ..schemas.signal_interface import (
    SignalInterfacePortIn,
    SignalInterfacePortOut,
    SignalInterfacePortPatchRequest,
    SignalInterfacePortProvisionIn,
)

router = APIRouter()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _row_to_port_out(row: dict) -> SignalInterfacePortOut:
    return SignalInterfacePortOut(
        signal_interface_port_id=row["SignalInterfacePort_ID"],
        port_identifier=row["PortIdentifier"],
        description=row["Description"],
        is_active=bool(row["IsActive"]),
        signal_interface_id=row["SignalInterface_ID"],
        signal_interface_name=row["signal_interface_name"],
    )


# ---------------------------------------------------------------------------
# SignalInterfacePort CRUD
# ---------------------------------------------------------------------------


@router.get("", response_model=PaginatedResponse[SignalInterfacePortOut])
def list_signal_interface_ports(
    signal_interface_id: int | None = Query(
        default=None, description="Filter by SignalInterface_ID"
    ),
    is_active: bool | None = Query(default=None, description="Filter by IsActive flag"),
    page: int = Query(default=1, ge=1, description="1-based page number"),
    page_size: int = Query(default=100, ge=1, le=1000, description="Rows per page"),
    conn=Depends(get_db),
):
    """Return a paginated list of SignalInterfacePorts with optional filters."""
    items, total = signal_interface_repository.list_signal_interface_ports(
        conn,
        signal_interface_id=signal_interface_id,
        is_active=is_active,
        page=page,
        page_size=page_size,
    )
    return PaginatedResponse(
        items=[_row_to_port_out(r) for r in items],
        total=total,
        page=page,
        page_size=page_size,
        has_next=(page * page_size) < total,
    )


@router.get("/{signal_interface_port_id}", response_model=SignalInterfacePortOut)
def get_signal_interface_port(signal_interface_port_id: int, conn=Depends(get_db)):
    """Return a SignalInterfacePort by ID."""
    row = signal_interface_repository.get_signal_interface_port_by_id(
        conn, signal_interface_port_id
    )
    if row is None:
        raise HTTPException(
            status_code=404,
            detail=f"SignalInterfacePort {signal_interface_port_id} not found.",
        )
    return _row_to_port_out(row)


@router.post("/provision", response_model=SignalInterfacePortOut, status_code=201)
def provision_signal_interface_port(body: SignalInterfacePortProvisionIn, conn=Depends(get_db)):
    """Find or create a SignalInterfacePort by signal_interface_id + port_identifier.

    Idempotent: returns the existing port if one matches (signal_interface_id, port_identifier).
    """
    port_id, _ = signal_interface_repository.find_or_create_signal_interface_port(
        conn, body.signal_interface_id, body.port_identifier
    )
    row = signal_interface_repository.get_signal_interface_port_by_id(conn, port_id)
    return _row_to_port_out(row)  # type: ignore[arg-type]


@router.post("", response_model=SignalInterfacePortOut, status_code=201)
def create_signal_interface_port(body: SignalInterfacePortIn, conn=Depends(get_db)):
    """Create a new SignalInterfacePort.

    Returns 409 when a port with the same identifier already exists in the same interface.
    """
    try:
        new_id = signal_interface_repository.create_signal_interface_port(
            conn,
            signal_interface_id=body.signal_interface_id,
            port_identifier=body.port_identifier,
            description=body.description,
        )
    except pyodbc.IntegrityError as exc:
        raise HTTPException(
            status_code=409,
            detail=(
                f"A SignalInterfacePort with identifier {body.port_identifier!r} already exists "
                f"in SignalInterface {body.signal_interface_id}. Database error: {exc}"
            ),
        ) from exc

    row = signal_interface_repository.get_signal_interface_port_by_id(conn, new_id)
    return _row_to_port_out(row)  # type: ignore[arg-type]


@router.patch("/{signal_interface_port_id}", response_model=SignalInterfacePortOut)
def patch_signal_interface_port(
    signal_interface_port_id: int,
    body: SignalInterfacePortPatchRequest,
    conn=Depends(get_db),
):
    """Partially update a SignalInterfacePort (description, is_active).

    Only fields explicitly set in the request body are written.
    """
    if (
        signal_interface_repository.get_signal_interface_port_by_id(
            conn, signal_interface_port_id
        )
        is None
    ):
        raise HTTPException(
            status_code=404,
            detail=f"SignalInterfacePort {signal_interface_port_id} not found.",
        )

    row = signal_interface_repository.patch_signal_interface_port(
        conn,
        signal_interface_port_id,
        body.model_dump(exclude_none=True),
    )
    return _row_to_port_out(row)  # type: ignore[arg-type]


@router.delete("/{signal_interface_port_id}", status_code=204)
def delete_signal_interface_port(signal_interface_port_id: int, conn=Depends(get_db)):
    """Delete a SignalInterfacePort by ID."""
    if not signal_interface_repository.delete_signal_interface_port(
        conn, signal_interface_port_id
    ):
        raise HTTPException(
            status_code=404,
            detail=f"SignalInterfacePort {signal_interface_port_id} not found.",
        )
