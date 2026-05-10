"""Pydantic schemas for ControlLoop endpoints."""

from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel

# ---------------------------------------------------------------------------
# ControlLoop
# ---------------------------------------------------------------------------


class ControlLoopCreateRequest(BaseModel):
    name: str
    controller_kind_id: int
    fallback_control_loop_id: int | None = None
    algorithm_reference: str | None = None
    description: str | None = None


class ControlLoopOut(BaseModel):
    control_loop_id: int
    name: str
    controller_kind_id: int
    controller_kind_name: str | None
    fallback_control_loop_id: int | None
    algorithm_reference: str | None
    description: str | None


# ---------------------------------------------------------------------------
# ControlLoopPort
# ---------------------------------------------------------------------------


class ControlLoopPortAddRequest(BaseModel):
    """Associate a Channel with a loop.

    Provide either ``role_id`` (int) or ``role_name`` (string matching a
    ControlLoopPortKind.Name). If both are given, ``role_id`` takes precedence.
    """

    channel_id: int
    role_id: int | None = None
    role_name: str | None = None


class ControlLoopPortOut(BaseModel):
    control_loop_port_id: int
    control_loop_id: int
    channel_id: int
    role_id: int
    role_name: str


class ControlLoopPortsResponse(BaseModel):
    control_loop_id: int
    ports: list[ControlLoopPortOut]


# ---------------------------------------------------------------------------
# ControlLoopApplication
# ---------------------------------------------------------------------------


class ApplicationOpenRequest(BaseModel):
    """Open a new active Application for a loop.

    ``parameters`` should be a JSON string (e.g. ``'{"Kp": 1.2, "Ki": 0.05}'``).
    """

    start_time: datetime
    parameters: str | None = None
    applied_by_person_id: int | None = None
    notes: str | None = None


class RetuneRequest(BaseModel):
    """Close the current active Application and open a new one.

    The active Application's EndTime is set to ``start_time``.
    ``parameters`` should be a JSON string.
    """

    start_time: datetime
    parameters: str | None = None
    applied_by_person_id: int | None = None
    notes: str | None = None


class ControlLoopApplicationOut(BaseModel):
    control_loop_application_id: int
    control_loop_id: int
    start_time: datetime
    end_time: datetime | None
    parameters: str | None
    applied_by_person_id: int | None
    notes: str | None


class RetuneResponse(BaseModel):
    control_loop_id: int
    new_application_id: int
    closed_application_id: int | None


class ApplicationAtTimeResponse(BaseModel):
    control_loop_id: int
    at_time: datetime
    application: ControlLoopApplicationOut | None


# ---------------------------------------------------------------------------
# Fallback chain
# ---------------------------------------------------------------------------


class FallbackChainResponse(BaseModel):
    root_loop_id: int
    chain: list[ControlLoopOut]
