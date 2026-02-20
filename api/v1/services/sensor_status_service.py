"""Service for sensor status business logic."""

from datetime import datetime, timezone
from typing import Optional

from ..repositories.sensor_status_repository import SensorStatusRepository


class SensorStatusService:
    """Service for sensor status operations."""

    def __init__(self, repo: SensorStatusRepository):
        self.repo = repo

    def get_all_status_codes(self) -> list[dict]:
        """Get all sensor status codes for UI dropdowns."""
        return self.repo.get_all_status_codes()

    def get_equipment_status(
        self, equipment_id: int, at: Optional[datetime] = None
    ) -> Optional[dict]:
        """Get full health picture for an equipment."""
        if not self.repo.check_equipment_exists(equipment_id):
            return None

        equipment_name = self.repo.get_equipment_name(equipment_id)
        queried_at = at or datetime.now(timezone.utc)

        device_status = self.repo.get_current_device_status(equipment_id)

        channel_statuses = self.repo.get_all_channel_statuses_for_equipment(
            equipment_id
        )

        overall_operational = True
        worst_severity = 0

        if device_status:
            if not device_status.get("is_operational", True):
                overall_operational = False
            worst_severity = max(worst_severity, device_status.get("severity", 0))

        for channel in channel_statuses:
            if not channel.get("is_operational", True):
                overall_operational = False
            worst_severity = max(worst_severity, channel.get("severity", 0))

        formatted_channel_statuses = []
        for ch in channel_statuses:
            formatted_channel_statuses.append(
                {
                    "measurement_metadata_id": ch["measurement_metadata_id"],
                    "parameter": ch["measurement_parameter"],
                    "location": ch["location_name"],
                    "status_code": ch["status_code_id"],
                    "status_name": ch["status_name"],
                    "is_operational": ch["is_operational"],
                    "severity": ch["severity"],
                    "since": ch["status_since"],
                }
            )

        formatted_device_status = None
        if device_status:
            formatted_device_status = {
                "status_code": device_status["status_code_id"],
                "status_name": device_status["status_name"],
                "is_operational": device_status["is_operational"],
                "severity": device_status["severity"],
                "since": device_status["status_since"],
            }

        return {
            "equipment_id": equipment_id,
            "equipment_name": equipment_name,
            "queried_at": queried_at,
            "device_status": formatted_device_status,
            "channel_statuses": formatted_channel_statuses,
            "overall_operational": overall_operational,
            "worst_severity": worst_severity,
        }

    def get_equipment_status_history(
        self,
        equipment_id: int,
        from_dt: datetime,
        to_dt: datetime,
        channel: Optional[str] = None,
    ) -> Optional[dict]:
        """Get status transitions over a time range."""
        if not self.repo.check_equipment_exists(equipment_id):
            return None

        equipment_name = self.repo.get_equipment_name(equipment_id)

        device_transitions = self.repo.get_device_status_transitions(
            equipment_id, from_dt, to_dt
        )

        all_channels = self.repo.get_all_channel_statuses_for_equipment(equipment_id)

        channel_transitions = {}
        for ch in all_channels:
            metadata_id = ch["measurement_metadata_id"]
            parameter = ch["measurement_parameter"]

            if channel and parameter != channel:
                continue

            transitions = self.repo.get_channel_status_transitions(
                metadata_id, from_dt, to_dt
            )
            formatted_transitions = [
                {
                    "timestamp": t["transition_time"],
                    "status_code": t["status_code_id"],
                    "status_name": t["status_name"],
                    "is_operational": t["is_operational"],
                }
                for t in transitions
            ]

            channel_transitions[parameter] = {
                "measurement_metadata_id": metadata_id,
                "transitions": formatted_transitions,
            }

        formatted_device_transitions = [
            {
                "timestamp": t["transition_time"],
                "status_code": t["status_code_id"],
                "status_name": t["status_name"],
                "is_operational": t["is_operational"],
            }
            for t in device_transitions
        ]

        return {
            "equipment_id": equipment_id,
            "equipment_name": equipment_name,
            "query_range": {
                "from": from_dt.isoformat() + "Z",
                "to": to_dt.isoformat() + "Z",
            },
            "device_transitions": formatted_device_transitions,
            "channel_transitions": channel_transitions,
        }

    def get_timeseries_status_band(
        self, metadata_id: int, from_dt: datetime, to_dt: datetime
    ) -> Optional[dict]:
        """Get status band for a measurement channel."""
        if not self.repo.check_metadata_exists(metadata_id):
            return None

        parameter_name = self.repo.get_parameter_name(metadata_id)
        equipment_id = self.repo.get_equipment_for_metadata(metadata_id)
        equipment_name = None
        if equipment_id:
            equipment_name = self.repo.get_equipment_name(equipment_id)

        status_intervals = self.repo.get_status_band(metadata_id, from_dt, to_dt)

        has_status_data = len(status_intervals) > 0

        formatted_intervals = []
        for interval in status_intervals:
            formatted_intervals.append(
                {
                    "from": interval["from_time"],
                    "to": interval["to_time"],
                    "status_code": interval["status_code_id"],
                    "status_name": interval["status_name"],
                    "is_operational": interval["is_operational"],
                    "severity": interval["severity"],
                }
            )

        return {
            "metadata_id": metadata_id,
            "parameter": parameter_name,
            "equipment_name": equipment_name,
            "query_range": {
                "from": from_dt.isoformat() + "Z",
                "to": to_dt.isoformat() + "Z",
            },
            "status_intervals": formatted_intervals,
            "has_status_data": has_status_data,
        }
