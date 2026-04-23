"""SignalInterface CRUD and traversal endpoints.

Covers:
  GET  /signal-interfaces                     — paginated list with filters
  GET  /signal-interfaces/{id}                — get single interface
  POST /signal-interfaces                     — create interface
  PATCH /signal-interfaces/{id}               — partial update
  DELETE /signal-interfaces/{id}              — delete
  GET  /signal-interfaces/{id}/ports          — list ports under this interface
  GET  /signal-interfaces/{id}/channels       — list channels under this interface
"""

from __future__ import annotations

import pyodbc
from fastapi import APIRouter, Depends, HTTPException, Query

from api.database import get_db
from ..repositories import channel_repository, signal_interface_repository
from ..schemas.common import PaginatedResponse
from ..schemas.signal_interface import (
    DasCreateIn,
    DasOut,
    DasLookupOut,
    DasUpdateIn,
    SignalInterfaceIn,
    SignalInterfaceLookupOut,
    SignalInterfaceOut,
    SignalInterfacePatchRequest,
    SignalInterfacePortCreateIn,
    SignalInterfacePortOut,
    SignalInterfaceProvisionIn,
)

router = APIRouter()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _row_to_signal_interface_out(row: dict) -> SignalInterfaceOut:
    return SignalInterfaceOut(
        signal_interface_id=row["SignalInterface_ID"],
        name=row["Name"],
        make=row["Make"],
        model=row["Model"],
        serial_number=row["SerialNumber"],
        description=row["Description"],
        is_active=bool(row["IsActive"]),
        data_acquisition_system_id=row["DataAcquisitionSystem_ID"],
        das_name=row["das_name"],
        signal_interface_type_id=row["SignalInterfaceType_ID"],
        signal_interface_type_name=row["signal_interface_type_name"],
    )


def _row_to_port_out(row: dict) -> SignalInterfacePortOut:
    return SignalInterfacePortOut(
        signal_interface_port_id=row["SignalInterfacePort_ID"],
        port_identifier=row["PortIdentifier"],
        description=row["Description"],
        is_active=bool(row["IsActive"]),
        signal_interface_id=row["SignalInterface_ID"],
        signal_interface_name=row["signal_interface_name"],
        signal_interface_port_kind_id=row["SignalInterfacePortKind_ID"],
        signal_interface_port_kind_name=row["signal_interface_port_kind_name"],
    )


# ---------------------------------------------------------------------------
# SignalInterface CRUD
# ---------------------------------------------------------------------------


@router.get("", response_model=PaginatedResponse[SignalInterfaceOut])
def list_signal_interfaces(
    das_id: int | None = Query(
        default=None, description="Filter by DataAcquisitionSystem_ID"
    ),
    is_active: bool | None = Query(default=None, description="Filter by IsActive flag"),
    signal_interface_type_id: int | None = Query(
        default=None, description="Filter by SignalInterfaceType_ID"
    ),
    equipment_id: int | None = Query(
        default=None, description="Filter by active Equipment_ID"
    ),
    page: int = Query(default=1, ge=1, description="1-based page number"),
    page_size: int = Query(default=100, ge=1, le=1000, description="Rows per page"),
    conn=Depends(get_db),
):
    """Return a paginated list of SignalInterfaces with optional filters."""
    items, total = signal_interface_repository.list_signal_interfaces(
        conn,
        das_id=das_id,
        is_active=is_active,
        signal_interface_type_id=signal_interface_type_id,
        equipment_id=equipment_id,
        page=page,
        page_size=page_size,
    )
    return PaginatedResponse(
        items=[_row_to_signal_interface_out(r) for r in items],
        total=total,
        page=page,
        page_size=page_size,
        has_next=(page * page_size) < total,
    )


@router.get("/lookup", response_model=list[SignalInterfaceLookupOut])
def list_signal_interfaces_lookup(conn=Depends(get_db)):
    """Return a lightweight ``[{signal_interface_id, name}]`` list for dropdown use."""
    return signal_interface_repository.list_signal_interfaces_lookup(conn)


# ---------------------------------------------------------------------------
# DataAcquisitionSystem CRUD
# ---------------------------------------------------------------------------


@router.get("/das/lookup", response_model=list[DasLookupOut])
def list_das_lookup(conn=Depends(get_db)):
    """Return a lightweight ``[{das_id, name}]`` list for dropdown use."""
    rows = signal_interface_repository.list_das(conn)
    return [DasLookupOut(das_id=r["DataAcquisitionSystem_ID"], name=r["Name"]) for r in rows]


@router.get("/das", response_model=list[DasOut])
def list_das(conn=Depends(get_db)):
    """Return all DataAcquisitionSystem rows ordered by name."""
    rows = signal_interface_repository.list_das(conn)
    return [
        DasOut(das_id=r["DataAcquisitionSystem_ID"], name=r["Name"], description=r["Description"])
        for r in rows
    ]


@router.post("/das", response_model=DasOut, status_code=201)
def create_das(body: DasCreateIn, conn=Depends(get_db)):
    """Create a new DataAcquisitionSystem."""
    try:
        row = signal_interface_repository.insert_das(conn, body.name, body.description)
    except pyodbc.IntegrityError as exc:
        raise HTTPException(
            status_code=409,
            detail=f"A DataAcquisitionSystem named {body.name!r} already exists. Database error: {exc}",
        ) from exc
    return DasOut(**row)


@router.put("/das/{das_id}", response_model=DasOut)
def update_das(das_id: int, body: DasUpdateIn, conn=Depends(get_db)):
    """Update a DataAcquisitionSystem's name and description."""
    row = signal_interface_repository.update_das(conn, das_id, body.name, body.description)
    if row is None:
        raise HTTPException(status_code=404, detail=f"DataAcquisitionSystem {das_id} not found.")
    return DasOut(**row)


@router.delete("/das/{das_id}", status_code=204)
def delete_das(das_id: int, conn=Depends(get_db)):
    """Delete a DataAcquisitionSystem by ID."""
    if not signal_interface_repository.delete_das(conn, das_id):
        raise HTTPException(status_code=404, detail=f"DataAcquisitionSystem {das_id} not found.")


@router.get("/{signal_interface_id}", response_model=SignalInterfaceOut)
def get_signal_interface(signal_interface_id: int, conn=Depends(get_db)):
    """Return a SignalInterface by ID."""
    row = signal_interface_repository.get_signal_interface_by_id(
        conn, signal_interface_id
    )
    if row is None:
        raise HTTPException(
            status_code=404, detail=f"SignalInterface {signal_interface_id} not found."
        )
    return _row_to_signal_interface_out(row)


@router.post("/provision", response_model=SignalInterfaceOut, status_code=201)
def provision_signal_interface(body: SignalInterfaceProvisionIn, conn=Depends(get_db)):
    """Find or create a SignalInterface by das_name + name + type_name.

    Idempotent: returns the existing interface if one matches (das_name, name).
    """
    das_id, _ = signal_interface_repository.find_or_create_das(conn, body.das_name)
    type_id = signal_interface_repository.find_signal_interface_type_by_name(
        conn, body.type_name
    )
    if type_id is None:
        raise HTTPException(
            status_code=422,
            detail=f"SignalInterfaceType {body.type_name!r} not found.",
        )
    si_id, _ = signal_interface_repository.find_or_create_signal_interface(
        conn, das_id=das_id, name=body.name, signal_interface_type_id=type_id
    )
    row = signal_interface_repository.get_signal_interface_by_id(conn, si_id)
    return _row_to_signal_interface_out(row)  # type: ignore[arg-type]


@router.post("", response_model=SignalInterfaceOut, status_code=201)
def create_signal_interface(body: SignalInterfaceIn, conn=Depends(get_db)):
    """Create a new SignalInterface.

    Returns 409 when a unique constraint is violated.
    """
    try:
        new_id = signal_interface_repository.create_signal_interface(
            conn,
            das_id=body.data_acquisition_system_id,
            name=body.name,
            signal_interface_type_id=body.signal_interface_type_id,
            make=body.make,
            model=body.model,
            serial_number=body.serial_number,
            description=body.description,
        )
    except pyodbc.IntegrityError as exc:
        raise HTTPException(
            status_code=409,
            detail=f"A SignalInterface with name {body.name!r} already exists in DAS {body.data_acquisition_system_id}. Database error: {exc}",
        ) from exc

    row = signal_interface_repository.get_signal_interface_by_id(conn, new_id)
    return _row_to_signal_interface_out(row)


@router.patch("/{signal_interface_id}", response_model=SignalInterfaceOut)
def patch_signal_interface(
    signal_interface_id: int, body: SignalInterfacePatchRequest, conn=Depends(get_db)
):
    """Partially update a SignalInterface.

    Only fields explicitly set in the request body are written.
    """
    if (
        signal_interface_repository.get_signal_interface_by_id(
            conn, signal_interface_id
        )
        is None
    ):
        raise HTTPException(
            status_code=404, detail=f"SignalInterface {signal_interface_id} not found."
        )

    row = signal_interface_repository.patch_signal_interface(
        conn,
        signal_interface_id,
        body.model_dump(exclude_none=True),
    )
    return _row_to_signal_interface_out(row)


@router.delete("/{signal_interface_id}", status_code=204)
def delete_signal_interface(signal_interface_id: int, conn=Depends(get_db)):
    """Delete a SignalInterface by ID."""
    if not signal_interface_repository.delete_signal_interface(
        conn, signal_interface_id
    ):
        raise HTTPException(
            status_code=404, detail=f"SignalInterface {signal_interface_id} not found."
        )


# ---------------------------------------------------------------------------
# Traversal: ports under an interface
# ---------------------------------------------------------------------------


@router.get(
    "/{signal_interface_id}/ports",
    response_model=PaginatedResponse[SignalInterfacePortOut],
)
def list_ports_under_interface(
    signal_interface_id: int,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=100, ge=1, le=1000),
    conn=Depends(get_db),
):
    """Return all SignalInterfacePorts belonging to a SignalInterface."""
    items, total = signal_interface_repository.list_signal_interface_ports(
        conn,
        signal_interface_id=signal_interface_id,
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


@router.post(
    "/{signal_interface_id}/ports",
    response_model=SignalInterfacePortOut,
    status_code=201,
)
def create_port_under_interface(
    signal_interface_id: int,
    body: SignalInterfacePortCreateIn,
    conn=Depends(get_db),
):
    """Create a new SignalInterfacePort under the given SignalInterface.

    ``signal_interface_id`` is taken from the path — it must not be included in the
    request body.
    """
    if signal_interface_repository.get_signal_interface_by_id(conn, signal_interface_id) is None:
        raise HTTPException(
            status_code=404, detail=f"SignalInterface {signal_interface_id} not found."
        )
    try:
        new_id = signal_interface_repository.create_signal_interface_port(
            conn,
            signal_interface_id=signal_interface_id,
            port_identifier=body.port_identifier,
            signal_interface_port_kind_id=body.signal_interface_port_kind_id,
            description=body.description,
        )
    except pyodbc.IntegrityError as exc:
        raise HTTPException(
            status_code=409,
            detail=f"Port {body.port_identifier!r} already exists on interface {signal_interface_id}. Database error: {exc}",
        ) from exc
    row = signal_interface_repository.get_signal_interface_port_by_id(conn, new_id)
    return _row_to_port_out(row)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Traversal: channels under an interface
# ---------------------------------------------------------------------------


@router.get("/{signal_interface_id}/channels", response_model=PaginatedResponse[dict])
def list_channels_under_interface(
    signal_interface_id: int,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=100, ge=1, le=1000),
    conn=Depends(get_db),
):
    """Return all Channels linked to a SignalInterface."""
    items, total = channel_repository.list_channels(
        conn,
        signal_interface_id=signal_interface_id,
        page=page,
        page_size=page_size,
    )
    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        has_next=(page * page_size) < total,
    )
