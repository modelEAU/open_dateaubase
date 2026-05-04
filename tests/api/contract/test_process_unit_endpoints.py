"""Contract tests for ProcessUnit and ProcessUnitType endpoints (Issue #23).

Tests run without a live database using dependency_overrides and MagicMock.

Covers:
  - GET  /process-unit-kinds: returns list
  - POST /process-unit-kinds: creates type, returns 201
  - GET  /process-units: returns list, accepts site_id filter
  - GET  /process-units/{id}: 200 on found, 404 on miss
  - POST /process-units: creates unit, returns 201
  - PUT  /process-units/{id}: 200 on found, 404 on miss
  - DELETE /process-units/{id}: 204 on success, 404 on miss, 409 on dependency
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from api.database import get_db
from api.main import app

_TYPES_REPO = "api.v1.endpoints.process_units.process_unit_repository"
_UNITS_REPO = "api.v1.endpoints.process_units.process_unit_repository"


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

_TYPE_ROW = {"process_unit_kind_id": 1, "name": "Reactor", "description": None}

_UNIT_ROW = {
    "id": 1,
    "site_id": 1,
    "tag": "R-210",
    "name": "Reacteur R-210",
    "description": None,
    "process_unit_kind_id": 1,
    "process_unit_kind_name": "Reactor",
    "parent_id": None,
    "parent_name": None,
}


# ---------------------------------------------------------------------------
# ProcessUnitType
# ---------------------------------------------------------------------------


class TestListProcessUnitTypes:
    def test_returns_list(self, client, mock_conn):
        with patch(f"{_TYPES_REPO}.get_all_process_unit_types", return_value=[_TYPE_ROW]):
            resp = client.get("/api/v1/process-unit-kinds")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert data[0]["name"] == "Reactor"

    def test_empty_list(self, client, mock_conn):
        with patch(f"{_TYPES_REPO}.get_all_process_unit_types", return_value=[]):
            resp = client.get("/api/v1/process-unit-kinds")
        assert resp.status_code == 200
        assert resp.json() == []


class TestCreateProcessUnitType:
    def test_returns_201(self, client, mock_conn):
        with patch(f"{_TYPES_REPO}.insert_process_unit_type", return_value=_TYPE_ROW):
            resp = client.post("/api/v1/process-unit-kinds", json={"name": "Reactor"})
        assert resp.status_code == 201
        assert resp.json()["name"] == "Reactor"


class TestUpdateProcessUnitType:
    def test_returns_200_on_found(self, client, mock_conn):
        with patch(f"{_TYPES_REPO}.update_process_unit_type", return_value=_TYPE_ROW):
            resp = client.put("/api/v1/process-unit-kinds/1", json={"name": "Reactor"})
        assert resp.status_code == 200

    def test_returns_404_on_miss(self, client, mock_conn):
        with patch(f"{_TYPES_REPO}.update_process_unit_type", return_value=None):
            resp = client.put("/api/v1/process-unit-kinds/999", json={"name": "X"})
        assert resp.status_code == 404


class TestDeleteProcessUnitType:
    def test_returns_204_on_success(self, client, mock_conn):
        with patch(f"{_TYPES_REPO}.delete_process_unit_type", return_value=True):
            resp = client.delete("/api/v1/process-unit-kinds/1")
        assert resp.status_code == 204

    def test_returns_404_on_miss(self, client, mock_conn):
        with patch(f"{_TYPES_REPO}.delete_process_unit_type", return_value=False):
            resp = client.delete("/api/v1/process-unit-kinds/999")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# ProcessUnit
# ---------------------------------------------------------------------------


class TestListProcessUnits:
    def test_returns_list(self, client, mock_conn):
        with patch(f"{_UNITS_REPO}.get_all_process_units", return_value=[_UNIT_ROW]):
            resp = client.get("/api/v1/process-units")
        assert resp.status_code == 200
        assert resp.json()[0]["tag"] == "R-210"

    def test_site_id_filter_passed(self, client, mock_conn):
        with patch(f"{_UNITS_REPO}.get_all_process_units", return_value=[]) as mock_fn:
            resp = client.get("/api/v1/process-units?site_id=2")
        assert resp.status_code == 200
        mock_fn.assert_called_once()
        _, kwargs = mock_fn.call_args
        assert kwargs.get("site_id") == 2

    def test_tree_mode_calls_tree_fn(self, client, mock_conn):
        with patch(f"{_UNITS_REPO}.get_process_unit_tree", return_value=[]) as mock_tree:
            resp = client.get("/api/v1/process-units?site_id=1&tree=true")
        assert resp.status_code == 200
        mock_tree.assert_called_once()


class TestGetProcessUnit:
    def test_returns_200_on_found(self, client, mock_conn):
        with patch(f"{_UNITS_REPO}.get_process_unit_by_id", return_value=_UNIT_ROW):
            resp = client.get("/api/v1/process-units/1")
        assert resp.status_code == 200
        assert resp.json()["id"] == 1

    def test_returns_404_on_miss(self, client, mock_conn):
        with patch(f"{_UNITS_REPO}.get_process_unit_by_id", return_value=None):
            resp = client.get("/api/v1/process-units/999")
        assert resp.status_code == 404


class TestCreateProcessUnit:
    def test_returns_201(self, client, mock_conn):
        with patch(f"{_UNITS_REPO}.insert_process_unit", return_value=_UNIT_ROW):
            resp = client.post(
                "/api/v1/process-units",
                json={"site_id": 1, "tag": "R-210", "name": "Reacteur R-210"},
            )
        assert resp.status_code == 201
        assert resp.json()["tag"] == "R-210"


class TestUpdateProcessUnit:
    def test_returns_200_on_found(self, client, mock_conn):
        with patch(f"{_UNITS_REPO}.update_process_unit", return_value=_UNIT_ROW):
            resp = client.put(
                "/api/v1/process-units/1",
                json={"site_id": 1, "tag": "R-210", "name": "Updated"},
            )
        assert resp.status_code == 200

    def test_returns_404_on_miss(self, client, mock_conn):
        with patch(f"{_UNITS_REPO}.update_process_unit", return_value=None):
            resp = client.put(
                "/api/v1/process-units/999",
                json={"site_id": 1, "tag": "X", "name": "X"},
            )
        assert resp.status_code == 404


class TestDeleteProcessUnit:
    def test_returns_204_on_success(self, client, mock_conn):
        with patch(f"{_UNITS_REPO}.delete_process_unit", return_value=True):
            resp = client.delete("/api/v1/process-units/1")
        assert resp.status_code == 204

    def test_returns_404_on_miss(self, client, mock_conn):
        with patch(f"{_UNITS_REPO}.delete_process_unit", return_value=False):
            resp = client.delete("/api/v1/process-units/999")
        assert resp.status_code == 404

    def test_returns_409_when_children_exist(self, client, mock_conn):
        with patch(
            f"{_UNITS_REPO}.delete_process_unit",
            side_effect=ValueError("ProcessUnit 1 has 2 child unit(s)."),
        ):
            resp = client.delete("/api/v1/process-units/1")
        assert resp.status_code == 409

    def test_returns_409_when_sampling_points_linked(self, client, mock_conn):
        with patch(
            f"{_UNITS_REPO}.delete_process_unit",
            side_effect=ValueError("ProcessUnit 1 is linked to 3 sampling point(s)."),
        ):
            resp = client.delete("/api/v1/process-units/1")
        assert resp.status_code == 409
