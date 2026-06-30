"""Unit tests for PRD-2 S2: Event/EventKind schemas with exclusive-arc validator.

Red→green: all assertions fail before EventIn is implemented (no validator, no schema).
After S2, each assertion passes without a DB connection.

Coverage:
- Zero arc targets → ValidationError
- Two arc targets → ValidationError
- Each of the 8 arc levels with exactly one target → OK (8 separate assertions)
- EventKindIn / EventKindOut round-trip
- EventOut construction
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from api.v1.schemas.events import EventIn, EventKindIn, EventKindOut, EventOut

_NOW = datetime(2024, 3, 15, 10, 0, 0, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _base(**extra) -> dict:
    """Minimal valid EventIn kwargs with exactly-one arc target supplied via extra."""
    return {"event_kind_id": 1, "start_datetime": _NOW, **extra}


# ---------------------------------------------------------------------------
# Arc-validator: rejection cases
# ---------------------------------------------------------------------------


def test_event_in_zero_targets_raises() -> None:
    """EventIn with no arc target must raise ValidationError."""
    with pytest.raises(ValidationError, match="exactly one target required"):
        EventIn(**_base())


def test_event_in_two_targets_raises() -> None:
    """EventIn with two arc targets must raise ValidationError."""
    with pytest.raises(ValidationError, match="exactly one target required"):
        EventIn(**_base(equipment_id=1, site_id=2))


def test_event_in_eight_targets_raises() -> None:
    """EventIn with all 8 arc targets must raise ValidationError."""
    with pytest.raises(ValidationError, match="exactly one target required"):
        EventIn(
            **_base(
                channel_id=1,
                equipment_id=2,
                signal_interface_id=3,
                data_acquisition_system_id=4,
                sampling_point_id=5,
                process_unit_id=6,
                site_id=7,
                campaign_id=8,
            )
        )


# ---------------------------------------------------------------------------
# Arc-validator: acceptance cases (one per arc level)
# ---------------------------------------------------------------------------


def test_event_in_channel_only_ok() -> None:
    evt = EventIn(**_base(channel_id=5))
    assert evt.channel_id == 5
    assert evt.equipment_id is None


def test_event_in_equipment_only_ok() -> None:
    evt = EventIn(**_base(equipment_id=10))
    assert evt.equipment_id == 10
    assert evt.channel_id is None


def test_event_in_signal_interface_only_ok() -> None:
    evt = EventIn(**_base(signal_interface_id=3))
    assert evt.signal_interface_id == 3


def test_event_in_das_only_ok() -> None:
    evt = EventIn(**_base(data_acquisition_system_id=7))
    assert evt.data_acquisition_system_id == 7


def test_event_in_sampling_point_only_ok() -> None:
    evt = EventIn(**_base(sampling_point_id=2))
    assert evt.sampling_point_id == 2


def test_event_in_process_unit_only_ok() -> None:
    evt = EventIn(**_base(process_unit_id=4))
    assert evt.process_unit_id == 4


def test_event_in_site_only_ok() -> None:
    evt = EventIn(**_base(site_id=1))
    assert evt.site_id == 1


def test_event_in_campaign_only_ok() -> None:
    evt = EventIn(**_base(campaign_id=99))
    assert evt.campaign_id == 99


# ---------------------------------------------------------------------------
# EventKindIn / EventKindOut
# ---------------------------------------------------------------------------


def test_event_kind_in_minimal() -> None:
    k = EventKindIn(name="Calibration")
    assert k.name == "Calibration"
    assert k.description is None


def test_event_kind_in_with_description() -> None:
    k = EventKindIn(name="Cleaning", description="Sensor flushed")
    assert k.description == "Sensor flushed"


def test_event_kind_out_round_trip() -> None:
    k = EventKindOut(event_kind_id=1, name="Calibration", description=None)
    assert k.event_kind_id == 1
    assert k.name == "Calibration"
    assert k.description is None


# ---------------------------------------------------------------------------
# EventOut construction
# ---------------------------------------------------------------------------


def test_event_out_with_equipment_target() -> None:
    evt = EventOut(
        event_id=42,
        event_kind_id=1,
        event_kind_name="Calibration",
        is_instantaneous=False,
        start_datetime=_NOW,
        equipment_id=7,
    )
    assert evt.event_id == 42
    assert evt.equipment_id == 7
    assert evt.channel_id is None
    assert evt.site_id is None


def test_event_out_instantaneous() -> None:
    evt = EventOut(
        event_id=1,
        event_kind_id=14,
        event_kind_name="ControllerCrash",
        is_instantaneous=True,
        start_datetime=_NOW,
        data_acquisition_system_id=3,
    )
    assert evt.is_instantaneous is True
    assert evt.end_datetime is None
