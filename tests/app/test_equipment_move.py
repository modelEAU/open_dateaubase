"""AppTest regression tests for the Equipment Move wizard.

Covers:
  Relocate (Change Location tab):
    - Campaign required: no campaigns → advance blocked
    - Same-destination guard: fires when dest == current SP
    - Happy path confirm: relocate_equipment called with campaign_id in payload
    - API error on confirm: error stored in summary session state
    - Equipment event: both relocate_equipment and create_equipment_event called

  Rewire (Change Wiring tab):
    - Same-wiring guard: fires when dest SI/port == current wiring
    - Happy path confirm: rewire_equipment called with correct payload (port omitted when None)
    - API error on confirm: error stored in summary session state
    - Equipment event: both rewire_equipment and create_equipment_event called
"""

from __future__ import annotations

from contextlib import ExitStack
from datetime import date, time
from pathlib import Path
from unittest.mock import patch

import pytest
from streamlit.testing.v1 import AppTest

PAGE = str(Path(__file__).parent.parent.parent / "app" / "pages" / "equipment_move.py")
# Patch the SOURCE module so re-imports inside AppTest pick up the mocks.
# equipment_move.py uses `from app.api_client import …`; patching the local
# binding (app.pages.equipment_move.*) gets overwritten on each AppTest re-run
# because the page re-executes the import at the top of the file.
MOD = "app.api_client"

# ---------------------------------------------------------------------------
# Stable fixture data
# ---------------------------------------------------------------------------

_EQUIPMENT = [{"equipment_id": 1, "identifier": "Sensor-001"}]
_SAMPLING_POINTS = [
    {"sampling_point_id": 1, "label": "SP-Alpha"},
    {"sampling_point_id": 2, "label": "SP-Beta"},
]
_CAMPAIGNS = [{"campaign_id": 10, "name": "Summer 2024"}]
_SIGNAL_INTERFACES = [{"signal_interface_id": 5, "name": "AI_01", "das_name": "DAS-001"}]
_EVENT_KINDS = [{"event_type_id": 1, "event_type_name": "Maintenance"}]
# Current location: SP-Alpha (id=1); used to trigger same-destination guard
_LOCATION_RESPONSE = {
    "equipment_id": 1,
    "history_id": 1,
    "sampling_point_id": 1,
    "sampling_point_name": "SP-Alpha",
    "valid_from": "2024-01-01T00:00:00",
    "valid_to": None,
}
# Current wiring: SI=5 / port=None; used to trigger same-wiring guard
_WIRING_RESPONSE = {
    "equipment_id": 1,
    "history_id": 1,
    "signal_interface_id": 5,
    "signal_interface_port_id": None,
    "signal_interface_name": "AI_01",
    "valid_from": "2024-01-01T00:00:00",
    "valid_to": None,
}

# ---------------------------------------------------------------------------
# Patch specs — ALL lookups called on every page render (both tabs run always)
# ---------------------------------------------------------------------------

_LOOKUP_SPECS = [
    (f"{MOD}.list_equipment_lookup", _EQUIPMENT),
    (f"{MOD}.list_equipment_event_kinds", _EVENT_KINDS),
    (f"{MOD}.list_sampling_points_lookup", _SAMPLING_POINTS),
    (f"{MOD}.list_campaigns_lookup", _CAMPAIGNS),
    (f"{MOD}.list_signal_interfaces_lookup", _SIGNAL_INTERFACES),
    (f"{MOD}.list_signal_interface_ports", []),
    (f"{MOD}.get_location_at_time", _LOCATION_RESPONSE),
    (f"{MOD}.get_wiring_at_time", _WIRING_RESPONSE),
]


@pytest.fixture()
def mocked_lookups():
    """Patch all read-only lookup functions; no mutation mocks."""
    with ExitStack() as stack:
        for target, retval in _LOOKUP_SPECS:
            stack.enter_context(patch(target, return_value=retval))
        yield


@pytest.fixture()
def mock_apis():
    """Patch lookup AND mutation functions. Yields dict of mutation mocks."""
    with ExitStack() as stack:
        for target, retval in _LOOKUP_SPECS:
            stack.enter_context(patch(target, return_value=retval))
        mocks = {
            "relocate_equipment": stack.enter_context(
                patch(f"{MOD}.relocate_equipment", return_value={})
            ),
            "rewire_equipment": stack.enter_context(
                patch(f"{MOD}.rewire_equipment", return_value={})
            ),
            "create_equipment_event": stack.enter_context(
                patch(f"{MOD}.create_equipment_event", return_value={})
            ),
        }
        yield mocks


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _at_relocate(step: int, extra: dict | None = None) -> AppTest:
    """AppTest pre-seeded at the given relocate wizard step."""
    at = AppTest.from_file(PAGE, default_timeout=10)
    at.session_state["mv_step"] = step
    if extra:
        for k, v in extra.items():
            at.session_state[k] = v
    return at


def _at_rewire(step: int, extra: dict | None = None) -> AppTest:
    """AppTest pre-seeded at the given rewire wizard step."""
    at = AppTest.from_file(PAGE, default_timeout=10)
    at.session_state["mw_step"] = step
    if extra:
        for k, v in extra.items():
            at.session_state[k] = v
    return at


def _errors(at: AppTest) -> list[str]:
    return [e.value for e in at.error]


def _warnings(at: AppTest) -> list[str]:
    return [w.value for w in at.warning]


# ---------------------------------------------------------------------------
# Relocate — step 2 validation
# ---------------------------------------------------------------------------


class TestRelocateStep2Validation:
    def test_no_campaigns_shows_warning_and_blocks_advance(self):
        """When the campaigns lookup returns nothing, the wizard shows a
        warning and on_next returns 'Select a campaign.'."""
        with ExitStack() as stack:
            for target, retval in _LOOKUP_SPECS:
                rv = [] if "list_campaigns_lookup" in target else retval
                stack.enter_context(patch(target, return_value=rv))

            at = _at_relocate(
                2, {"mv_equipment_id": 1, "mv_equipment_label": "Sensor-001"}
            )
            at.run()
            assert any("campaigns" in w.lower() for w in _warnings(at))
            at.button(key="mv_next_2").click().run()
            assert any("campaign" in e.lower() for e in _errors(at))

    def test_same_destination_blocks_advance(self, mocked_lookups):
        """Selecting the same sampling point as the current location must be
        rejected.  _LOCATION_RESPONSE returns SP-Alpha (id=1); the SP
        selectbox defaults to index 0 which is also SP-Alpha."""
        at = _at_relocate(
            2, {"mv_equipment_id": 1, "mv_equipment_label": "Sensor-001"}
        )
        at.run()
        at.button(key="mv_next_2").click().run()
        assert any("same as the current sampling point" in e for e in _errors(at))


# ---------------------------------------------------------------------------
# Relocate — step 4 confirm
# ---------------------------------------------------------------------------


class TestRelocateConfirm:
    _STATE: dict = {
        "mv_equipment_id": 1,
        "mv_equipment_label": "Sensor-001",
        "mv_dest_sp_id": 2,
        "mv_dest_sp_label": "SP-Beta",
        "mv_campaign_id": 10,
        "mv_campaign_label": "Summer 2024",
        "mv_date": date(2024, 6, 15),
        "mv_time": time(10, 0),
        "mv_notes": "",
        "mv_add_event": False,
    }

    def test_confirm_calls_relocate_with_campaign_id(self, mock_apis):
        at = _at_relocate(4, dict(self._STATE))
        at.run()
        at.button(key="mv_next_4").click().run()

        mock_apis["relocate_equipment"].assert_called_once()
        equipment_id, payload = mock_apis["relocate_equipment"].call_args[0]
        assert equipment_id == 1
        assert payload["sampling_point_id"] == 2
        assert payload["campaign_id"] == 10

    def test_confirm_advances_to_summary(self, mock_apis):
        at = _at_relocate(4, dict(self._STATE))
        at.run()
        at.button(key="mv_next_4").click().run()
        assert at.session_state.mv_step == 5

    def test_api_error_surfaces_in_summary(self, mock_apis):
        from app.api_client import APIError

        mock_apis["relocate_equipment"].side_effect = APIError(500, "DB constraint")
        at = _at_relocate(4, dict(self._STATE))
        at.run()
        at.button(key="mv_next_4").click().run()

        # Step still advances to summary; render_wizard_result calls st.error() for each error
        assert at.session_state.mv_step == 5
        assert any("Move failed" in e for e in _errors(at))

    def test_equipment_event_recorded_alongside_move(self, mock_apis):
        state = {
            **self._STATE,
            "mv_add_event": True,
            "mv_event_type_id": 1,
            "mv_event_type_label": "Maintenance",
            "mv_event_notes": "Post-install check",
            "mv_event_is_instantaneous": False,
        }
        at = _at_relocate(4, state)
        at.run()
        at.button(key="mv_next_4").click().run()

        mock_apis["relocate_equipment"].assert_called_once()
        mock_apis["create_equipment_event"].assert_called_once()
        event_payload = mock_apis["create_equipment_event"].call_args[0][0]
        assert event_payload["equipment_id"] == 1
        assert event_payload["event_type_id"] == 1


# ---------------------------------------------------------------------------
# Rewire — step 2 validation
# ---------------------------------------------------------------------------


class TestRewireStep2Validation:
    def test_same_wiring_blocks_advance(self, mocked_lookups):
        """Selecting the same SI/port as the current wiring must be rejected.
        _WIRING_RESPONSE returns SI=5/port=None; the SI selectbox defaults to
        index 0 (SI=5) and port defaults to 'No port (interface-level only)'."""
        at = _at_rewire(
            2, {"mw_equipment_id": 1, "mw_equipment_label": "Sensor-001"}
        )
        at.run()
        at.button(key="mw_next_2").click().run()
        assert any("same as current wiring" in e for e in _errors(at))


# ---------------------------------------------------------------------------
# Rewire — step 4 confirm
# ---------------------------------------------------------------------------


class TestRewireConfirm:
    _STATE: dict = {
        "mw_equipment_id": 1,
        "mw_equipment_label": "Sensor-001",
        "mw_dest_si_id": 5,
        "mw_dest_si_label": "DAS-001 › AI_01",
        "mw_dest_port_id": None,
        "mw_dest_port_label": "No port (interface-level only)",
        "mw_date": date(2024, 6, 15),
        "mw_time": time(10, 0),
        "mw_notes": "",
        "mw_add_event": False,
    }

    def test_confirm_calls_rewire_with_correct_payload(self, mock_apis):
        at = _at_rewire(4, dict(self._STATE))
        at.run()
        at.button(key="mw_next_4").click().run()

        mock_apis["rewire_equipment"].assert_called_once()
        equipment_id, payload = mock_apis["rewire_equipment"].call_args[0]
        assert equipment_id == 1
        assert payload["signal_interface_id"] == 5
        # port is None → must NOT appear in payload
        assert "signal_interface_port_id" not in payload

    def test_confirm_advances_to_summary(self, mock_apis):
        at = _at_rewire(4, dict(self._STATE))
        at.run()
        at.button(key="mw_next_4").click().run()
        assert at.session_state.mw_step == 5

    def test_api_error_surfaces_in_summary(self, mock_apis):
        from app.api_client import APIError

        mock_apis["rewire_equipment"].side_effect = APIError(422, "Invalid interface")
        at = _at_rewire(4, dict(self._STATE))
        at.run()
        at.button(key="mw_next_4").click().run()

        assert at.session_state.mw_step == 5
        assert any("Rewire failed" in e for e in _errors(at))

    def test_equipment_event_recorded_alongside_rewire(self, mock_apis):
        state = {
            **self._STATE,
            "mw_add_event": True,
            "mw_event_type_id": 1,
            "mw_event_type_label": "Maintenance",
            "mw_event_notes": "",
            "mw_event_is_instantaneous": True,
        }
        at = _at_rewire(4, state)
        at.run()
        at.button(key="mw_next_4").click().run()

        mock_apis["rewire_equipment"].assert_called_once()
        mock_apis["create_equipment_event"].assert_called_once()
        event_payload = mock_apis["create_equipment_event"].call_args[0][0]
        assert event_payload["equipment_id"] == 1
        assert event_payload["is_instantaneous"] is True
