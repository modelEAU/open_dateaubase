"""Pydantic schemas for equipment move endpoints."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Rewire (close current wiring + open new)
# ---------------------------------------------------------------------------


class EquipmentRewireRequest(BaseModel):
    """Replace the signal interface behind a piece of equipment."""

    signal_interface_id: int
    signal_interface_port_id: int | None = None
    valid_from: datetime
    note: str | None = None


class EquipmentRewireResponse(BaseModel):
    equipment_id: int
    new_wiring_history_id: int
    closed_wiring_history_id: int | None
    annotation_ids: list[int]


# ---------------------------------------------------------------------------
# Register interface (first wiring row — no active row must exist)
# ---------------------------------------------------------------------------


class EquipmentRegisterInterfaceRequest(BaseModel):
    """Open a first EquipmentWiringHistory row for equipment."""

    signal_interface_id: int
    signal_interface_port_id: int | None = None
    valid_from: datetime | None = None
    note: str | None = None


class EquipmentRegisterInterfaceResponse(BaseModel):
    equipment_id: int
    wiring_history_id: int


# ---------------------------------------------------------------------------
# Relocate (close current location + open new + auto-annotate)
# ---------------------------------------------------------------------------


class EquipmentRelocateRequest(BaseModel):
    """Move equipment to a new sampling point."""

    sampling_point_id: int
    valid_from: datetime
    notes: str | None = None
    campaign_id: int | None = None


class EquipmentRelocateResponse(BaseModel):
    equipment_id: int
    new_location_history_id: int
    closed_location_history_id: int | None
    annotation_ids: list[int]


# ---------------------------------------------------------------------------
# Point-in-time queries
# ---------------------------------------------------------------------------


class WiringAtTimeResponse(BaseModel):
    equipment_id: int
    at_time: datetime
    history_id: int | None
    signal_interface_id: int | None
    signal_interface_port_id: int | None
    signal_interface_name: str | None
    equipment_identifier: str | None
    valid_from: datetime | None
    valid_to: datetime | None


class LocationAtTimeResponse(BaseModel):
    equipment_id: int
    at_time: datetime
    history_id: int | None
    sampling_point_id: int | None
    sampling_point_name: str | None
    valid_from: datetime | None
    valid_to: datetime | None


class ActiveCampaignDeploymentResponse(BaseModel):
    """The still-running campaign whose deployment placed this equipment, if any
    (consistency audit F13). ``campaign_id`` is None when no open campaign row
    exists — reconfiguring then closes no running campaign's deployment."""

    equipment_id: int
    campaign_id: int | None
    campaign_name: str | None
    equipment_location_history_id: int | None
    sampling_point_id: int | None
    sampling_point_name: str | None
