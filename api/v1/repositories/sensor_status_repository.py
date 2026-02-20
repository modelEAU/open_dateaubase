"""Repository for sensor status SQL queries."""

from datetime import datetime
from typing import Optional

import pyodbc


class SensorStatusRepository:
    """Repository for sensor status queries."""

    def __init__(self, conn: pyodbc.Connection):
        self.conn = conn

    def get_all_status_codes(self) -> list[dict]:
        """Get all sensor status codes."""
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT StatusCodeID AS id, StatusName AS name, Description AS description,
                   IsOperational AS is_operational, Severity AS severity
            FROM dbo.SensorStatusCode
            ORDER BY StatusCodeID
            """
        )
        rows = cursor.fetchall()
        cursor.close()
        return [
            {
                "id": row[0],
                "name": row[1],
                "description": row[2],
                "is_operational": bool(row[3]) if row[3] is not None else None,
                "severity": row[4],
            }
            for row in rows
        ]

    def get_current_channel_status(
        self, measurement_metadata_id: int
    ) -> Optional[dict]:
        """Get the current status for a measurement channel (Query 1)."""
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT TOP 1
                sc.StatusCodeID AS status_code_id,
                sc.StatusName AS status_name,
                sc.IsOperational AS is_operational,
                sc.Severity AS severity,
                v.[Timestamp] AS status_since
            FROM dbo.MetaData statusMD
            JOIN dbo.Value v ON v.[Metadata_ID] = statusMD.[Metadata_ID]
            JOIN dbo.SensorStatusCode sc ON sc.StatusCodeID = CAST(v.Value AS INT)
            WHERE statusMD.StatusOfMetaDataID = ?
            ORDER BY v.[Timestamp] DESC
            """,
            measurement_metadata_id,
        )
        row = cursor.fetchone()
        cursor.close()
        if not row:
            return None
        return {
            "status_code_id": row[0],
            "status_name": row[1],
            "is_operational": bool(row[2]) if row[2] is not None else None,
            "severity": row[3],
            "status_since": row[4],
        }

    def get_channel_status_at_time(
        self, measurement_metadata_id: int, timestamp: datetime
    ) -> Optional[dict]:
        """Get the status at a specific point in time (Query 2)."""
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT TOP 1
                sc.StatusCodeID AS status_code_id,
                sc.StatusName AS status_name,
                sc.IsOperational AS is_operational,
                sc.Severity AS severity,
                v.[Timestamp] AS status_since
            FROM dbo.MetaData statusMD
            JOIN dbo.Value v ON v.[Metadata_ID] = statusMD.[Metadata_ID]
            JOIN dbo.SensorStatusCode sc ON sc.StatusCodeID = CAST(v.Value AS INT)
            WHERE statusMD.StatusOfMetaDataID = ?
              AND v.[Timestamp] <= ?
            ORDER BY v.[Timestamp] DESC
            """,
            measurement_metadata_id,
            timestamp,
        )
        row = cursor.fetchone()
        cursor.close()
        if not row:
            return None
        return {
            "status_code_id": row[0],
            "status_name": row[1],
            "is_operational": bool(row[2]) if row[2] is not None else None,
            "severity": row[3],
            "status_since": row[4],
        }

    def get_channel_status_transitions(
        self, measurement_metadata_id: int, t1: datetime, t2: datetime
    ) -> list[dict]:
        """Get channel status transitions in a time range (Query 3)."""
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT
                v.[Timestamp] AS transition_time,
                sc.StatusCodeID AS status_code_id,
                sc.StatusName AS status_name,
                sc.IsOperational AS is_operational,
                sc.Severity AS severity
            FROM dbo.MetaData statusMD
            JOIN dbo.Value v ON v.[Metadata_ID] = statusMD.[Metadata_ID]
            JOIN dbo.SensorStatusCode sc ON sc.StatusCodeID = CAST(v.Value AS INT)
            WHERE statusMD.StatusOfMetaDataID = ?
              AND v.[Timestamp] BETWEEN ? AND ?
            ORDER BY v.[Timestamp]
            """,
            measurement_metadata_id,
            t1,
            t2,
        )
        rows = cursor.fetchall()
        cursor.close()
        return [
            {
                "transition_time": row[0],
                "status_code_id": row[1],
                "status_name": row[2],
                "is_operational": bool(row[3]) if row[3] is not None else None,
                "severity": row[4],
            }
            for row in rows
        ]

    def get_device_status_transitions(
        self, equipment_id: int, t1: datetime, t2: datetime
    ) -> list[dict]:
        """Get device-level status transitions in a time range."""
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT
                v.[Timestamp] AS transition_time,
                sc.StatusCodeID AS status_code_id,
                sc.StatusName AS status_name,
                sc.IsOperational AS is_operational,
                sc.Severity AS severity
            FROM dbo.MetaData statusMD
            JOIN dbo.Value v ON v.[Metadata_ID] = statusMD.[Metadata_ID]
            JOIN dbo.SensorStatusCode sc ON sc.StatusCodeID = CAST(v.Value AS INT)
            WHERE statusMD.StatusOfEquipmentID = ?
              AND v.[Timestamp] BETWEEN ? AND ?
            ORDER BY v.[Timestamp]
            """,
            equipment_id,
            t1,
            t2,
        )
        rows = cursor.fetchall()
        cursor.close()
        return [
            {
                "transition_time": row[0],
                "status_code_id": row[1],
                "status_name": row[2],
                "is_operational": bool(row[3]) if row[3] is not None else None,
                "severity": row[4],
            }
            for row in rows
        ]

    def get_status_band(
        self, measurement_metadata_id: int, t1: datetime, t2: datetime
    ) -> list[dict]:
        """Get status intervals for rendering (Query 4)."""
        cursor = self.conn.cursor()
        cursor.execute(
            """
            WITH StatusTransitions AS (
                SELECT TOP 1
                    v.[Timestamp] AS transition_time,
                    CAST(v.Value AS INT) AS status_code_id
                FROM dbo.MetaData statusMD
                JOIN dbo.Value v ON v.[Metadata_ID] = statusMD.[Metadata_ID]
                WHERE statusMD.StatusOfMetaDataID = ?
                  AND v.[Timestamp] <= ?
                ORDER BY v.[Timestamp] DESC

                UNION ALL

                SELECT
                    v.[Timestamp] AS transition_time,
                    CAST(v.Value AS INT) AS status_code_id
                FROM dbo.MetaData statusMD
                JOIN dbo.Value v ON v.[Metadata_ID] = statusMD.[Metadata_ID]
                WHERE statusMD.StatusOfMetaDataID = ?
                  AND v.[Timestamp] > ? AND v.[Timestamp] <= ?
            ),
            StatusIntervals AS (
                SELECT
                    transition_time AS interval_start,
                    LEAD(transition_time) OVER (ORDER BY transition_time) AS interval_end,
                    status_code_id
                FROM StatusTransitions
            )
            SELECT
                CASE WHEN si.interval_start < ? THEN ? ELSE si.interval_start END AS from_time,
                CASE WHEN si.interval_end IS NULL THEN ?
                     WHEN si.interval_end > ? THEN ?
                     ELSE si.interval_end END AS to_time,
                sc.StatusCodeID AS status_code_id,
                sc.StatusName AS status_name,
                sc.IsOperational AS is_operational,
                sc.Severity AS severity
            FROM StatusIntervals si
            JOIN dbo.SensorStatusCode sc ON sc.StatusCodeID = si.status_code_id
            WHERE si.interval_end IS NULL OR si.interval_end > ?
            ORDER BY si.interval_start
            """,
            measurement_metadata_id,
            t1,
            measurement_metadata_id,
            t1,
            t2,
            t1,
            t1,
            t2,
            t2,
            t1,
        )
        rows = cursor.fetchall()
        cursor.close()
        return [
            {
                "from_time": row[0],
                "to_time": row[1],
                "status_code_id": row[2],
                "status_name": row[3],
                "is_operational": bool(row[4]) if row[4] is not None else None,
                "severity": row[5],
            }
            for row in rows
        ]

    def get_all_channel_statuses_for_equipment(self, equipment_id: int) -> list[dict]:
        """Get all channel statuses for an equipment (Query 7)."""
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT
                measMD.[Metadata_ID] AS measurement_metadata_id,
                p.[Parameter] AS measurement_parameter,
                sp.[Sampling_point] AS location_name,
                sc.StatusCodeID AS status_code_id,
                sc.StatusName AS status_name,
                sc.IsOperational AS is_operational,
                sc.Severity AS severity,
                latestStatus.[Timestamp] AS status_since
            FROM dbo.MetaData statusMD
            JOIN dbo.MetaData measMD ON measMD.[Metadata_ID] = statusMD.StatusOfMetaDataID
            JOIN dbo.Parameter p ON p.Parameter_ID = measMD.Parameter_ID
            JOIN dbo.SamplingPoints sp ON sp.Sampling_point_ID = measMD.Sampling_point_ID
            CROSS APPLY (
                SELECT TOP 1 v.[Timestamp], v.Value
                FROM dbo.Value v
                WHERE v.[Metadata_ID] = statusMD.[Metadata_ID]
                ORDER BY v.[Timestamp] DESC
            ) latestStatus
            JOIN dbo.SensorStatusCode sc ON sc.StatusCodeID = CAST(latestStatus.Value AS INT)
            WHERE measMD.Equipment_ID = ?
              AND statusMD.StatusOfMetaDataID IS NOT NULL
            ORDER BY p.[Parameter]
            """,
            equipment_id,
        )
        rows = cursor.fetchall()
        cursor.close()
        return [
            {
                "measurement_metadata_id": row[0],
                "measurement_parameter": row[1],
                "location_name": row[2],
                "status_code_id": row[3],
                "status_name": row[4],
                "is_operational": bool(row[5]) if row[5] is not None else None,
                "severity": row[6],
                "status_since": row[7],
            }
            for row in rows
        ]

    def get_current_device_status(self, equipment_id: int) -> Optional[dict]:
        """Get current device-level status (Query 8)."""
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT TOP 1
                sc.StatusCodeID AS status_code_id,
                sc.StatusName AS status_name,
                sc.IsOperational AS is_operational,
                sc.Severity AS severity,
                v.[Timestamp] AS status_since
            FROM dbo.MetaData statusMD
            JOIN dbo.Value v ON v.[Metadata_ID] = statusMD.[Metadata_ID]
            JOIN dbo.SensorStatusCode sc ON sc.StatusCodeID = CAST(v.Value AS INT)
            WHERE statusMD.StatusOfEquipmentID = ?
            ORDER BY v.[Timestamp] DESC
            """,
            equipment_id,
        )
        row = cursor.fetchone()
        cursor.close()
        if not row:
            return None
        return {
            "status_code_id": row[0],
            "status_name": row[1],
            "is_operational": bool(row[2]) if row[2] is not None else None,
            "severity": row[3],
            "status_since": row[4],
        }

    def get_equipment_name(self, equipment_id: int) -> Optional[str]:
        """Get equipment name by ID."""
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT identifier FROM dbo.Equipment WHERE Equipment_ID = ?",
            equipment_id,
        )
        row = cursor.fetchone()
        cursor.close()
        return row[0] if row else None

    def get_parameter_name(self, metadata_id: int) -> Optional[str]:
        """Get parameter name for a MetaData entry."""
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT p.[Parameter]
            FROM dbo.MetaData md
            JOIN dbo.Parameter p ON p.Parameter_ID = md.Parameter_ID
            WHERE md.Metadata_ID = ?
            """,
            metadata_id,
        )
        row = cursor.fetchone()
        cursor.close()
        return row[0] if row else None

    def get_equipment_for_metadata(self, metadata_id: int) -> Optional[int]:
        """Get equipment ID for a MetaData entry."""
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT Equipment_ID FROM dbo.MetaData WHERE Metadata_ID = ?",
            metadata_id,
        )
        row = cursor.fetchone()
        cursor.close()
        return row[0] if row else None

    def check_metadata_exists(self, metadata_id: int) -> bool:
        """Check if a MetaData entry exists."""
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT 1 FROM dbo.MetaData WHERE Metadata_ID = ?",
            metadata_id,
        )
        row = cursor.fetchone()
        cursor.close()
        return row is not None

    def check_equipment_exists(self, equipment_id: int) -> bool:
        """Check if an equipment entry exists."""
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT 1 FROM dbo.Equipment WHERE Equipment_ID = ?",
            equipment_id,
        )
        row = cursor.fetchone()
        cursor.close()
        return row is not None
