"""Contract tests for SignalInterface, SignalInterfacePort, and SignalInterfaceType endpoints.

Tests run without a live database using dependency_overrides and MagicMock.

Covers:
  - GET    /signal-interface-kinds
  - POST   /signal-interface-kinds
  - PUT    /signal-interface-kinds/{id}
  - DELETE /signal-interface-kinds/{id}
  - GET    /signal-interfaces
  - GET    /signal-interfaces/{id}
  - POST   /signal-interfaces
  - PATCH  /signal-interfaces/{id}
  - DELETE /signal-interfaces/{id}
  - GET    /signal-interfaces/{id}/ports
  - GET    /signal-interfaces/{id}/channels
  - GET    /signal-interface-ports
  - GET    /signal-interface-ports/{id}
  - POST   /signal-interface-ports
  - PATCH  /signal-interface-ports/{id}
  - DELETE /signal-interface-ports/{id}
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from api.database import get_db
from api.main import app

_LOOKUP_REPO = "api.v1.endpoints.signal_interface_kinds.lookup_repository"
_SI_REPO = "api.v1.endpoints.signal_interfaces.signal_interface_repository"
_SIP_REPO = "api.v1.endpoints.signal_interface_ports.signal_interface_repository"
_CHANNEL_REPO = "api.v1.endpoints.signal_interfaces.channel_repository"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_conn():
    conn = MagicMock()
    cursor = MagicMock()
    conn.cursor.return_value = cursor

    def _override():
        yield conn

    app.dependency_overrides[get_db] = _override
    yield conn, cursor
    app.dependency_overrides.clear()


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


# ---------------------------------------------------------------------------
# Sample data
# ---------------------------------------------------------------------------

_TYPE_ROW = {
    "signal_interface_kind_id": 1,
    "name": "PLC",
    "description": "Programmable logic controller",
}

_INTERFACE_ROW = {
    "SignalInterface_ID": 1,
    "DataAcquisitionSystem_ID": 1,
    "SignalInterfaceKind_ID": 1,
    "Name": "PLC-01",
    "Make": "Rockwell",
    "Model": "ControlLogix",
    "SerialNumber": "SN123",
    "Description": "Main PLC",
    "IsActive": 1,
    "signal_interface_kind_name": "PLC",
    "das_name": "DAS-A",
}

_PORT_ROW = {
    "SignalInterfacePort_ID": 1,
    "SignalInterface_ID": 1,
    "PortIdentifier": "6/Ch0",
    "SignalInterfacePortKind_ID": 1,
    "Description": "Analog input 0",
    "IsActive": 1,
    "signal_interface_port_kind_name": "AnalogIn",
    "signal_interface_name": "PLC-01",
}

_CHANNEL_ROW = {
    "channel_id": 1,
    "signal_interface_id": 1,
    "signal_interface_name": "PLC-01",
    "tag_name": "AI_01",
    "signal_interface_port_id": 1,
    "signal_interface_port_identifier": "6/Ch0",
    "parent_channel_id": None,
    "parent_channel_tag_name": None,
    "channel_kind_id": 1,
    "channel_kind_name": "Value",
    "parameter_id": 1,
    "parameter_name": "Temperature",
    "data_provenance_kind_id": 1,
    "data_provenance_kind_name": "SCADA",
    "processing_kind_id": 1,
    "processing_kind_name": "Raw",
    "value_kind_id": 1,
    "value_kind_name": "Scalar",
    "unit_id": 1,
    "unit_name": "degC",
    "equipment_id": None,
    "equipment_identifier": None,
}


# ---------------------------------------------------------------------------
# SignalInterfaceType
# ---------------------------------------------------------------------------


class TestListSignalInterfaceTypes:
    def test_returns_list(self, client, mock_conn):
        with patch(
            f"{_LOOKUP_REPO}.get_signal_interface_kinds", return_value=[_TYPE_ROW]
        ):
            resp = client.get("/api/v1/signal-interface-kinds")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert data[0]["name"] == "PLC"

    def test_empty_list(self, client, mock_conn):
        with patch(f"{_LOOKUP_REPO}.get_signal_interface_kinds", return_value=[]):
            resp = client.get("/api/v1/signal-interface-kinds")
        assert resp.status_code == 200
        assert resp.json() == []


class TestCreateSignalInterfaceType:
    def test_returns_201(self, client, mock_conn):
        with patch(
            f"{_LOOKUP_REPO}.insert_signal_interface_kind", return_value=_TYPE_ROW
        ):
            resp = client.post("/api/v1/signal-interface-kinds", json={"name": "PLC"})
        assert resp.status_code == 201
        assert resp.json()["name"] == "PLC"


class TestUpdateSignalInterfaceType:
    def test_returns_200_on_found(self, client, mock_conn):
        with patch(
            f"{_LOOKUP_REPO}.update_signal_interface_kind", return_value=_TYPE_ROW
        ):
            resp = client.put("/api/v1/signal-interface-kinds/1", json={"name": "PLC"})
        assert resp.status_code == 200

    def test_returns_404_on_miss(self, client, mock_conn):
        with patch(f"{_LOOKUP_REPO}.update_signal_interface_kind", return_value=None):
            resp = client.put("/api/v1/signal-interface-kinds/999", json={"name": "X"})
        assert resp.status_code == 404


class TestDeleteSignalInterfaceType:
    def test_returns_204_on_success(self, client, mock_conn):
        with patch(f"{_LOOKUP_REPO}.delete_signal_interface_kind", return_value=True):
            resp = client.delete("/api/v1/signal-interface-kinds/1")
        assert resp.status_code == 204

    def test_returns_404_on_miss(self, client, mock_conn):
        with patch(f"{_LOOKUP_REPO}.delete_signal_interface_kind", return_value=False):
            resp = client.delete("/api/v1/signal-interface-kinds/999")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# SignalInterface
# ---------------------------------------------------------------------------


class TestListSignalInterfaces:
    def test_returns_list(self, client, mock_conn):
        with patch(
            f"{_SI_REPO}.list_signal_interfaces", return_value=([_INTERFACE_ROW], 1)
        ):
            resp = client.get("/api/v1/signal-interfaces")
        assert resp.status_code == 200
        data = resp.json()
        assert data["items"][0]["name"] == "PLC-01"

    def test_filters_passed(self, client, mock_conn):
        with patch(
            f"{_SI_REPO}.list_signal_interfaces", return_value=([], 0)
        ) as mock_fn:
            resp = client.get("/api/v1/signal-interfaces?das_id=1&is_active=true")
        assert resp.status_code == 200
        _, kwargs = mock_fn.call_args
        assert kwargs.get("das_id") == 1
        assert kwargs.get("is_active") is True


class TestGetSignalInterface:
    def test_returns_200_on_found(self, client, mock_conn):
        with patch(
            f"{_SI_REPO}.get_signal_interface_by_id", return_value=_INTERFACE_ROW
        ):
            resp = client.get("/api/v1/signal-interfaces/1")
        assert resp.status_code == 200
        assert resp.json()["name"] == "PLC-01"

    def test_returns_404_on_miss(self, client, mock_conn):
        with patch(f"{_SI_REPO}.get_signal_interface_by_id", return_value=None):
            resp = client.get("/api/v1/signal-interfaces/999")
        assert resp.status_code == 404


class TestCreateSignalInterface:
    def test_returns_201(self, client, mock_conn):
        with patch(f"{_SI_REPO}.create_signal_interface", return_value=1):
            with patch(
                f"{_SI_REPO}.get_signal_interface_by_id", return_value=_INTERFACE_ROW
            ):
                resp = client.post(
                    "/api/v1/signal-interfaces",
                    json={
                        "data_acquisition_system_id": 1,
                        "name": "PLC-01",
                        "signal_interface_kind_id": 1,
                    },
                )
        assert resp.status_code == 201
        assert resp.json()["name"] == "PLC-01"


class TestPatchSignalInterface:
    def test_returns_200_on_found(self, client, mock_conn):
        with patch(
            f"{_SI_REPO}.get_signal_interface_by_id", return_value=_INTERFACE_ROW
        ):
            with patch(
                f"{_SI_REPO}.patch_signal_interface", return_value=_INTERFACE_ROW
            ):
                resp = client.patch(
                    "/api/v1/signal-interfaces/1",
                    json={"description": "Updated"},
                )
        assert resp.status_code == 200

    def test_returns_404_on_miss(self, client, mock_conn):
        with patch(f"{_SI_REPO}.get_signal_interface_by_id", return_value=None):
            resp = client.patch(
                "/api/v1/signal-interfaces/999",
                json={"description": "Updated"},
            )
        assert resp.status_code == 404


class TestDeleteSignalInterface:
    def test_returns_204_on_success(self, client, mock_conn):
        with patch(f"{_SI_REPO}.delete_signal_interface", return_value=True):
            resp = client.delete("/api/v1/signal-interfaces/1")
        assert resp.status_code == 204

    def test_returns_404_on_miss(self, client, mock_conn):
        with patch(f"{_SI_REPO}.delete_signal_interface", return_value=False):
            resp = client.delete("/api/v1/signal-interfaces/999")
        assert resp.status_code == 404


class TestListPortsUnderInterface:
    def test_returns_list(self, client, mock_conn):
        with patch(
            f"{_SI_REPO}.list_signal_interface_ports", return_value=([_PORT_ROW], 1)
        ):
            resp = client.get("/api/v1/signal-interfaces/1/ports")
        assert resp.status_code == 200
        data = resp.json()
        assert data["items"][0]["port_identifier"] == "6/Ch0"


class TestListChannelsUnderInterface:
    def test_returns_list(self, client, mock_conn):
        with patch(f"{_CHANNEL_REPO}.list_channels", return_value=([_CHANNEL_ROW], 1)):
            resp = client.get("/api/v1/signal-interfaces/1/channels")
        assert resp.status_code == 200
        data = resp.json()
        assert data["items"][0]["tag_name"] == "AI_01"


# ---------------------------------------------------------------------------
# SignalInterfacePort
# ---------------------------------------------------------------------------


class TestListSignalInterfacePorts:
    def test_returns_list(self, client, mock_conn):
        with patch(
            f"{_SIP_REPO}.list_signal_interface_ports", return_value=([_PORT_ROW], 1)
        ):
            resp = client.get("/api/v1/signal-interface-ports")
        assert resp.status_code == 200
        data = resp.json()
        assert data["items"][0]["port_identifier"] == "6/Ch0"

    def test_filter_by_interface(self, client, mock_conn):
        with patch(
            f"{_SIP_REPO}.list_signal_interface_ports", return_value=([], 0)
        ) as mock_fn:
            resp = client.get("/api/v1/signal-interface-ports?signal_interface_id=1")
        assert resp.status_code == 200
        _, kwargs = mock_fn.call_args
        assert kwargs.get("signal_interface_id") == 1


class TestGetSignalInterfacePort:
    def test_returns_200_on_found(self, client, mock_conn):
        with patch(
            f"{_SIP_REPO}.get_signal_interface_port_by_id", return_value=_PORT_ROW
        ):
            resp = client.get("/api/v1/signal-interface-ports/1")
        assert resp.status_code == 200
        assert resp.json()["port_identifier"] == "6/Ch0"

    def test_returns_404_on_miss(self, client, mock_conn):
        with patch(f"{_SIP_REPO}.get_signal_interface_port_by_id", return_value=None):
            resp = client.get("/api/v1/signal-interface-ports/999")
        assert resp.status_code == 404


class TestCreateSignalInterfacePort:
    def test_returns_201(self, client, mock_conn):
        with patch(f"{_SIP_REPO}.create_signal_interface_port", return_value=1):
            with patch(
                f"{_SIP_REPO}.get_signal_interface_port_by_id", return_value=_PORT_ROW
            ):
                resp = client.post(
                    "/api/v1/signal-interface-ports",
                    json={
                        "signal_interface_id": 1,
                        "port_identifier": "6/Ch0",
                        "signal_interface_port_kind_id": 1,
                    },
                )
        assert resp.status_code == 201
        assert resp.json()["port_identifier"] == "6/Ch0"


class TestPatchSignalInterfacePort:
    def test_returns_200_on_found(self, client, mock_conn):
        with patch(
            f"{_SIP_REPO}.get_signal_interface_port_by_id", return_value=_PORT_ROW
        ):
            with patch(
                f"{_SIP_REPO}.patch_signal_interface_port", return_value=_PORT_ROW
            ):
                resp = client.patch(
                    "/api/v1/signal-interface-ports/1",
                    json={"description": "Updated"},
                )
        assert resp.status_code == 200

    def test_returns_404_on_miss(self, client, mock_conn):
        with patch(f"{_SIP_REPO}.get_signal_interface_port_by_id", return_value=None):
            resp = client.patch(
                "/api/v1/signal-interface-ports/999",
                json={"description": "Updated"},
            )
        assert resp.status_code == 404


class TestDeleteSignalInterfacePort:
    def test_returns_204_on_success(self, client, mock_conn):
        with patch(f"{_SIP_REPO}.delete_signal_interface_port", return_value=True):
            resp = client.delete("/api/v1/signal-interface-ports/1")
        assert resp.status_code == 204

    def test_returns_404_on_miss(self, client, mock_conn):
        with patch(f"{_SIP_REPO}.delete_signal_interface_port", return_value=False):
            resp = client.delete("/api/v1/signal-interface-ports/999")
        assert resp.status_code == 404
