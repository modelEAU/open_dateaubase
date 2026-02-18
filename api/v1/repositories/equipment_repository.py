"""Data access for Equipment resources, events, and installations."""

from __future__ import annotations

from datetime import datetime

import pyodbc


def list_equipment(conn: pyodbc.Connection) -> list[dict]:
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT e.[Equipment_ID], e.[identifier], e.[Serial_number],
               e.[model_ID], em.[Equipment_model], em.[Manufacturer],
               e.[Owner], e.[Purchase_date]
        FROM [dbo].[Equipment] e
        LEFT JOIN [dbo].[EquipmentModel] em ON em.[Equipment_model_ID] = e.[model_ID]
        ORDER BY e.[Equipment_ID]
        """
    )
    return [
        {
            "equipment_id": row[0],
            "identifier": row[1],
            "serial_number": row[2],
            "model_id": row[3],
            "model_name": row[4],
            "manufacturer": row[5],
            "owner": row[6],
            "purchase_date": str(row[7]) if row[7] else None,
        }
        for row in cursor.fetchall()
    ]


def get_equipment_by_id(conn: pyodbc.Connection, equipment_id: int) -> dict | None:
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT e.[Equipment_ID], e.[identifier], e.[Serial_number],
               e.[model_ID], em.[Equipment_model], em.[Manufacturer],
               e.[Owner], e.[Purchase_date]
        FROM [dbo].[Equipment] e
        LEFT JOIN [dbo].[EquipmentModel] em ON em.[Equipment_model_ID] = e.[model_ID]
        WHERE e.[Equipment_ID] = ?
        """,
        equipment_id,
    )
    row = cursor.fetchone()
    if row is None:
        return None
    return {
        "equipment_id": row[0],
        "identifier": row[1],
        "serial_number": row[2],
        "model_id": row[3],
        "model_name": row[4],
        "manufacturer": row[5],
        "owner": row[6],
        "purchase_date": str(row[7]) if row[7] else None,
    }


def get_equipment_events(
    conn: pyodbc.Connection,
    equipment_id: int,
    from_dt: datetime | None,
    to_dt: datetime | None,
) -> list[dict]:
    params: list = [equipment_id]
    where = "WHERE ee.[Equipment_ID] = ?"
    if from_dt:
        where += " AND ee.[EventDateTimeStart] >= ?"
        params.append(from_dt)
    if to_dt:
        where += " AND ee.[EventDateTimeStart] <= ?"
        params.append(to_dt)

    cursor = conn.cursor()
    cursor.execute(
        f"""
        SELECT ee.[EquipmentEvent_ID], ee.[EquipmentEventType_ID],
               eet.[EventType_Name],
               ee.[EventDateTimeStart], ee.[EventDateTimeEnd],
               ee.[PerformedByPerson_ID],
               CONCAT(per.[First_name], ' ', per.[Last_name]) AS PersonName,
               ee.[Campaign_ID], c.[Name] AS CampaignName,
               ee.[Notes]
        FROM [dbo].[EquipmentEvent] ee
        LEFT JOIN [dbo].[EquipmentEventType] eet
            ON eet.[EquipmentEventType_ID] = ee.[EquipmentEventType_ID]
        LEFT JOIN [dbo].[Person] per ON per.[Person_ID] = ee.[PerformedByPerson_ID]
        LEFT JOIN [dbo].[Campaign] c  ON c.[Campaign_ID]  = ee.[Campaign_ID]
        {where}
        ORDER BY ee.[EventDateTimeStart]
        """,
        *params,
    )
    return [
        {
            "event_id": row[0],
            "event_type_id": row[1],
            "event_type_name": row[2],
            "start_datetime": row[3],
            "end_datetime": row[4],
            "performed_by_person_id": row[5],
            "performed_by_name": row[6],
            "campaign_id": row[7],
            "campaign_name": row[8],
            "notes": row[9],
        }
        for row in cursor.fetchall()
    ]


def get_equipment_installations(
    conn: pyodbc.Connection,
    equipment_id: int,
    from_dt: datetime | None,
    to_dt: datetime | None,
) -> list[dict]:
    params: list = [equipment_id]
    where = "WHERE ei.[Equipment_ID] = ?"
    if from_dt:
        where += " AND (ei.[RemovedDate] IS NULL OR ei.[RemovedDate] >= ?)"
        params.append(from_dt)
    if to_dt:
        where += " AND ei.[InstalledDate] <= ?"
        params.append(to_dt)

    cursor = conn.cursor()
    cursor.execute(
        f"""
        SELECT ei.[EquipmentInstallation_ID], ei.[Sampling_point_ID],
               sp.[Name] AS LocationName,
               ei.[InstalledDate], ei.[RemovedDate],
               ei.[Campaign_ID], c.[Name] AS CampaignName,
               ei.[Notes]
        FROM [dbo].[EquipmentInstallation] ei
        LEFT JOIN [dbo].[SamplingPoints] sp ON sp.[Sampling_point_ID] = ei.[Sampling_point_ID]
        LEFT JOIN [dbo].[Campaign]        c  ON c.[Campaign_ID]        = ei.[Campaign_ID]
        {where}
        ORDER BY ei.[InstalledDate]
        """,
        *params,
    )
    return [
        {
            "installation_id": row[0],
            "sampling_location_id": row[1],
            "location_name": row[2],
            "installed_date": row[3],
            "removed_date": row[4],
            "campaign_id": row[5],
            "campaign_name": row[6],
            "notes": row[7],
        }
        for row in cursor.fetchall()
    ]
