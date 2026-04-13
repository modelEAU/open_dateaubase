"""Lookup queries for dropdown/reference data across all ingest forms."""

from __future__ import annotations

import pyodbc


def get_units_lookup(conn: pyodbc.Connection) -> list[dict]:
    cursor = conn.cursor()
    cursor.execute("SELECT Unit_ID, Unit FROM [dbo].[Unit] ORDER BY Unit_ID")
    return [{"unit_id": row[0], "unit": row[1]} for row in cursor.fetchall()]


def insert_unit(conn: pyodbc.Connection, unit: str) -> dict:
    cursor = conn.cursor()
    cursor.execute("INSERT INTO [dbo].[Unit] ([Unit]) VALUES (?)", unit)
    cursor.execute("SELECT @@IDENTITY")
    new_id = int(cursor.fetchone()[0])
    conn.commit()
    return {"unit_id": new_id, "unit": unit}


def update_unit(conn: pyodbc.Connection, unit_id: int, unit: str) -> dict | None:
    cursor = conn.cursor()
    cursor.execute("UPDATE [dbo].[Unit] SET [Unit]=? WHERE [Unit_ID]=?", unit, unit_id)
    conn.commit()
    if cursor.rowcount == 0:
        return None
    return {"unit_id": unit_id, "unit": unit}


def delete_unit(conn: pyodbc.Connection, unit_id: int) -> bool:
    cursor = conn.cursor()
    cursor.execute("DELETE FROM [dbo].[Unit] WHERE [Unit_ID]=?", unit_id)
    conn.commit()
    return cursor.rowcount > 0


def get_laboratories_lookup(conn: pyodbc.Connection) -> list[dict]:
    cursor = conn.cursor()
    cursor.execute("SELECT Laboratory_ID, Name FROM [dbo].[Laboratory] ORDER BY Name")
    return [{"laboratory_id": row[0], "name": row[1]} for row in cursor.fetchall()]


def get_procedures_lookup(conn: pyodbc.Connection) -> list[dict]:
    cursor = conn.cursor()
    cursor.execute(
        "SELECT Procedure_ID, ProcedureName FROM [dbo].[Procedures] ORDER BY ProcedureName"
    )
    return [
        {"procedure_id": row[0], "procedure_name": row[1]} for row in cursor.fetchall()
    ]


def get_samples_lookup(conn: pyodbc.Connection) -> list[dict]:
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT s.Sample_ID,
               COALESCE(s.Description, 'Sample ' + CAST(s.Sample_ID AS NVARCHAR)) AS Label,
               s.SampleDateTimeStart
        FROM [dbo].[Sample] s
        ORDER BY s.SampleDateTimeStart DESC
        """
    )
    return [
        {
            "sample_id": row[0],
            "label": row[1],
            "sample_date": str(row[2]) if row[2] else None,
        }
        for row in cursor.fetchall()
    ]


def get_sampling_points_lookup(conn: pyodbc.Connection) -> list[dict]:
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT sp.SamplingPoint_ID,
               COALESCE(sp.SamplingPoint, 'Point ' + CAST(sp.SamplingPoint_ID AS NVARCHAR))
                 + ' \u2014 ' + COALESCE(sp.SamplingLocation, '') AS Label
        FROM [dbo].[SamplingPoint] sp
        ORDER BY sp.SamplingPoint
        """
    )
    return [{"sampling_point_id": row[0], "label": row[1]} for row in cursor.fetchall()]


def get_equipment_events_lookup(conn: pyodbc.Connection) -> list[dict]:
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT ee.EquipmentEvent_ID,
               et.EquipmentEventType_Name + ' \u2014 ' + e.Identifier
                 + ' (' + CONVERT(NVARCHAR, ee.EventDateTimeStart, 120) + ')' AS Label
        FROM [dbo].[EquipmentEvent] ee
        JOIN [dbo].[EquipmentEventType] et
          ON et.EquipmentEventType_ID = ee.EquipmentEventType_ID
        JOIN [dbo].[Equipment] e ON e.Equipment_ID = ee.Equipment_ID
        ORDER BY ee.EventDateTimeStart DESC
        """
    )
    return [
        {"equipment_event_id": row[0], "label": row[1]} for row in cursor.fetchall()
    ]


def get_data_provenance_lookup(conn: pyodbc.Connection) -> list[dict]:
    """Return all data provenance types for dropdowns."""
    cursor = conn.cursor()
    cursor.execute(
        "SELECT DataProvenance_ID, DataProvenance_Name FROM [dbo].[DataProvenance] ORDER BY DataProvenance_ID"
    )
    return [
        {"data_provenance_id": row[0], "data_provenance_name": row[1]}
        for row in cursor.fetchall()
    ]


def get_data_provenance_by_id(
    conn: pyodbc.Connection, provenance_id: int
) -> dict | None:
    """Return a single data provenance by ID."""
    cursor = conn.cursor()
    cursor.execute(
        "SELECT DataProvenance_ID, DataProvenance_Name FROM [dbo].[DataProvenance] WHERE DataProvenance_ID = ?",
        provenance_id,
    )
    row = cursor.fetchone()
    if row:
        return {"data_provenance_id": row[0], "data_provenance_name": row[1]}
    return None


def get_persons_lookup(conn: pyodbc.Connection) -> list[dict]:
    """Return all persons as {person_id, label} for dropdowns."""
    cursor = conn.cursor()
    cursor.execute(
        "SELECT [Person_ID], [FirstName], [LastName]"
        " FROM [dbo].[Person]"
        " ORDER BY [LastName], [FirstName]"
    )
    rows = cursor.fetchall()
    return [
        {
            "person_id": row[0],
            "label": f"{row[1] or ''} {row[2] or ''}".strip() or f"Person {row[0]}",
        }
        for row in rows
    ]

