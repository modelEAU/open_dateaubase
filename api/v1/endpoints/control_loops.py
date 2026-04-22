"""ControlLoop lifecycle endpoints.

Covers:
  POST /control-loops                          — create a loop
  GET  /control-loops/{loop_id}                — get loop details
  GET  /control-loops/{loop_id}/ports          — list ports on a loop
  POST /control-loops/{loop_id}/ports          — add a port to a loop
  POST /control-loops/{loop_id}/applications   — open first (or next) Application
  POST /control-loops/{loop_id}/retune         — close active Application, open new one
  GET  /control-loops/{loop_id}/active-application   — current active Application
  GET  /control-loops/{loop_id}/application-at       — point-in-time Application query
  GET  /control-loops/{loop_id}/fallback-chain       — full fallback chain
"""

from __future__ import annotations

from datetime import datetime

import pyodbc
from fastapi import APIRouter, Depends, HTTPException, Query

from api.database import get_db
from ..repositories import control_loop_repository
from ..schemas.control_loop import (
    ApplicationAtTimeResponse,
    ApplicationOpenRequest,
    ControlLoopApplicationOut,
    ControlLoopCreateRequest,
    ControlLoopOut,
    ControlLoopPortAddRequest,
    ControlLoopPortOut,
    ControlLoopPortsResponse,
    FallbackChainResponse,
    RetuneRequest,
    RetuneResponse,
)

router = APIRouter()


def _row_to_loop_out(row: dict) -> ControlLoopOut:
    return ControlLoopOut(
        control_loop_id=row["ControlLoop_ID"],
        name=row["Name"],
        controller_type=row["ControllerType"],
        fallback_control_loop_id=row["FallbackControlLoop_ID"],
        algorithm_reference=row["AlgorithmReference"],
        description=row["Description"],
    )


def _row_to_app_out(row: dict) -> ControlLoopApplicationOut:
    return ControlLoopApplicationOut(
        control_loop_application_id=row["ControlLoopApplication_ID"],
        control_loop_id=row["ControlLoop_ID"],
        start_time=row["StartTime"],
        end_time=row["EndTime"],
        parameters=row["Parameters"],
        applied_by_person_id=row["AppliedByPerson_ID"],
        notes=row["Notes"],
    )


# ---------------------------------------------------------------------------
# ControlLoop CRUD
# ---------------------------------------------------------------------------


@router.get(
    "",
    response_model=list[ControlLoopOut],
)
def list_control_loops(conn=Depends(get_db)):
    """Return all ControlLoops ordered by ID."""
    rows = control_loop_repository.list_control_loops(conn)
    return [_row_to_loop_out(r) for r in rows]


@router.post(
    "",
    response_model=ControlLoopOut,
    status_code=201,
)
def create_control_loop(
    body: ControlLoopCreateRequest,
    conn=Depends(get_db),
):
    """Create a new ControlLoop.

    ``controller_type`` must be one of: PID, PI, P, BangBang, Custom, Manual.
    Set ``algorithm_reference`` (path or repo URL) for Custom controllers.
    Set ``fallback_control_loop_id`` to build fallback chains.
    """
    if body.fallback_control_loop_id is not None:
        if (
            control_loop_repository.get_control_loop(
                conn, body.fallback_control_loop_id
            )
            is None
        ):
            raise HTTPException(
                status_code=422,
                detail=f"FallbackControlLoop_ID {body.fallback_control_loop_id} not found.",
            )

    loop_id = control_loop_repository.create_control_loop(
        conn,
        name=body.name,
        controller_type=body.controller_type,
        fallback_control_loop_id=body.fallback_control_loop_id,
        algorithm_reference=body.algorithm_reference,
        description=body.description,
    )
    row = control_loop_repository.get_control_loop(conn, loop_id)
    return _row_to_loop_out(row)


@router.get(
    "/{loop_id}",
    response_model=ControlLoopOut,
)
def get_control_loop(loop_id: int, conn=Depends(get_db)):
    """Return a ControlLoop by ID."""
    row = control_loop_repository.get_control_loop(conn, loop_id)
    if row is None:
        raise HTTPException(status_code=404, detail=f"ControlLoop {loop_id} not found.")
    return _row_to_loop_out(row)


# ---------------------------------------------------------------------------
# ControlLoopPort
# ---------------------------------------------------------------------------


@router.get(
    "/{loop_id}/ports",
    response_model=ControlLoopPortsResponse,
)
def list_loop_ports(loop_id: int, conn=Depends(get_db)):
    """Return all Channels associated with a ControlLoop."""
    if control_loop_repository.get_control_loop(conn, loop_id) is None:
        raise HTTPException(status_code=404, detail=f"ControlLoop {loop_id} not found.")
    rows = control_loop_repository.get_loop_ports(conn, loop_id)
    return ControlLoopPortsResponse(
        control_loop_id=loop_id,
        ports=[
            ControlLoopPortOut(
                control_loop_port_id=r["ControlLoopPort_ID"],
                control_loop_id=r["ControlLoop_ID"],
                channel_id=r["Channel_ID"],
                role_id=r["ControlLoopPortRole_ID"],
                role_name=r["role_name"],
            )
            for r in rows
        ],
    )


@router.post(
    "/{loop_id}/ports",
    response_model=ControlLoopPortOut,
    status_code=201,
)
def add_port(
    loop_id: int,
    body: ControlLoopPortAddRequest,
    conn=Depends(get_db),
):
    """Associate a Channel with a ControlLoop.

    Provide ``role_id`` (integer PK) or ``role_name`` (case-insensitive name lookup).
    The (ControlLoop_ID, Channel_ID) pair must be unique across all ports of the loop.
    """
    if control_loop_repository.get_control_loop(conn, loop_id) is None:
        raise HTTPException(status_code=404, detail=f"ControlLoop {loop_id} not found.")

    # Resolve role
    role_id = body.role_id
    if role_id is None:
        if body.role_name is None:
            raise HTTPException(
                status_code=422, detail="Provide either role_id or role_name."
            )
        role_id = control_loop_repository.find_role_by_name(conn, body.role_name)
        if role_id is None:
            raise HTTPException(
                status_code=422,
                detail=f"ControlLoopPortRole name {body.role_name!r} not found.",
            )

    try:
        port_id = control_loop_repository.add_loop_port(
            conn,
            loop_id=loop_id,
            channel_id=body.channel_id,
            role_id=role_id,
        )
    except pyodbc.IntegrityError as exc:
        raise HTTPException(
            status_code=409,
            detail=(
                f"Channel {body.channel_id} is already assigned to ControlLoop {loop_id}. "
                f"Database error: {exc}"
            ),
        ) from exc

    # Look up role name for the response
    rows = control_loop_repository.get_loop_ports(conn, loop_id)
    port_row = next(r for r in rows if r["ControlLoopPort_ID"] == port_id)
    return ControlLoopPortOut(
        control_loop_port_id=port_row["ControlLoopPort_ID"],
        control_loop_id=port_row["ControlLoop_ID"],
        channel_id=port_row["Channel_ID"],
        role_id=port_row["ControlLoopPortRole_ID"],
        role_name=port_row["role_name"],
    )


# ---------------------------------------------------------------------------
# ControlLoopApplication
# ---------------------------------------------------------------------------


@router.post(
    "/{loop_id}/applications",
    response_model=ControlLoopApplicationOut,
    status_code=201,
)
def open_application(
    loop_id: int,
    body: ApplicationOpenRequest,
    conn=Depends(get_db),
):
    """Open the first (or next) Application for a ControlLoop.

    Returns 409 if an active Application already exists — use ``/retune`` instead.
    ``parameters`` is a free-form JSON string (e.g. ``'{"Kp": 1.2, "Ki": 0.05}'``).
    """
    if control_loop_repository.get_control_loop(conn, loop_id) is None:
        raise HTTPException(status_code=404, detail=f"ControlLoop {loop_id} not found.")

    try:
        app_id = control_loop_repository.open_application(
            conn,
            loop_id=loop_id,
            start_time=body.start_time,
            parameters=body.parameters,
            applied_by_person_id=body.applied_by_person_id,
            notes=body.notes,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    row = control_loop_repository.get_active_application(conn, loop_id)
    return _row_to_app_out(row)


@router.post(
    "/{loop_id}/retune",
    response_model=RetuneResponse,
    status_code=201,
)
def retune(
    loop_id: int,
    body: RetuneRequest,
    conn=Depends(get_db),
):
    """Record a tuning event: close the active Application and open a new one.

    The active Application's ``EndTime`` is set to ``start_time``.
    If there is no active Application, a new one is opened without closing anything.
    Old tuning rows are preserved with their time windows intact.
    """
    if control_loop_repository.get_control_loop(conn, loop_id) is None:
        raise HTTPException(status_code=404, detail=f"ControlLoop {loop_id} not found.")

    new_id, closed_id = control_loop_repository.retune(
        conn,
        loop_id=loop_id,
        start_time=body.start_time,
        parameters=body.parameters,
        applied_by_person_id=body.applied_by_person_id,
        notes=body.notes,
    )
    return RetuneResponse(
        control_loop_id=loop_id,
        new_application_id=new_id,
        closed_application_id=closed_id,
    )


@router.get(
    "/{loop_id}/active-application",
    response_model=ControlLoopApplicationOut | None,
)
def get_active_application(loop_id: int, conn=Depends(get_db)):
    """Return the currently active Application for a loop, or null if none."""
    if control_loop_repository.get_control_loop(conn, loop_id) is None:
        raise HTTPException(status_code=404, detail=f"ControlLoop {loop_id} not found.")
    row = control_loop_repository.get_active_application(conn, loop_id)
    if row is None:
        return None
    return _row_to_app_out(row)


@router.get(
    "/{loop_id}/application-at",
    response_model=ApplicationAtTimeResponse,
)
def get_application_at(
    loop_id: int,
    at: datetime = Query(..., description="UTC datetime for the point-in-time query"),
    conn=Depends(get_db),
):
    """Return the Application that was active at the given timestamp.

    Returns ``null`` in the ``application`` field when no Application window covers ``at``.
    """
    if control_loop_repository.get_control_loop(conn, loop_id) is None:
        raise HTTPException(status_code=404, detail=f"ControlLoop {loop_id} not found.")
    row = control_loop_repository.get_application_at(conn, loop_id, at)
    return ApplicationAtTimeResponse(
        control_loop_id=loop_id,
        at_time=at,
        application=_row_to_app_out(row) if row is not None else None,
    )


# ---------------------------------------------------------------------------
# Fallback chain
# ---------------------------------------------------------------------------


@router.get(
    "/{loop_id}/fallback-chain",
    response_model=FallbackChainResponse,
)
def get_fallback_chain(loop_id: int, conn=Depends(get_db)):
    """Return the full fallback chain starting from *loop_id*.

    The first element is the loop itself; each subsequent element follows
    ``FallbackControlLoop_ID`` until NULL.

    This lets you traverse ``Outer PID → Inner PID → Manual`` chains in a single call.
    """
    if control_loop_repository.get_control_loop(conn, loop_id) is None:
        raise HTTPException(status_code=404, detail=f"ControlLoop {loop_id} not found.")
    chain = control_loop_repository.get_fallback_chain(conn, loop_id)
    return FallbackChainResponse(
        root_loop_id=loop_id,
        chain=[_row_to_loop_out(r) for r in chain],
    )
