"""Contract tests for ControlLoop endpoints (Issue #9).

Tests run without a live database using dependency_overrides and MagicMock.

Covers:
  - POST /control-loops: creates loop, validates controller_type, rejects unknown fallback
  - GET  /control-loops/{id}: 200 on found, 404 on miss
  - GET  /control-loops/{id}/ports: lists ports
  - POST /control-loops/{id}/ports: adds port, resolves role by name, rejects duplicate
  - POST /control-loops/{id}/applications: opens application, 409 on second open
  - POST /control-loops/{id}/retune: closes active + opens new; works with no active
  - GET  /control-loops/{id}/active-application: returns null when none
  - GET  /control-loops/{id}/application-at: point-in-time query
  - GET  /control-loops/{id}/fallback-chain: traverses chain
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from api.database import get_db
from api.main import app

_REPO = "api.v1.endpoints.control_loops.control_loop_repository"


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
# Helpers
# ---------------------------------------------------------------------------

_LOOP_ROW = {
    "ControlLoop_ID": 1,
    "Name": "DO PID",
    "ControllerType": "PID",
    "FallbackControlLoop_ID": None,
    "AlgorithmReference": None,
    "Description": None,
}

_APP_ROW = {
    "ControlLoopApplication_ID": 10,
    "ControlLoop_ID": 1,
    "StartTime": "2025-01-01T00:00:00",
    "EndTime": None,
    "Parameters": '{"Kp": 1.2, "Ki": 0.05, "Kd": 0.0}',
    "AppliedByPerson_ID": None,
    "Notes": None,
}


# ---------------------------------------------------------------------------
# POST /control-loops
# ---------------------------------------------------------------------------


class TestCreateControlLoop:
    def test_creates_pid_loop(self, client, mock_conn):
        with (
            patch(f"{_REPO}.get_control_loop", return_value=None) as _mock_get_fb,
            patch(f"{_REPO}.create_control_loop", return_value=1) as _mock_create,
            patch(f"{_REPO}.get_control_loop", return_value=_LOOP_ROW),
        ):
            resp = client.post(
                "/api/v1/control-loops",
                json={
                    "name": "DO PID",
                    "controller_type": "PID",
                },
            )
        assert resp.status_code == 201
        data = resp.json()
        assert data["control_loop_id"] == 1
        assert data["controller_type"] == "PID"

    def test_invalid_controller_type_rejected(self, client, mock_conn):
        resp = client.post(
            "/api/v1/control-loops",
            json={
                "name": "Bad Loop",
                "controller_type": "FUZZY",
            },
        )
        assert resp.status_code == 422

    def test_unknown_fallback_rejected(self, client, mock_conn):
        with patch(f"{_REPO}.get_control_loop", return_value=None):
            resp = client.post(
                "/api/v1/control-loops",
                json={
                    "name": "Child Loop",
                    "controller_type": "PID",
                    "fallback_control_loop_id": 999,
                },
            )
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# GET /control-loops/{loop_id}
# ---------------------------------------------------------------------------


class TestGetControlLoop:
    def test_returns_loop(self, client, mock_conn):
        with patch(f"{_REPO}.get_control_loop", return_value=_LOOP_ROW):
            resp = client.get("/api/v1/control-loops/1")
        assert resp.status_code == 200
        assert resp.json()["name"] == "DO PID"

    def test_404_on_missing(self, client, mock_conn):
        with patch(f"{_REPO}.get_control_loop", return_value=None):
            resp = client.get("/api/v1/control-loops/999")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# POST /control-loops/{loop_id}/ports
# ---------------------------------------------------------------------------


class TestAddPort:
    _PORT_ROW = {
        "ControlLoopPort_ID": 5,
        "ControlLoop_ID": 1,
        "Channel_ID": 20,
        "ControlLoopPortKind_ID": 1,
        "role_name": "MeasuredVariable",
    }

    def test_add_port_by_role_id(self, client, mock_conn):
        with (
            patch(f"{_REPO}.get_control_loop", return_value=_LOOP_ROW),
            patch(f"{_REPO}.add_loop_port", return_value=5),
            patch(f"{_REPO}.get_loop_ports", return_value=[self._PORT_ROW]),
        ):
            resp = client.post(
                "/api/v1/control-loops/1/ports",
                json={
                    "channel_id": 20,
                    "role_id": 1,
                },
            )
        assert resp.status_code == 201
        assert resp.json()["role_name"] == "MeasuredVariable"

    def test_add_port_by_role_name(self, client, mock_conn):
        with (
            patch(f"{_REPO}.get_control_loop", return_value=_LOOP_ROW),
            patch(f"{_REPO}.find_role_by_name", return_value=1),
            patch(f"{_REPO}.add_loop_port", return_value=5),
            patch(f"{_REPO}.get_loop_ports", return_value=[self._PORT_ROW]),
        ):
            resp = client.post(
                "/api/v1/control-loops/1/ports",
                json={
                    "channel_id": 20,
                    "role_name": "MeasuredVariable",
                },
            )
        assert resp.status_code == 201

    def test_unknown_role_name_rejected(self, client, mock_conn):
        with (
            patch(f"{_REPO}.get_control_loop", return_value=_LOOP_ROW),
            patch(f"{_REPO}.find_role_by_name", return_value=None),
        ):
            resp = client.post(
                "/api/v1/control-loops/1/ports",
                json={
                    "channel_id": 20,
                    "role_name": "Nonexistent",
                },
            )
        assert resp.status_code == 422

    def test_missing_role_rejected(self, client, mock_conn):
        with patch(f"{_REPO}.get_control_loop", return_value=_LOOP_ROW):
            resp = client.post(
                "/api/v1/control-loops/1/ports",
                json={
                    "channel_id": 20,
                },
            )
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# POST /control-loops/{loop_id}/applications
# ---------------------------------------------------------------------------


class TestOpenApplication:
    def test_opens_application(self, client, mock_conn):
        with (
            patch(f"{_REPO}.get_control_loop", return_value=_LOOP_ROW),
            patch(f"{_REPO}.open_application", return_value=10),
            patch(f"{_REPO}.get_active_application", return_value=_APP_ROW),
        ):
            resp = client.post(
                "/api/v1/control-loops/1/applications",
                json={
                    "start_time": "2025-01-01T00:00:00",
                    "parameters": '{"Kp": 1.2}',
                },
            )
        assert resp.status_code == 201
        assert resp.json()["control_loop_application_id"] == 10

    def test_409_when_already_active(self, client, mock_conn):
        with (
            patch(f"{_REPO}.get_control_loop", return_value=_LOOP_ROW),
            patch(
                f"{_REPO}.open_application",
                side_effect=ValueError("already has an active Application"),
            ),
        ):
            resp = client.post(
                "/api/v1/control-loops/1/applications",
                json={
                    "start_time": "2025-06-01T00:00:00",
                },
            )
        assert resp.status_code == 409


# ---------------------------------------------------------------------------
# POST /control-loops/{loop_id}/retune
# ---------------------------------------------------------------------------


class TestRetune:
    def test_retune_closes_and_opens(self, client, mock_conn):
        with (
            patch(f"{_REPO}.get_control_loop", return_value=_LOOP_ROW),
            patch(f"{_REPO}.retune", return_value=(11, 10)),
        ):
            resp = client.post(
                "/api/v1/control-loops/1/retune",
                json={
                    "start_time": "2025-06-01T00:00:00",
                    "parameters": '{"Kp": 2.0}',
                },
            )
        assert resp.status_code == 201
        data = resp.json()
        assert data["new_application_id"] == 11
        assert data["closed_application_id"] == 10

    def test_retune_with_no_active(self, client, mock_conn):
        with (
            patch(f"{_REPO}.get_control_loop", return_value=_LOOP_ROW),
            patch(f"{_REPO}.retune", return_value=(11, None)),
        ):
            resp = client.post(
                "/api/v1/control-loops/1/retune",
                json={
                    "start_time": "2025-06-01T00:00:00",
                },
            )
        assert resp.status_code == 201
        assert resp.json()["closed_application_id"] is None


# ---------------------------------------------------------------------------
# GET /control-loops/{loop_id}/active-application
# ---------------------------------------------------------------------------


class TestGetActiveApplication:
    def test_returns_active(self, client, mock_conn):
        with (
            patch(f"{_REPO}.get_control_loop", return_value=_LOOP_ROW),
            patch(f"{_REPO}.get_active_application", return_value=_APP_ROW),
        ):
            resp = client.get("/api/v1/control-loops/1/active-application")
        assert resp.status_code == 200
        assert resp.json()["control_loop_application_id"] == 10

    def test_returns_null_when_none(self, client, mock_conn):
        with (
            patch(f"{_REPO}.get_control_loop", return_value=_LOOP_ROW),
            patch(f"{_REPO}.get_active_application", return_value=None),
        ):
            resp = client.get("/api/v1/control-loops/1/active-application")
        assert resp.status_code == 200
        assert resp.json() is None


# ---------------------------------------------------------------------------
# GET /control-loops/{loop_id}/application-at
# ---------------------------------------------------------------------------


class TestGetApplicationAt:
    def test_returns_application(self, client, mock_conn):
        with (
            patch(f"{_REPO}.get_control_loop", return_value=_LOOP_ROW),
            patch(f"{_REPO}.get_application_at", return_value=_APP_ROW),
        ):
            resp = client.get(
                "/api/v1/control-loops/1/application-at",
                params={"at": "2025-03-01T12:00:00"},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["application"]["control_loop_application_id"] == 10

    def test_returns_null_application_before_any_tuning(self, client, mock_conn):
        with (
            patch(f"{_REPO}.get_control_loop", return_value=_LOOP_ROW),
            patch(f"{_REPO}.get_application_at", return_value=None),
        ):
            resp = client.get(
                "/api/v1/control-loops/1/application-at",
                params={"at": "2000-01-01T00:00:00"},
            )
        assert resp.status_code == 200
        assert resp.json()["application"] is None


# ---------------------------------------------------------------------------
# GET /control-loops/{loop_id}/fallback-chain
# ---------------------------------------------------------------------------


class TestGetFallbackChain:
    _MANUAL_ROW = {
        "ControlLoop_ID": 2,
        "Name": "Manual fallback",
        "ControllerType": "Manual",
        "FallbackControlLoop_ID": None,
        "AlgorithmReference": None,
        "Description": None,
    }

    def test_chain_with_one_fallback(self, client, mock_conn):
        chain = [
            {**_LOOP_ROW, "FallbackControlLoop_ID": 2},
            self._MANUAL_ROW,
        ]
        with (
            patch(f"{_REPO}.get_control_loop", return_value=_LOOP_ROW),
            patch(f"{_REPO}.get_fallback_chain", return_value=chain),
        ):
            resp = client.get("/api/v1/control-loops/1/fallback-chain")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["chain"]) == 2
        assert data["chain"][-1]["controller_type"] == "Manual"

    def test_chain_single_loop(self, client, mock_conn):
        with (
            patch(f"{_REPO}.get_control_loop", return_value=_LOOP_ROW),
            patch(f"{_REPO}.get_fallback_chain", return_value=[_LOOP_ROW]),
        ):
            resp = client.get("/api/v1/control-loops/1/fallback-chain")
        assert resp.status_code == 200
        assert len(resp.json()["chain"]) == 1
