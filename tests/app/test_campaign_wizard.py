"""Campaign wizard branch coverage using streamlit.testing.v1.AppTest.

Each test exercises one distinct branch of the wizard's validation or
execution logic. All API calls are mocked so no live server is needed.

Coverage map:
  Step 0  — name required; new-person name required
  Step 1  — new-site name required
  Step 2  — new sampling-location name required
  Step 3  — at least one DAS required; new-DAS name required
  Step 4  — at least one item required; new-equipment identifier required;
             new-tag string required
  Execute — all-new happy path; all-existing happy path;
             API error on site/campaign/DAS/equipment surfaces as friendly msg
"""
from __future__ import annotations

from contextlib import ExitStack
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from streamlit.testing.v1 import AppTest

# ---------------------------------------------------------------------------
# Harness & module paths
# ---------------------------------------------------------------------------

HARNESS = str(Path(__file__).parent / "wizard_harness.py")
MOD = "app.components.campaign_wizard"

# ---------------------------------------------------------------------------
# Stable fixture data (mirrors what the DB would return)
# ---------------------------------------------------------------------------

_CAMPAIGN_TYPES = [{"campaign_kind_id": 1, "name": "Monitoring"}]
_SITES = [{"site_id": 1, "name": "Site A"}]
_SITE_TYPES = [{"id": 1, "name": "WWTP"}]
_EQUIPMENT = [{"equipment_id": 1, "identifier": "Sensor-001"}]
_EQUIPMENT_MODELS = [{"model_id": 1, "manufacturer": "Acme", "model_name": "X100"}]
_PARAMETERS = [{"parameter_id": 1, "parameter_name": "pH"}]
_PROCESSING_DEGREES = [{"operation_kind_id": 1, "name": "Unprocessed"}]
_DAS = [{"das_id": 1, "name": "DAS-001"}]
# Vocab rename: SignalInterface replaces the old SignalPort concept.
_SIGNAL_INTERFACES = [
    {"signal_interface_id": 1, "name": "AI_01", "das_name": "DAS-001"}
]
_PERSONS = [{"person_id": 1, "label": "Alice Smith"}]
_SITE_SLS = [{"id": 1, "name": "Point A"}]
_PROCESS_UNITS: list[dict] = []

# ---------------------------------------------------------------------------
# Patch helpers
# ---------------------------------------------------------------------------

_LOOKUP_SPECS = [
    (f"{MOD}.list_campaign_kinds", _CAMPAIGN_TYPES),
    (f"{MOD}.list_sites_lookup", _SITES),
    (f"{MOD}.list_site_kinds", _SITE_TYPES),
    (f"{MOD}.list_equipment_lookup", _EQUIPMENT),
    (f"{MOD}.list_equipment_models_lookup", _EQUIPMENT_MODELS),
    (f"{MOD}.list_parameters_lookup", _PARAMETERS),
    (f"{MOD}.list_operation_kinds_lookup", _PROCESSING_DEGREES),
    (f"{MOD}.list_das_lookup", _DAS),
    (f"{MOD}.list_signal_interfaces_lookup", _SIGNAL_INTERFACES),
    (f"{MOD}.list_persons_lookup", _PERSONS),
    (f"{MOD}.list_site_sampling_locations", _SITE_SLS),
    (f"{MOD}.list_process_units_lookup", _PROCESS_UNITS),
]

_MUTATION_SPECS = [
    (f"{MOD}.create_site", {"id": 10}),
    (f"{MOD}.create_sampling_location", {"id": 20}),
    (f"{MOD}.create_person", {"person_id": 50}),
    (f"{MOD}.create_campaign", {"campaign_id": 100}),
    (f"{MOD}.create_das", {"das_id": 5}),
    (f"{MOD}.create_equipment_model", {"model_id": 15}),
    (f"{MOD}.create_equipment", {"equipment_id": 30}),
    (f"{MOD}.create_signal_interface", {"signal_interface_id": 40}),
    (f"{MOD}.create_channel", {"channel_id": 60}),
    (f"{MOD}.create_campaign_deployment", {"deployment_id": 70}),
    (f"{MOD}.create_process_unit", {"id": 80}),
    (f"{MOD}.register_equipment_at_interface", {}),
    (f"{MOD}.deploy_das", {}),
    (f"{MOD}.get_das_conflict", None),
]


@pytest.fixture()
def mocked_lookups():
    """Patch all read-only lookup functions with stable fixture data."""
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
        mocks = {}
        for target, retval in _MUTATION_SPECS:
            name = target.split(".")[-1]
            mocks[name] = stack.enter_context(patch(target, return_value=retval))
        yield mocks


def _at(step: int, extra: dict | None = None) -> AppTest:
    """Build an AppTest pre-seeded at the given wizard step."""
    at = AppTest.from_file(HARNESS, default_timeout=10)
    at.session_state["wizard_step"] = step
    if extra:
        for k, v in extra.items():
            at.session_state[k] = v
    return at


def _errors(at: AppTest) -> list[str]:
    return [e.value for e in at.error]


# ---------------------------------------------------------------------------
# Shared state builders
# ---------------------------------------------------------------------------


def _all_new_state() -> dict:
    """Complete wizard state for the 'all new entities' happy path."""
    return {
        # Step 0
        "wiz_s0_name": "Test Campaign",
        "wiz_s0_campaign_type": "Monitoring",
        "wiz_s0_description": "",
        "wiz_s0_start_date": None,
        "wiz_s0_end_date": None,
        "wiz_s0_person_mode": "Create new",
        "wiz_s0_person_first_name": "Alice",
        "wiz_s0_person_last_name": "Smith",
        "wiz_s0_person_email": "alice@example.com",
        "wiz_s0_person_role": "Engineer",
        "wiz_s0_person_organization": "Lab",
        "wiz_s0_person_phone": "",
        # Step 1
        "wiz_s1_mode": "Create new",
        "wiz_s1_site_name": "New Site",
        "wiz_s1_site_type_label": "WWTP",
        "wiz_s1_site_description": "",
        "wiz_site_lat_input": 45.5017,
        "wiz_site_lng_input": -73.5673,
        "wiz_site_city_input": "Montreal",
        "wiz_site_province_input": "QC",
        "wiz_site_country_input": "Canada",
        # Step 2
        "wiz_sl_ids": [0],
        "wiz_sl_next_id": 1,
        "wiz_sl_0_mode": "New",
        "wiz_sl_0_name_store": "Point A",
        "wiz_sl_0_description_store": "",
        # Step 3
        "wiz_das_ids": [0],
        "wiz_das_next_id": 1,
        "wiz_das_0_mode": "New",
        "wiz_das_0_das_name": "DAS-New",
        # Step 4
        "wiz_eq_ids": [0],
        "wiz_eq_next_id": 1,
        "wiz_tag_ids": [],
        "wiz_tag_next_id": 0,
        "wiz_eq_0_das_wiz_id": 0,
        "wiz_eq_0_mode": "New",
        "wiz_eq_0_model_mode": "Select existing",
        "wiz_eq_0_model": "Acme \u2013 X100",  # _model_label output
        "wiz_eq_0_identifier": "Sensor-New",
        "wiz_eq_0_serial": "",
        "wiz_eq_0_sp_id": 0,  # wizard SL 0 → DB ID 20 (from mock)
    }


def _all_existing_state() -> dict:
    """Complete wizard state for the 'all existing entities' happy path."""
    return {
        # Step 0
        "wiz_s0_name": "Test Campaign",
        "wiz_s0_campaign_type": "Monitoring",
        "wiz_s0_description": "",
        "wiz_s0_start_date": None,
        "wiz_s0_end_date": None,
        "wiz_s0_person_mode": "Select existing",
        "wiz_s0_responsible_person": "Alice Smith",
        # Step 1
        "wiz_s1_mode": "Use existing",
        "wiz_s1_site_label": "Site A",
        # Step 2 — link to existing sampling location
        "wiz_sl_ids": [0],
        "wiz_sl_next_id": 1,
        "wiz_sl_0_mode": "Existing",
        "wiz_sl_0_existing_label_store": "Point A",
        # Step 3
        "wiz_das_ids": [0],
        "wiz_das_next_id": 1,
        "wiz_das_0_mode": "Existing",
        "wiz_das_0_das_label": "DAS-001",
        # Step 4
        "wiz_eq_ids": [0],
        "wiz_eq_next_id": 1,
        "wiz_tag_ids": [],
        "wiz_tag_next_id": 0,
        "wiz_eq_0_das_wiz_id": 0,
        "wiz_eq_0_mode": "Existing",
        "wiz_eq_0_eq_label": "Sensor-001",
        "wiz_eq_0_sp_id": 0,  # wizard SL 0 → DB ID 1 (from _SITE_SLS via list_site_sampling_locations)
    }


# ---------------------------------------------------------------------------
# Step 0: Campaign basics
# ---------------------------------------------------------------------------


class TestStep0Validation:
    def test_name_required(self, mocked_lookups):
        at = _at(0)
        at.run()
        at.button(key="wiz_next_0").click().run()
        assert any("Campaign name is required" in e for e in _errors(at))

    def test_new_person_name_required(self, mocked_lookups):
        at = _at(0, {"wiz_s0_person_mode": "Create new"})
        at.run()
        at.text_input(key="wiz_s0_name").set_value("Test Campaign")
        at.button(key="wiz_next_0").click().run()
        assert any("first name or last name is required" in e for e in _errors(at))

    def test_valid_existing_person_advances(self, mocked_lookups):
        at = _at(0)
        at.run()
        at.text_input(key="wiz_s0_name").set_value("Test Campaign")
        # selectbox defaults to first option ("Alice Smith") — person valid
        at.button(key="wiz_next_0").click().run()
        assert not _errors(at)
        assert at.session_state.wizard_step == 1


# ---------------------------------------------------------------------------
# Step 1: Site
# ---------------------------------------------------------------------------


class TestStep1Validation:
    def test_new_site_name_required(self, mocked_lookups):
        with patch(f"{MOD}.render_location_picker", return_value={}):
            at = _at(1, {"wiz_s1_mode": "Create new"})
            at.run()
            # Leave site name empty, click Next
            at.button(key="wiz_next_1").click().run()
        assert any("Site name is required" in e for e in _errors(at))

    def test_existing_site_advances(self, mocked_lookups):
        at = _at(1, {"wiz_s1_mode": "Use existing"})
        at.run()
        at.button(key="wiz_next_1").click().run()
        assert not _errors(at)
        assert at.session_state.wizard_step == 2


# ---------------------------------------------------------------------------
# Step 2: Sampling Locations
# ---------------------------------------------------------------------------


class TestStep2Validation:
    def test_new_sl_name_required(self, mocked_lookups):
        # Add a new SL entry but leave name empty
        at = _at(
            2,
            {
                "wiz_s1_mode": "Use existing",
                "wiz_sl_ids": [0],
                "wiz_sl_next_id": 1,
                "wiz_sl_0_mode": "New",
                "wiz_sl_0_name": "",
                "wiz_sl_0_name_store": "",
            },
        )
        at.run()
        at.button(key="wiz_next_2").click().run()
        assert any("name is required" in e for e in _errors(at))

    def test_zero_sls_advances(self, mocked_lookups):
        # Step 2 allows skipping (0 SLs is valid at this step)
        at = _at(2, {"wiz_s1_mode": "Use existing", "wiz_sl_ids": [], "wiz_sl_next_id": 0})
        at.run()
        at.button(key="wiz_next_2").click().run()
        assert not _errors(at)
        assert at.session_state.wizard_step == 3


# ---------------------------------------------------------------------------
# Step 3: Data Acquisition Systems
# ---------------------------------------------------------------------------


class TestStep3Validation:
    def test_no_das_required(self, mocked_lookups):
        at = _at(3, {"wiz_das_ids": [], "wiz_das_next_id": 0})
        at.run()
        at.button(key="wiz_next_3").click().run()
        assert any("at least one Data Acquisition System" in e for e in _errors(at))

    def test_new_das_name_required(self, mocked_lookups):
        at = _at(
            3,
            {
                "wiz_das_ids": [0],
                "wiz_das_next_id": 1,
                "wiz_das_0_mode": "New",
                "wiz_das_0_das_name": "",
            },
        )
        at.run()
        at.button(key="wiz_next_3").click().run()
        assert any("name is required" in e for e in _errors(at))

    def test_existing_das_advances(self, mocked_lookups):
        at = _at(
            3,
            {
                "wiz_das_ids": [0],
                "wiz_das_next_id": 1,
                "wiz_das_0_mode": "Existing",
                "wiz_das_0_das_label": "DAS-001",
            },
        )
        at.run()
        at.button(key="wiz_next_3").click().run()
        assert not _errors(at)
        assert at.session_state.wizard_step == 4

    def test_das_move_strands_equipment_warning(self, mocked_lookups):
        """F1: picking a DAS active at another site lists the equipment it strands."""
        conflict = {
            "conflicting_site_name": "Plant A",
            "conflicting_site_id": 2,
            "conflicting_campaign_name": "Old Study",
        }
        stranded = [
            {
                "equipment_id": 5,
                "equipment_identifier": "pH-01",
                "sampling_point_name": "Influent",
                "current_site_name": "Plant A",
            }
        ]
        at = _at(
            3,
            {
                "wiz_s1_mode": "Use existing",
                "wiz_s1_site_label": "Site A",
                "wiz_das_ids": [0],
                "wiz_das_next_id": 1,
                "wiz_das_0_mode": "Existing",
                "wiz_das_0_das_label": "DAS-001",
            },
        )
        with patch(f"{MOD}.get_das_conflict", return_value=conflict), patch(
            f"{MOD}.get_das_move_conflicts", return_value=stranded
        ) as m:
            at.run()
        warnings = " ".join(w.value for w in at.warning)
        assert "would strand 1 wired equipment" in warnings
        assert "pH-01" in warnings
        # queried with the resolved DAS id and the new (campaign) site id
        assert m.call_args.args == (1, 1)


# ---------------------------------------------------------------------------
# Step 4: Equipment & Tags
# ---------------------------------------------------------------------------


class TestStep4Validation:
    def _base_state(self, extra: dict | None = None) -> dict:
        state = {
            "wiz_s1_mode": "Use existing",
            "wiz_sl_ids": [0],
            "wiz_sl_next_id": 1,
            "wiz_sl_0_mode": "New",
            "wiz_sl_0_name_store": "Point A",
            "wiz_das_ids": [0],
            "wiz_das_next_id": 1,
            "wiz_das_0_mode": "Existing",
            "wiz_das_0_das_label": "DAS-001",
            "wiz_eq_ids": [],
            "wiz_eq_next_id": 0,
            "wiz_tag_ids": [],
            "wiz_tag_next_id": 0,
        }
        if extra:
            state.update(extra)
        return state

    def test_no_items_required(self, mocked_lookups):
        at = _at(4, self._base_state())
        at.run()
        at.button(key="wiz_next_4").click().run()
        assert any("at least one piece of equipment" in e for e in _errors(at))

    def test_new_equipment_identifier_required(self, mocked_lookups):
        at = _at(
            4,
            self._base_state(
                {
                    "wiz_eq_ids": [0],
                    "wiz_eq_next_id": 1,
                    "wiz_eq_0_das_wiz_id": 0,
                    "wiz_eq_0_mode": "New",
                    "wiz_eq_0_model_mode": "Select existing",
                    "wiz_eq_0_model": "Acme \u2013 X100",
                    "wiz_eq_0_identifier": "",  # missing
                    "wiz_eq_0_sp_id": 0,
                }
            ),
        )
        at.run()
        at.button(key="wiz_next_4").click().run()
        assert any("identifier is required" in e for e in _errors(at))

    def test_new_equipment_model_name_required_when_creating_model(self, mocked_lookups):
        at = _at(
            4,
            self._base_state(
                {
                    "wiz_eq_ids": [0],
                    "wiz_eq_next_id": 1,
                    "wiz_eq_0_das_wiz_id": 0,
                    "wiz_eq_0_mode": "New",
                    "wiz_eq_0_model_mode": "Create new",
                    "wiz_eq_0_model_name_new": "",  # missing
                    "wiz_eq_0_identifier": "Sensor-X",
                    "wiz_eq_0_sp_id": 0,
                }
            ),
        )
        at.run()
        at.button(key="wiz_next_4").click().run()
        assert any("model name is required" in e for e in _errors(at))

    def test_new_standalone_tag_string_required(self, mocked_lookups):
        at = _at(
            4,
            self._base_state(
                {
                    "wiz_tag_ids": [0],
                    "wiz_tag_next_id": 1,
                    "wiz_tag_0_das_wiz_id": 0,
                    "wiz_tag_0_eq_wiz_id": None,
                    "wiz_tag_0_mode": "New",
                    "wiz_tag_0_tag": "",  # missing
                    "wiz_tag_0_port_type": "Analog",
                    "wiz_tag_0_parameter": "pH",
                    "wiz_tag_0_value_type": "Scalar",
                    "wiz_tag_0_sp_id": 0,
                }
            ),
        )
        at.run()
        at.button(key="wiz_next_4").click().run()
        assert any("tag / interface name is required" in e for e in _errors(at))


# ---------------------------------------------------------------------------
# Step 5: Execute — happy paths
# ---------------------------------------------------------------------------


class TestExecuteHappyPath:
    def test_all_new_entities_calls_correct_apis(self, mock_apis):
        at = _at(5, _all_new_state())
        at.run()
        at.button(key="wiz_next_5").click().run()

        assert not _errors(at), f"Unexpected errors: {_errors(at)}"
        mock_apis["create_site"].assert_called_once()
        mock_apis["create_person"].assert_called_once()
        mock_apis["create_campaign"].assert_called_once()
        mock_apis["create_das"].assert_called_once()
        mock_apis["create_equipment"].assert_called_once()
        mock_apis["create_campaign_deployment"].assert_called_once()

    def test_all_new_campaign_payload(self, mock_apis):
        at = _at(5, _all_new_state())
        at.run()
        at.button(key="wiz_next_5").click().run()

        payload = mock_apis["create_campaign"].call_args[0][0]
        assert payload["name"] == "Test Campaign"
        assert payload["campaign_kind_id"] == 1  # "Monitoring" → id 1
        assert payload["responsible_person_id"] == 50  # from create_person mock

    def test_all_existing_skips_creation_apis(self, mock_apis):
        at = _at(5, _all_existing_state())
        at.run()
        at.button(key="wiz_next_5").click().run()

        assert not _errors(at), f"Unexpected errors: {_errors(at)}"
        mock_apis["create_site"].assert_not_called()
        mock_apis["create_person"].assert_not_called()
        mock_apis["create_das"].assert_not_called()
        mock_apis["create_equipment"].assert_not_called()
        # Campaign itself is always created
        mock_apis["create_campaign"].assert_called_once()
        mock_apis["create_campaign_deployment"].assert_called_once()

    def test_all_existing_uses_resolved_ids(self, mock_apis):
        at = _at(5, _all_existing_state())
        at.run()
        at.button(key="wiz_next_5").click().run()

        payload = mock_apis["create_campaign"].call_args[0][0]
        assert payload["site_id"] == 1  # "Site A" → id 1
        assert payload["responsible_person_id"] == 1  # "Alice Smith" → person_id 1

    def test_new_equipment_new_model_creates_model_first(self, mock_apis):
        state = _all_new_state()
        state["wiz_eq_0_model_mode"] = "Create new"
        state["wiz_eq_0_model_name_new"] = "CustomSensor"
        state["wiz_eq_0_model_manufacturer"] = "Acme"
        at = _at(5, state)
        at.run()
        at.button(key="wiz_next_5").click().run()

        assert not _errors(at), f"Unexpected errors: {_errors(at)}"
        mock_apis["create_equipment_model"].assert_called_once()
        model_payload = mock_apis["create_equipment_model"].call_args[0][0]
        assert model_payload["equipment_model"] == "CustomSensor"
        mock_apis["create_equipment"].assert_called_once()
        eq_payload = mock_apis["create_equipment"].call_args[0][0]
        assert eq_payload["model_id"] == 15  # from create_equipment_model mock


# ---------------------------------------------------------------------------
# Regression tests for BUG-3 and BUG-4 (campaign wizard state propagation)
# ---------------------------------------------------------------------------


class TestStatePropagationBugs:
    """Streamlit drops widget keys once their step is no longer rendered.
    The wizard must read snapshot-stable `_store` keys to survive across
    step transitions. These tests simulate the post-transition state by
    deleting widget keys while keeping only the store keys."""

    def test_bug_3_site_id_resolved_from_store_key_only(self, mock_apis):
        """BUG-3: campaign payload was missing site_id because
        wiz_s1_site_label is dropped after step 1. Fix: read
        wiz_s1_site_label_store first."""
        state = _all_existing_state()
        # Simulate Streamlit dropping the widget key after step 1 transitions.
        del state["wiz_s1_site_label"]
        state["wiz_s1_site_label_store"] = "Site A"

        at = _at(5, state)
        at.run()
        at.button(key="wiz_next_5").click().run()

        assert not _errors(at), f"BUG-3 regression: {_errors(at)}"
        payload = mock_apis["create_campaign"].call_args[0][0]
        assert payload["site_id"] == 1  # "Site A" resolves to id=1

    def test_bug_4_sl_mode_resolved_from_store_key_only(self, mock_apis):
        """BUG-4: step 3 reported 'No sampling locations selected' because
        wiz_sl_{id}_mode was dropped after step 2. Fix: read
        wiz_sl_{id}_mode_store first."""
        state = _all_existing_state()
        # Simulate Streamlit dropping the mode widget key after step 2.
        del state["wiz_sl_0_mode"]
        state["wiz_sl_0_mode_store"] = "Existing"

        at = _at(5, state)
        at.run()
        at.button(key="wiz_next_5").click().run()

        assert not _errors(at), f"BUG-4 regression: {_errors(at)}"
        # The SL must still be linked to the equipment deployment.
        mock_apis["create_campaign_deployment"].assert_called_once()


# ---------------------------------------------------------------------------
# Step 5: Execute — API error handling
# ---------------------------------------------------------------------------


class TestExecuteAPIErrors:
    def test_site_creation_failure_shows_friendly_error(self, mock_apis):
        from app.api_client import APIError

        mock_apis["create_site"].side_effect = APIError(500, "DB constraint violation")
        at = _at(5, _all_new_state())
        at.run()
        at.button(key="wiz_next_5").click().run()

        assert any("Site creation failed" in e for e in _errors(at))
        mock_apis["create_campaign"].assert_not_called()

    def test_campaign_creation_failure_shows_friendly_error(self, mock_apis):
        from app.api_client import APIError

        mock_apis["create_campaign"].side_effect = APIError(422, "Name already taken")
        at = _at(5, _all_new_state())
        at.run()
        at.button(key="wiz_next_5").click().run()

        assert any("Campaign creation failed" in e for e in _errors(at))

    def test_das_creation_failure_shows_friendly_error(self, mock_apis):
        from app.api_client import APIError

        mock_apis["create_das"].side_effect = APIError(500, "Internal error")
        at = _at(5, _all_new_state())
        at.run()
        at.button(key="wiz_next_5").click().run()

        assert any("DAS-New" in e or "Data Acquisition System" in e for e in _errors(at))
        mock_apis["create_equipment"].assert_not_called()

    def test_equipment_creation_failure_shows_friendly_error(self, mock_apis):
        from app.api_client import APIError

        mock_apis["create_equipment"].side_effect = APIError(409, "Duplicate identifier")
        at = _at(5, _all_new_state())
        at.run()
        at.button(key="wiz_next_5").click().run()

        assert any("Sensor-New" in e or "Equipment" in e for e in _errors(at))
