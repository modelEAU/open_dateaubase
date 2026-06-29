"""Repository for sensor status SQL queries."""

from datetime import datetime
from typing import Optional

import pyodbc

# Sub-query fragment: given a measurement channel_id (?), find the Channel_ID of its
# Status sub-signal channel.  Used as an inline scalar subquery.
# New schema: Status channels are linked via ParentChannel_ID + ChannelKind.Name = 'Status'
_STATUS_CHANNEL_FOR_MEASUREMENT = """
    (SELECT sc.[Channel_ID]
     FROM   [dbo].[Channel]       sc
     JOIN   [dbo].[ChannelKind]   cr  ON cr.[ChannelKind_ID]  = sc.[ChannelKind_ID]
     WHERE  sc.[ParentChannel_ID] = ?
       AND  cr.[Name] = N'Status')
"""


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

    def get_current_channel_status(self, measurement_channel_id: int) -> Optional[dict]:
        """Get the current status for a measurement channel (Query 1)."""
        cursor = self.conn.cursor()
        cursor.execute(
            f"""
            SELECT TOP 1
                sc.StatusCodeID AS status_code_id,
                sc.StatusName AS status_name,
                sc.IsOperational AS is_operational,
                sc.Severity AS severity,
                o.[Timestamp] AS status_since
            FROM [dbo].[Observation] o
            JOIN [dbo].[Value] v ON v.[Observation_ID] = o.[Observation_ID]
            JOIN [dbo].[SensorStatusCode] sc ON sc.StatusCodeID = CAST(v.Value AS INT)
            WHERE o.[Channel_ID] = {_STATUS_CHANNEL_FOR_MEASUREMENT}
            ORDER BY o.[Timestamp] DESC
            """,
            measurement_channel_id,
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
        self, measurement_channel_id: int, timestamp: datetime
    ) -> Optional[dict]:
        """Get the status at a specific point in time (Query 2)."""
        cursor = self.conn.cursor()
        cursor.execute(
            f"""
            SELECT TOP 1
                sc.StatusCodeID AS status_code_id,
                sc.StatusName AS status_name,
                sc.IsOperational AS is_operational,
                sc.Severity AS severity,
                o.[Timestamp] AS status_since
            FROM [dbo].[Observation] o
            JOIN [dbo].[Value] v ON v.[Observation_ID] = o.[Observation_ID]
            JOIN [dbo].[SensorStatusCode] sc ON sc.StatusCodeID = CAST(v.Value AS INT)
            WHERE o.[Channel_ID] = {_STATUS_CHANNEL_FOR_MEASUREMENT}
              AND o.[Timestamp] <= ?
            ORDER BY o.[Timestamp] DESC
            """,
            measurement_channel_id,
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
        self, measurement_channel_id: int, t1: datetime, t2: datetime
    ) -> list[dict]:
        """Get channel status transitions in a time range (Query 3)."""
        cursor = self.conn.cursor()
        cursor.execute(
            f"""
            SELECT
                o.[Timestamp] AS transition_time,
                sc.StatusCodeID AS status_code_id,
                sc.StatusName AS status_name,
                sc.IsOperational AS is_operational,
                sc.Severity AS severity
            FROM [dbo].[Observation] o
            JOIN [dbo].[Value] v ON v.[Observation_ID] = o.[Observation_ID]
            JOIN [dbo].[SensorStatusCode] sc ON sc.StatusCodeID = CAST(v.Value AS INT)
            WHERE o.[Channel_ID] = {_STATUS_CHANNEL_FOR_MEASUREMENT}
              AND o.[Timestamp] BETWEEN ? AND ?
            ORDER BY o.[Timestamp]
            """,
            measurement_channel_id,
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
        # Device status: join through EquipmentWiringHistory -> Channel -> Status sub-channel
        cursor.execute(
            """
            SELECT
                o.[Timestamp] AS transition_time,
                sc.StatusCodeID AS status_code_id,
                sc.StatusName AS status_name,
                sc.IsOperational AS is_operational,
                sc.Severity AS severity
            FROM [dbo].[EquipmentWiringHistory] ewh
            JOIN [dbo].[vw_ChannelResolved] valueC ON valueC.[SignalInterface_ID] = ewh.[SignalInterface_ID]
                                            AND (
                                                valueC.[SignalInterfacePort_ID] = ewh.[SignalInterfacePort_ID]
                                                OR (valueC.[SignalInterfacePort_ID] IS NULL AND ewh.[SignalInterfacePort_ID] IS NULL)
                                                OR ewh.[SignalInterfacePort_ID] IS NULL
                                            )
            JOIN [dbo].[Channel]        statusC ON statusC.[ParentChannel_ID] = valueC.[Channel_ID]
            JOIN [dbo].[ChannelKind]    cr      ON cr.[ChannelKind_ID] = statusC.[ChannelKind_ID]
                                               AND cr.[Name] = N'Status'
            JOIN [dbo].[Observation]   o       ON o.[Channel_ID] = statusC.[Channel_ID]
            JOIN [dbo].[Value]         v       ON v.[Observation_ID] = o.[Observation_ID]
            JOIN [dbo].[SensorStatusCode] sc   ON sc.StatusCodeID = CAST(v.Value AS INT)
            WHERE ewh.[Equipment_ID] = ?
              AND ewh.[ValidTo] IS NULL
              AND o.[Timestamp] BETWEEN ? AND ?
            ORDER BY o.[Timestamp]
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
        self, measurement_channel_id: int, t1: datetime, t2: datetime
    ) -> list[dict]:
        """Get status intervals for rendering (Query 4)."""
        cursor = self.conn.cursor()
        cursor.execute(
            f"""
            WITH StatusTransitions AS (
                SELECT TOP 1
                    o.[Timestamp] AS transition_time,
                    CAST(v.Value AS INT) AS status_code_id
                FROM [dbo].[Observation] o
                JOIN [dbo].[Value] v ON v.[Observation_ID] = o.[Observation_ID]
                WHERE o.[Channel_ID] = {_STATUS_CHANNEL_FOR_MEASUREMENT}
                  AND o.[Timestamp] <= ?
                ORDER BY o.[Timestamp] DESC

                UNION ALL

                SELECT
                    o.[Timestamp] AS transition_time,
                    CAST(v.Value AS INT) AS status_code_id
                FROM [dbo].[Observation] o
                JOIN [dbo].[Value] v ON v.[Observation_ID] = o.[Observation_ID]
                WHERE o.[Channel_ID] = {_STATUS_CHANNEL_FOR_MEASUREMENT}
                  AND o.[Timestamp] > ? AND o.[Timestamp] <= ?
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
            measurement_channel_id,  # sub-query for first UNION branch
            t1,
            measurement_channel_id,  # sub-query for second UNION branch
            t1,
            t2,
            t1,
            t1,
            t2,
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
                valueC.[Channel_ID] AS measurement_channel_id,
                p.[Parameter] AS measurement_parameter,
                NULL AS location_name,
                sc.StatusCodeID AS status_code_id,
                sc.StatusName AS status_name,
                sc.IsOperational AS is_operational,
                sc.Severity AS severity,
                latestStatus.[Timestamp] AS status_since
            FROM [dbo].[EquipmentWiringHistory] ewh
            JOIN [dbo].[vw_ChannelResolved] valueC  ON valueC.[SignalInterface_ID] = ewh.[SignalInterface_ID]
                                              AND (
                                                  valueC.[SignalInterfacePort_ID] = ewh.[SignalInterfacePort_ID]
                                                  OR (valueC.[SignalInterfacePort_ID] IS NULL AND ewh.[SignalInterfacePort_ID] IS NULL)
                                                  OR ewh.[SignalInterfacePort_ID] IS NULL
                                              )
            JOIN [dbo].[Parameter]      p       ON p.[Parameter_ID]        = valueC.[Parameter_ID]
            JOIN [dbo].[Channel]        statusC ON statusC.[ParentChannel_ID] = valueC.[Channel_ID]
            JOIN [dbo].[ChannelKind]    cr      ON cr.[ChannelKind_ID] = statusC.[ChannelKind_ID]
                                               AND cr.[Name] = N'Status'
            CROSS APPLY (
                SELECT TOP 1 o.[Timestamp], v.Value
                FROM [dbo].[Observation] o
                JOIN [dbo].[Value] v ON v.[Observation_ID] = o.[Observation_ID]
                WHERE o.[Channel_ID] = statusC.[Channel_ID]
                ORDER BY o.[Timestamp] DESC
            ) latestStatus
            JOIN dbo.SensorStatusCode sc ON sc.StatusCodeID = CAST(latestStatus.Value AS INT)
            WHERE ewh.[Equipment_ID] = ?
              AND ewh.[ValidTo] IS NULL
            ORDER BY p.[Parameter]
            """,
            equipment_id,
        )
        rows = cursor.fetchall()
        cursor.close()
        return [
            {
                "measurement_channel_id": row[0],
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
                o.[Timestamp] AS status_since
            FROM [dbo].[EquipmentWiringHistory] ewh
            JOIN [dbo].[vw_ChannelResolved] valueC  ON valueC.[SignalInterface_ID] = ewh.[SignalInterface_ID]
                                              AND (
                                                  valueC.[SignalInterfacePort_ID] = ewh.[SignalInterfacePort_ID]
                                                  OR (valueC.[SignalInterfacePort_ID] IS NULL AND ewh.[SignalInterfacePort_ID] IS NULL)
                                                  OR ewh.[SignalInterfacePort_ID] IS NULL
                                              )
            JOIN [dbo].[Channel]        statusC ON statusC.[ParentChannel_ID] = valueC.[Channel_ID]
            JOIN [dbo].[ChannelKind]    cr      ON cr.[ChannelKind_ID] = statusC.[ChannelKind_ID]
                                               AND cr.[Name] = N'Status'
            JOIN [dbo].[Observation]   o       ON o.[Channel_ID] = statusC.[Channel_ID]
            JOIN [dbo].[Value]         v       ON v.[Observation_ID] = o.[Observation_ID]
            JOIN [dbo].[SensorStatusCode] sc   ON sc.StatusCodeID = CAST(v.Value AS INT)
            WHERE ewh.[Equipment_ID] = ?
              AND ewh.[ValidTo] IS NULL
            ORDER BY o.[Timestamp] DESC
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
            "SELECT [Identifier] FROM dbo.Equipment WHERE Equipment_ID = ?",
            equipment_id,
        )
        row = cursor.fetchone()
        cursor.close()
        return row[0] if row else None

    def get_parameter_name(self, channel_id: int) -> Optional[str]:
        """Get parameter name for a Channel entry."""
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT p.[Parameter]
            FROM dbo.Channel c
            JOIN dbo.Parameter p ON p.Parameter_ID = c.Parameter_ID
            WHERE c.Channel_ID = ?
            """,
            channel_id,
        )
        row = cursor.fetchone()
        cursor.close()
        return row[0] if row else None

    def get_equipment_for_channel(self, channel_id: int) -> Optional[int]:
        """Get the currently-linked equipment ID for a Channel."""
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT ewh.[Equipment_ID]
            FROM [dbo].[vw_ChannelResolved] c
            JOIN [dbo].[EquipmentWiringHistory] ewh
              ON ewh.[SignalInterface_ID] = c.[SignalInterface_ID]
             AND (
                 ewh.[SignalInterfacePort_ID] = c.[SignalInterfacePort_ID]
                 OR (ewh.[SignalInterfacePort_ID] IS NULL AND c.[SignalInterfacePort_ID] IS NULL)
                 OR c.[SignalInterfacePort_ID] IS NULL
             )
             AND ewh.[ValidTo] IS NULL
            WHERE c.[Channel_ID] = ?
            """,
            channel_id,
        )
        row = cursor.fetchone()
        cursor.close()
        return row[0] if row else None

    def check_channel_exists(self, channel_id: int) -> bool:
        """Check if a Channel entry exists."""
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT 1 FROM dbo.Channel WHERE Channel_ID = ?",
            channel_id,
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
