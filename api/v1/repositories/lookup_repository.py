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
    cursor.execute(
        "SELECT [Laboratory_ID], [Name], [Site_ID], [Description] FROM [dbo].[Laboratory] ORDER BY [Name]"
    )
    return [
        {"laboratory_id": row[0], "name": row[1], "site_id": row[2], "description": row[3]}
        for row in cursor.fetchall()
    ]


def insert_laboratory(conn: pyodbc.Connection, name: str, site_id: int | None = None, description: str | None = None) -> dict:
    """Insert a new Laboratory row and return it."""
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO [dbo].[Laboratory] ([Name], [Site_ID], [Description])"
            " OUTPUT inserted.[Laboratory_ID], inserted.[Name], inserted.[Site_ID], inserted.[Description]"
            " VALUES (?, ?, ?)",
            name,
            site_id,
            description,
        )
        row = cursor.fetchone()
        conn.commit()
        return {"laboratory_id": row[0], "name": row[1], "site_id": row[2], "description": row[3]}
    except Exception:
        conn.rollback()
        raise


def update_laboratory(
    conn: pyodbc.Connection, laboratory_id: int, name: str, site_id: int | None = None, description: str | None = None
) -> dict | None:
    """Update a Laboratory row and return it, or None if not found."""
    cursor = conn.cursor()
    try:
        cursor.execute(
            "UPDATE [dbo].[Laboratory]"
            " SET [Name]=?, [Site_ID]=?, [Description]=?"
            " OUTPUT inserted.[Laboratory_ID], inserted.[Name], inserted.[Site_ID], inserted.[Description]"
            " WHERE [Laboratory_ID]=?",
            name,
            site_id,
            description,
            laboratory_id,
        )
        row = cursor.fetchone()
        conn.commit()
        if row is None:
            return None
        return {"laboratory_id": row[0], "name": row[1], "site_id": row[2], "description": row[3]}
    except Exception:
        conn.rollback()
        raise


def delete_laboratory(conn: pyodbc.Connection, laboratory_id: int) -> bool:
    """Delete a Laboratory row. Returns True if a row was deleted."""
    cursor = conn.cursor()
    try:
        cursor.execute(
            "DELETE FROM [dbo].[Laboratory] WHERE [Laboratory_ID]=?",
            laboratory_id,
        )
        conn.commit()
        return cursor.rowcount > 0
    except Exception:
        conn.rollback()
        raise


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


def get_all_persons(conn: pyodbc.Connection) -> list[dict]:
    """Return all persons with full fields."""
    cursor = conn.cursor()
    cursor.execute(
        "SELECT [Person_ID], [FirstName], [LastName], [Email], [Role], [Company], [Phone]"
        " FROM [dbo].[Person] ORDER BY [LastName], [FirstName]"
    )
    return [
        {
            "person_id": row[0],
            "first_name": row[1],
            "last_name": row[2],
            "email": row[3],
            "role": row[4],
            "company": row[5],
            "phone": row[6],
        }
        for row in cursor.fetchall()
    ]


# ---------------------------------------------------------------------------
# QualityCode
# ---------------------------------------------------------------------------


def get_quality_codes(conn: pyodbc.Connection) -> list[dict]:
    cursor = conn.cursor()
    cursor.execute(
        "SELECT [QualityCode_ID], [Name], [Description], [IsUsable]"
        " FROM [dbo].[QualityCode] ORDER BY [QualityCode_ID]"
    )
    return [
        {
            "quality_code_id": row[0],
            "name": row[1],
            "description": row[2],
            "is_usable": bool(row[3]),
        }
        for row in cursor.fetchall()
    ]


def insert_quality_code(
    conn: pyodbc.Connection, name: str, description: str | None, is_usable: bool
) -> dict:
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO [dbo].[QualityCode] ([Name], [Description], [IsUsable])"
            " OUTPUT inserted.[QualityCode_ID], inserted.[Name],"
            "        inserted.[Description], inserted.[IsUsable]"
            " VALUES (?, ?, ?)",
            name,
            description,
            1 if is_usable else 0,
        )
        row = cursor.fetchone()
        conn.commit()
        return {
            "quality_code_id": row[0],
            "name": row[1],
            "description": row[2],
            "is_usable": bool(row[3]),
        }
    except Exception:
        conn.rollback()
        raise


def update_quality_code(
    conn: pyodbc.Connection,
    qc_id: int,
    name: str,
    description: str | None,
    is_usable: bool,
) -> dict | None:
    cursor = conn.cursor()
    try:
        cursor.execute(
            "UPDATE [dbo].[QualityCode]"
            " SET [Name]=?, [Description]=?, [IsUsable]=?"
            " OUTPUT inserted.[QualityCode_ID], inserted.[Name],"
            "        inserted.[Description], inserted.[IsUsable]"
            " WHERE [QualityCode_ID]=?",
            name,
            description,
            1 if is_usable else 0,
            qc_id,
        )
        row = cursor.fetchone()
        conn.commit()
        if row is None:
            return None
        return {
            "quality_code_id": row[0],
            "name": row[1],
            "description": row[2],
            "is_usable": bool(row[3]),
        }
    except Exception:
        conn.rollback()
        raise


def delete_quality_code(conn: pyodbc.Connection, qc_id: int) -> bool:
    cursor = conn.cursor()
    try:
        cursor.execute(
            "DELETE FROM [dbo].[QualityCode] WHERE [QualityCode_ID]=?",
            qc_id,
        )
        conn.commit()
        return cursor.rowcount > 0
    except Exception:
        conn.rollback()
        raise


# ---------------------------------------------------------------------------
# SampleType
# ---------------------------------------------------------------------------


def get_sample_types(conn: pyodbc.Connection) -> list[dict]:
    cursor = conn.cursor()
    cursor.execute(
        "SELECT [SampleType_ID], [Name], [Description]"
        " FROM [dbo].[SampleType] ORDER BY [Name]"
    )
    return [
        {"sample_type_id": row[0], "name": row[1], "description": row[2]}
        for row in cursor.fetchall()
    ]


def insert_sample_type(
    conn: pyodbc.Connection, name: str, description: str | None
) -> dict:
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO [dbo].[SampleType] ([Name], [Description])"
            " OUTPUT inserted.[SampleType_ID], inserted.[Name], inserted.[Description]"
            " VALUES (?, ?)",
            name,
            description,
        )
        row = cursor.fetchone()
        conn.commit()
        return {"sample_type_id": row[0], "name": row[1], "description": row[2]}
    except Exception:
        conn.rollback()
        raise


def update_sample_type(
    conn: pyodbc.Connection, sample_type_id: int, name: str, description: str | None
) -> dict | None:
    cursor = conn.cursor()
    try:
        cursor.execute(
            "UPDATE [dbo].[SampleType]"
            " SET [Name]=?, [Description]=?"
            " OUTPUT inserted.[SampleType_ID], inserted.[Name], inserted.[Description]"
            " WHERE [SampleType_ID]=?",
            name,
            description,
            sample_type_id,
        )
        row = cursor.fetchone()
        conn.commit()
        if row is None:
            return None
        return {"sample_type_id": row[0], "name": row[1], "description": row[2]}
    except Exception:
        conn.rollback()
        raise


def delete_sample_type(conn: pyodbc.Connection, sample_type_id: int) -> bool:
    cursor = conn.cursor()
    try:
        cursor.execute(
            "DELETE FROM [dbo].[SampleType] WHERE [SampleType_ID]=?",
            sample_type_id,
        )
        conn.commit()
        return cursor.rowcount > 0
    except Exception:
        conn.rollback()
        raise


# ---------------------------------------------------------------------------
# SampleMethod
# ---------------------------------------------------------------------------


def get_sample_methods(conn: pyodbc.Connection) -> list[dict]:
    cursor = conn.cursor()
    cursor.execute(
        "SELECT [SampleMethod_ID], [Name], [Description]"
        " FROM [dbo].[SampleMethod] ORDER BY [Name]"
    )
    return [
        {"sample_method_id": row[0], "name": row[1], "description": row[2]}
        for row in cursor.fetchall()
    ]


def insert_sample_method(
    conn: pyodbc.Connection, name: str, description: str | None
) -> dict:
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO [dbo].[SampleMethod] ([Name], [Description])"
            " OUTPUT inserted.[SampleMethod_ID], inserted.[Name], inserted.[Description]"
            " VALUES (?, ?)",
            name,
            description,
        )
        row = cursor.fetchone()
        conn.commit()
        return {"sample_method_id": row[0], "name": row[1], "description": row[2]}
    except Exception:
        conn.rollback()
        raise


def update_sample_method(
    conn: pyodbc.Connection, sample_method_id: int, name: str, description: str | None
) -> dict | None:
    cursor = conn.cursor()
    try:
        cursor.execute(
            "UPDATE [dbo].[SampleMethod]"
            " SET [Name]=?, [Description]=?"
            " OUTPUT inserted.[SampleMethod_ID], inserted.[Name], inserted.[Description]"
            " WHERE [SampleMethod_ID]=?",
            name,
            description,
            sample_method_id,
        )
        row = cursor.fetchone()
        conn.commit()
        if row is None:
            return None
        return {"sample_method_id": row[0], "name": row[1], "description": row[2]}
    except Exception:
        conn.rollback()
        raise


def delete_sample_method(conn: pyodbc.Connection, sample_method_id: int) -> bool:
    cursor = conn.cursor()
    try:
        cursor.execute(
            "DELETE FROM [dbo].[SampleMethod] WHERE [SampleMethod_ID]=?",
            sample_method_id,
        )
        conn.commit()
        return cursor.rowcount > 0
    except Exception:
        conn.rollback()
        raise

