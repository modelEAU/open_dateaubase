"""Tests for sensor status API endpoints contract."""

import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch


class TestSensorStatusEndpointsContract:
    """Test that sensor status endpoints match documented API contracts."""

    @pytest.fixture
    def mock_repo(self):
        """Create a mock repository."""
        repo = MagicMock()
        repo.get_all_status_codes.return_value = [
            {
                "id": 0,
                "name": "Unknown",
                "description": "Status not reported",
                "is_operational": False,
                "severity": 1,
            },
            {
                "id": 1,
                "name": "Operational",
                "description": "Sensor working normally",
                "is_operational": True,
                "severity": 0,
            },
        ]
        return repo

    @pytest.fixture
    def mock_service(self, mock_repo):
        """Create a mock service."""
        from api.v1.services.sensor_status_service import SensorStatusService

        return SensorStatusService(mock_repo)

    def test_status_codes_response_format(self, mock_service):
        """GET /status-codes should return the documented schema."""
        result = mock_service.get_all_status_codes()

        assert isinstance(result, list)
        for item in result:
            assert "id" in item
            assert "name" in item
            assert "description" in item
            assert "is_operational" in item
            assert "severity" in item

    def test_equipment_status_response_format(self, mock_repo, mock_service):
        """GET /equipment/{id}/status should return documented schema."""
        mock_repo.check_equipment_exists.return_value = True
        mock_repo.get_equipment_name.return_value = "SC1000_Controller"
        mock_repo.get_current_device_status.return_value = {
            "status_code_id": 1,
            "status_name": "Operational",
            "is_operational": True,
            "severity": 0,
            "status_since": datetime(2025, 1, 1),
        }
        mock_repo.get_all_channel_statuses_for_equipment.return_value = [
            {
                "measurement_metadata_id": 42,
                "measurement_parameter": "TSS",
                "location_name": "Primary Effluent",
                "status_code_id": 1,
                "status_name": "Operational",
                "is_operational": True,
                "severity": 0,
                "status_since": datetime(2025, 1, 1),
            },
        ]

        result = mock_service.get_equipment_status(equipment_id=5)

        assert result is not None
        assert result["equipment_id"] == 5
        assert result["equipment_name"] == "SC1000_Controller"
        assert "device_status" in result
        assert "channel_statuses" in result
        assert "overall_operational" in result
        assert "worst_severity" in result

    def test_timeseries_status_response_format(self, mock_repo, mock_service):
        """GET /timeseries/{id}/status should return documented schema."""
        mock_repo.check_metadata_exists.return_value = True
        mock_repo.get_parameter_name.return_value = "pH"
        mock_repo.get_equipment_for_metadata.return_value = 5
        mock_repo.get_equipment_name.return_value = "SC1000"
        mock_repo.get_status_band.return_value = [
            {
                "from_time": datetime(2025, 2, 1),
                "to_time": datetime(2025, 2, 15),
                "status_code_id": 1,
                "status_name": "Operational",
                "is_operational": True,
                "severity": 0,
            },
        ]

        result = mock_service.get_timeseries_status_band(
            metadata_id=42,
            from_dt=datetime(2025, 2, 1),
            to_dt=datetime(2025, 2, 28),
        )

        assert result is not None
        assert result["metadata_id"] == 42
        assert result["parameter"] == "pH"
        assert "query_range" in result
        assert "status_intervals" in result
        assert "has_status_data" in result

    def test_status_history_response_format(self, mock_repo, mock_service):
        """GET /equipment/{id}/status/history should return documented schema."""
        mock_repo.check_equipment_exists.return_value = True
        mock_repo.get_equipment_name.return_value = "SC1000"
        mock_repo.get_channel_status_transitions.return_value = [
            {
                "transition_time": datetime(2025, 2, 15),
                "status_code_id": 10,
                "status_name": "Fouled",
                "is_operational": True,
                "severity": 2,
            },
        ]
        mock_repo.get_all_channel_statuses_for_equipment.return_value = [
            {
                "measurement_metadata_id": 42,
                "measurement_parameter": "pH",
                "status_code_id": 10,
                "status_name": "Fouled",
                "is_operational": True,
                "severity": 2,
            },
        ]

        result = mock_service.get_equipment_status_history(
            equipment_id=5,
            from_dt=datetime(2025, 2, 1),
            to_dt=datetime(2025, 2, 28),
        )

        assert result is not None
        assert result["equipment_id"] == 5
        assert "query_range" in result
        assert "device_transitions" in result
        assert "channel_transitions" in result


class TestSensorStatusSchemas:
    """Test Pydantic schemas for sensor status."""

    def test_status_code_response_schema(self):
        """StatusCodeResponse should validate correctly."""
        from api.v1.schemas.sensor_status import StatusCodeResponse

        data = {
            "id": 1,
            "name": "Operational",
            "description": "Sensor is working",
            "is_operational": True,
            "severity": 0,
        }
        model = StatusCodeResponse(**data)
        assert model.id == 1
        assert model.name == "Operational"

    def test_status_interval_schema(self):
        """StatusInterval should serialize with from/to field names."""
        from api.v1.schemas.sensor_status import StatusInterval

        data = {
            "from": datetime(2025, 2, 1),
            "to": datetime(2025, 2, 15),
            "status_code": 1,
            "status_name": "Operational",
            "is_operational": True,
            "severity": 0,
        }
        model = StatusInterval(**data)
        assert model.from_time == datetime(2025, 2, 1)
        assert model.to_time == datetime(2025, 2, 15)

    def test_status_interval_json_serialization(self):
        """StatusInterval should serialize to JSON with 'from' and 'to' keys."""
        from api.v1.schemas.sensor_status import StatusInterval

        data = {
            "from": datetime(2025, 2, 1),
            "to": datetime(2025, 2, 15),
            "status_code": 1,
            "status_name": "Operational",
            "is_operational": True,
            "severity": 0,
        }
        model = StatusInterval(**data)
        json_str = model.model_dump_json(by_alias=True)
        assert '"from"' in json_str
        assert '"to"' in json_str
