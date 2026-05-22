"""Data access for Equipment resources, events, and installations."""

from __future__ import annotations

from datetime import datetime

import pyodbc


def list_equipment(conn: pyodbc.Connection) -> list[dict]:
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT e.[Equipment_ID], e.[Identifier], e.[SerialNumber],
               e.[EquipmentModel_ID], em.[EquipmentModel], em.[Manufacturer],
               e.[Owner], e.[PurchaseDate]
        FROM [dbo].[Equipment] e
        LEFT JOIN [dbo].[EquipmentModel] em ON em.[EquipmentModel_ID] = e.[EquipmentModel_ID]
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
        SELECT e.[Equipment_ID], e.[Identifier], e.[SerialNumber],
               e.[EquipmentModel_ID], em.[EquipmentModel], em.[Manufacturer],
               e.[Owner], e.[PurchaseDate]
        FROM [dbo].[Equipment] e
        LEFT JOIN [dbo].[EquipmentModel] em ON em.[EquipmentModel_ID] = e.[EquipmentModel_ID]
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


def insert_equipment(conn: pyodbc.Connection, data: dict) -> dict | None:
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO [dbo].[Equipment] ([Identifier], [SerialNumber], [EquipmentModel_ID], [Owner], [PurchaseDate])"
        " VALUES (?, ?, ?, ?, ?)",
        data.get("identifier"),
        data.get("serial_number"),
        data.get("model_id"),
        data.get("owner"),
        data.get("purchase_date"),
    )
    cursor.execute("SELECT @@IDENTITY")
    _row = cursor.fetchone()
    assert _row is not None
    new_id = int(_row[0])
    conn.commit()
    return get_equipment_by_id(conn, new_id)


def update_equipment(
    conn: pyodbc.Connection, equipment_id: int, data: dict
) -> dict | None:
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE [dbo].[Equipment]"
        " SET [Identifier]=?, [SerialNumber]=?, [EquipmentModel_ID]=?, [Owner]=?, [PurchaseDate]=?"
        " WHERE [Equipment_ID]=?",
        data.get("identifier"),
        data.get("serial_number"),
        data.get("model_id"),
        data.get("owner"),
        data.get("purchase_date"),
        equipment_id,
    )
    conn.commit()
    return get_equipment_by_id(conn, equipment_id)


def delete_equipment(conn: pyodbc.Connection, equipment_id: int) -> bool:
    cursor = conn.cursor()
    cursor.execute("DELETE FROM [dbo].[Equipment] WHERE [Equipment_ID]=?", equipment_id)
    conn.commit()
    return cursor.rowcount > 0


def patch_equipment(
    conn: pyodbc.Connection, equipment_id: int, data: dict
) -> dict | None:
    """Partial update of equipment - only updates fields that are present in data."""
    existing = get_equipment_by_id(conn, equipment_id)
    if existing is None:
        return None

    fields = []
    values = []

    if "identifier" in data:
        fields.append("[Identifier]=?")
        values.append(data.get("identifier"))
    if "serial_number" in data:
        fields.append("[SerialNumber]=?")
        values.append(data.get("serial_number"))
    if "model_id" in data:
        fields.append("[EquipmentModel_ID]=?")
        values.append(data.get("model_id"))
    if "owner" in data:
        fields.append("[Owner]=?")
        values.append(data.get("owner"))
    if "purchase_date" in data:
        fields.append("[PurchaseDate]=?")
        values.append(data.get("purchase_date"))

    if not fields:
        return existing

    values.append(equipment_id)
    cursor = conn.cursor()
    cursor.execute(
        f"UPDATE [dbo].[Equipment] SET {', '.join(fields)} WHERE [Equipment_ID]=?",
        *values,
    )
    conn.commit()
    return get_equipment_by_id(conn, equipment_id)


def get_models_lookup(conn: pyodbc.Connection) -> list[dict]:
    """Return equipment models for dropdowns."""
    cursor = conn.cursor()
    cursor.execute(
        "SELECT [EquipmentModel_ID], [EquipmentModel], [Manufacturer] FROM [dbo].[EquipmentModel] ORDER BY [Manufacturer], [EquipmentModel]"
    )
    return [
        {"model_id": row[0], "model_name": row[1], "manufacturer": row[2]}
        for row in cursor.fetchall()
    ]


def list_equipment_models(conn: pyodbc.Connection) -> list[dict]:
    """Return all equipment models (full rows)."""
    cursor = conn.cursor()
    cursor.execute(
        "SELECT [EquipmentModel_ID], [EquipmentModel], [Method], [Functions], [Manufacturer], [ManualLocation]"
        " FROM [dbo].[EquipmentModel] ORDER BY [EquipmentModel_ID]"
    )
    return [
        {
            "model_id": row[0],
            "equipment_model": row[1],
            "method": row[2],
            "functions": row[3],
            "manufacturer": row[4],
            "manual_location": row[5],
        }
        for row in cursor.fetchall()
    ]


def get_equipment_model_by_id(conn: pyodbc.Connection, model_id: int) -> dict | None:
    cursor = conn.cursor()
    cursor.execute(
        "SELECT [EquipmentModel_ID], [EquipmentModel], [Method], [Functions], [Manufacturer], [ManualLocation]"
        " FROM [dbo].[EquipmentModel] WHERE [EquipmentModel_ID]=?",
        model_id,
    )
    row = cursor.fetchone()
    if row is None:
        return None
    return {
        "model_id": row[0],
        "equipment_model": row[1],
        "method": row[2],
        "functions": row[3],
        "manufacturer": row[4],
        "manual_location": row[5],
    }


def insert_equipment_model(conn: pyodbc.Connection, data: dict) -> dict | None:
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO [dbo].[EquipmentModel] ([EquipmentModel], [Method], [Functions], [Manufacturer], [ManualLocation])"
        " VALUES (?, ?, ?, ?, ?)",
        data.get("equipment_model"),
        data.get("method"),
        data.get("functions"),
        data.get("manufacturer"),
        data.get("manual_location"),
    )
    cursor.execute("SELECT @@IDENTITY")
    _row = cursor.fetchone()
    assert _row is not None
    new_id = int(_row[0])
    conn.commit()
    return get_equipment_model_by_id(conn, new_id)


def update_equipment_model(conn: pyodbc.Connection, model_id: int, data: dict) -> dict | None:
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE [dbo].[EquipmentModel]"
        " SET [EquipmentModel]=?, [Method]=?, [Functions]=?, [Manufacturer]=?, [ManualLocation]=?"
        " WHERE [EquipmentModel_ID]=?",
        data.get("equipment_model"),
        data.get("method"),
        data.get("functions"),
        data.get("manufacturer"),
        data.get("manual_location"),
        model_id,
    )
    conn.commit()
    return get_equipment_model_by_id(conn, model_id)


def delete_equipment_model(conn: pyodbc.Connection, model_id: int) -> bool:
    cursor = conn.cursor()
    cursor.execute("DELETE FROM [dbo].[EquipmentModel] WHERE [EquipmentModel_ID]=?", model_id)
    conn.commit()
    return cursor.rowcount > 0


def get_equipment_lookup(conn: pyodbc.Connection) -> list[dict]:
    """Return all equipment for dropdowns (id + identifier)."""
    cursor = conn.cursor()
    cursor.execute(
        "SELECT [Equipment_ID], [Identifier] FROM [dbo].[Equipment] ORDER BY [Identifier]"
    )
    return [{"equipment_id": row[0], "identifier": row[1]} for row in cursor.fetchall()]


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
        SELECT ee.[EquipmentEvent_ID], ee.[EquipmentEventKind_ID],
               eet.[Name],
               ee.[IsInstantaneous],
               ee.[EventDateTimeStart], ee.[EventDateTimeEnd],
               ee.[PerformedByPerson_ID],
               CONCAT(per.[FirstName], ' ', per.[LastName]) AS PerformedByName,
               ee.[RecordedByPerson_ID],
               CONCAT(rec.[FirstName], ' ', rec.[LastName]) AS RecordedByName,
               ee.[Notes]
        FROM [dbo].[EquipmentEvent] ee
        LEFT JOIN [dbo].[EquipmentEventKind] eet
            ON eet.[EquipmentEventKind_ID] = ee.[EquipmentEventKind_ID]
        LEFT JOIN [dbo].[Person] per ON per.[Person_ID] = ee.[PerformedByPerson_ID]
        LEFT JOIN [dbo].[Person] rec ON rec.[Person_ID] = ee.[RecordedByPerson_ID]
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
            "is_instantaneous": bool(row[3]),
            "start_datetime": row[4],
            "end_datetime": row[5],
            "performed_by_person_id": row[6],
            "performed_by_name": row[7],
            "recorded_by_person_id": row[8],
            "recorded_by_name": row[9],
            "notes": row[10],
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
        SELECT ei.[Installation_ID], ei.[SamplingPoint_ID],
               sp.[SamplingPoint] AS LocationName,
               ei.[InstalledDate], ei.[RemovedDate],
               ei.[Campaign_ID], c.[Name] AS CampaignName,
               ei.[Notes]
        FROM [dbo].[EquipmentInstallation] ei
        LEFT JOIN [dbo].[SamplingPoint] sp ON sp.[SamplingPoint_ID] = ei.[SamplingPoint_ID]
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


def get_equipment_event_kinds(conn: pyodbc.Connection) -> list[dict]:
    """Return all EquipmentEventKind rows for dropdowns."""
    cursor = conn.cursor()
    cursor.execute(
        "SELECT [EquipmentEventKind_ID], [Name], [Description] FROM [dbo].[EquipmentEventKind] ORDER BY [Name]"
    )
    return [
        {"event_type_id": row[0], "event_type_name": row[1], "description": row[2]}
        for row in cursor.fetchall()
    ]


def insert_equipment_event_kind(conn: pyodbc.Connection, name: str) -> dict:
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO [dbo].[EquipmentEventKind] ([Name])"
            " OUTPUT inserted.[EquipmentEventKind_ID], inserted.[Name]"
            " VALUES (?)",
            name,
        )
        row = cursor.fetchone()
        assert row is not None
        conn.commit()
        return {"event_type_id": row[0], "event_type_name": row[1]}
    except Exception:
        conn.rollback()
        raise


def update_equipment_event_kind(conn: pyodbc.Connection, event_kind_id: int, name: str) -> dict | None:
    cursor = conn.cursor()
    try:
        cursor.execute(
            "UPDATE [dbo].[EquipmentEventKind]"
            " SET [Name]=?"
            " OUTPUT inserted.[EquipmentEventKind_ID], inserted.[Name]"
            " WHERE [EquipmentEventKind_ID]=?",
            name,
            event_kind_id,
        )
        row = cursor.fetchone()
        conn.commit()
        if row is None:
            return None
        return {"event_type_id": row[0], "event_type_name": row[1]}
    except Exception:
        conn.rollback()
        raise


def delete_equipment_event_kind(conn: pyodbc.Connection, event_kind_id: int) -> bool:
    cursor = conn.cursor()
    try:
        cursor.execute(
            "DELETE FROM [dbo].[EquipmentEventKind] WHERE [EquipmentEventKind_ID]=?",
            event_kind_id,
        )
        conn.commit()
        return cursor.rowcount > 0
    except Exception:
        conn.rollback()
        raise


def insert_equipment_event(conn: pyodbc.Connection, data: dict) -> dict:
    """Insert a new EquipmentEvent row and return the created record."""
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO [dbo].[EquipmentEvent]
            ([Equipment_ID], [EquipmentEventKind_ID], [IsInstantaneous],
             [EventDateTimeStart], [EventDateTimeEnd],
             [PerformedByPerson_ID], [RecordedByPerson_ID], [Notes])
        OUTPUT INSERTED.[EquipmentEvent_ID]
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        data["equipment_id"],
        data["event_type_id"],
        int(data.get("is_instantaneous", False)),
        data["start_datetime"],
        data.get("end_datetime"),
        data.get("performed_by_person_id"),
        data.get("recorded_by_person_id"),
        data.get("notes"),
    )
    _id_row = cursor.fetchone()
    assert _id_row is not None
    event_id = _id_row[0]
    conn.commit()

    # Re-fetch with joins for the full response
    cursor.execute(
        """
        SELECT ee.[EquipmentEvent_ID], ee.[EquipmentEventKind_ID],
               eet.[Name],
               ee.[IsInstantaneous],
               ee.[EventDateTimeStart], ee.[EventDateTimeEnd],
               ee.[PerformedByPerson_ID],
               CONCAT(per.[FirstName], ' ', per.[LastName]) AS PerformedByName,
               ee.[RecordedByPerson_ID],
               CONCAT(rec.[FirstName], ' ', rec.[LastName]) AS RecordedByName,
               ee.[Notes]
        FROM [dbo].[EquipmentEvent] ee
        LEFT JOIN [dbo].[EquipmentEventKind] eet ON eet.[EquipmentEventKind_ID] = ee.[EquipmentEventKind_ID]
        LEFT JOIN [dbo].[Person] per ON per.[Person_ID] = ee.[PerformedByPerson_ID]
        LEFT JOIN [dbo].[Person] rec ON rec.[Person_ID] = ee.[RecordedByPerson_ID]
        WHERE ee.[EquipmentEvent_ID] = ?
        """,
        event_id,
    )
    row = cursor.fetchone()
    assert row is not None
    return {
        "event_id": row[0],
        "event_type_id": row[1],
        "event_type_name": row[2],
        "is_instantaneous": bool(row[3]),
        "start_datetime": row[4],
        "end_datetime": row[5],
        "performed_by_person_id": row[6],
        "performed_by_name": row[7],
        "recorded_by_person_id": row[8],
        "recorded_by_name": row[9],
        "notes": row[10],
    }


# ---------------------------------------------------------------------------
# Commission / Decommission
# ---------------------------------------------------------------------------


def _find_event_kind_id_by_name(conn: pyodbc.Connection, name: str) -> int | None:
    cursor = conn.cursor()
    cursor.execute(
        "SELECT [EquipmentEventKind_ID] FROM [dbo].[EquipmentEventKind]"
        " WHERE [Name] = ?",
        name,
    )
    row = cursor.fetchone()
    return row[0] if row else None


def commission_equipment(
    conn: pyodbc.Connection,
    equipment_id: int,
    notes: str | None = None,
    performed_by_person_id: int | None = None,
) -> dict:
    """Set Equipment.IsActive = 1 and record a Commissioning EquipmentEvent.

    Returns ``{"equipment_id", "is_active", "equipment_event_id"}``.
    """
    event_type_id = _find_event_kind_id_by_name(conn, "Commissioning")
    if event_type_id is None:
        raise RuntimeError(
            "EquipmentEventKind 'Commissioning' is missing from seed data."
        )

    cursor = conn.cursor()
    cursor.execute(
        "UPDATE [dbo].[Equipment] SET [IsActive] = 1 WHERE [Equipment_ID] = ?",
        equipment_id,
    )
    if cursor.rowcount == 0:
        conn.rollback()
        raise ValueError(f"Equipment {equipment_id} not found.")

    cursor.execute(
        """
        INSERT INTO [dbo].[EquipmentEvent]
            ([Equipment_ID], [EquipmentEventKind_ID], [EventDateTimeStart],
             [PerformedByPerson_ID], [Notes])
        OUTPUT INSERTED.[EquipmentEvent_ID]
        VALUES (?, ?, SYSUTCDATETIME(), ?, ?)
        """,
        equipment_id,
        event_type_id,
        performed_by_person_id,
        notes,
    )
    _row = cursor.fetchone()
    assert _row is not None
    event_id: int = _row[0]
    conn.commit()
    return {"equipment_id": equipment_id, "is_active": True, "equipment_event_id": event_id}


def decommission_equipment(
    conn: pyodbc.Connection,
    equipment_id: int,
    notes: str | None = None,
    performed_by_person_id: int | None = None,
) -> dict:
    """Set Equipment.IsActive = 0 and record a Decommissioning EquipmentEvent.

    Returns ``{"equipment_id", "is_active", "equipment_event_id"}``.
    """
    event_type_id = _find_event_kind_id_by_name(conn, "Decommissioning")
    if event_type_id is None:
        raise RuntimeError(
            "EquipmentEventKind 'Decommissioning' is missing from seed data."
        )

    cursor = conn.cursor()
    cursor.execute(
        "UPDATE [dbo].[Equipment] SET [IsActive] = 0 WHERE [Equipment_ID] = ?",
        equipment_id,
    )
    if cursor.rowcount == 0:
        conn.rollback()
        raise ValueError(f"Equipment {equipment_id} not found.")

    cursor.execute(
        """
        INSERT INTO [dbo].[EquipmentEvent]
            ([Equipment_ID], [EquipmentEventKind_ID], [EventDateTimeStart],
             [PerformedByPerson_ID], [Notes])
        OUTPUT INSERTED.[EquipmentEvent_ID]
        VALUES (?, ?, SYSUTCDATETIME(), ?, ?)
        """,
        equipment_id,
        event_type_id,
        performed_by_person_id,
        notes,
    )
    _row = cursor.fetchone()
    assert _row is not None
    event_id: int = _row[0]
    conn.commit()
    return {"equipment_id": equipment_id, "is_active": False, "equipment_event_id": event_id}


# ---------------------------------------------------------------------------
# EquipmentModelHasParameter
# ---------------------------------------------------------------------------


def list_model_parameters(conn: pyodbc.Connection, model_id: int) -> list[dict]:
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT p.[Parameter_ID], p.[Parameter] AS ParameterName, p.[Description]
        FROM [dbo].[EquipmentModelHasParameter] emp
        JOIN [dbo].[Parameter] p ON p.[Parameter_ID] = emp.[Parameter_ID]
        WHERE emp.[EquipmentModel_ID] = ?
        ORDER BY p.[Parameter]
        """,
        model_id,
    )
    return [
        {"model_id": model_id, "parameter_id": row[0], "parameter_name": row[1], "description": row[2]}
        for row in cursor.fetchall()
    ]


def add_model_parameter(conn: pyodbc.Connection, model_id: int, parameter_id: int) -> dict:
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO [dbo].[EquipmentModelHasParameter] ([EquipmentModel_ID], [Parameter_ID])"
            " VALUES (?, ?)",
            model_id,
            parameter_id,
        )
        conn.commit()
    except Exception as exc:
        conn.rollback()
        if "PRIMARY KEY" in str(exc) or "UNIQUE" in str(exc) or "Violation" in str(exc):
            raise ValueError("Already linked") from exc
        raise
    return {"model_id": model_id, "parameter_id": parameter_id}


def remove_model_parameter(conn: pyodbc.Connection, model_id: int, parameter_id: int) -> bool:
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM [dbo].[EquipmentModelHasParameter]"
        " WHERE [EquipmentModel_ID] = ? AND [Parameter_ID] = ?",
        model_id,
        parameter_id,
    )
    conn.commit()
    return cursor.rowcount > 0


# ---------------------------------------------------------------------------
# EquipmentModelHasProcedures
# ---------------------------------------------------------------------------


def list_model_procedures(conn: pyodbc.Connection, model_id: int) -> list[dict]:
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT p.[Procedure_ID], p.[ProcedureName]
        FROM [dbo].[EquipmentModelHasProcedures] emp
        JOIN [dbo].[Procedures] p ON p.[Procedure_ID] = emp.[Procedure_ID]
        WHERE emp.[EquipmentModel_ID] = ?
        ORDER BY p.[ProcedureName]
        """,
        model_id,
    )
    return [
        {"model_id": model_id, "procedure_id": row[0], "procedure_name": row[1]}
        for row in cursor.fetchall()
    ]


def add_model_procedure(conn: pyodbc.Connection, model_id: int, procedure_id: int) -> dict:
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO [dbo].[EquipmentModelHasProcedures] ([EquipmentModel_ID], [Procedure_ID])"
            " VALUES (?, ?)",
            model_id,
            procedure_id,
        )
        conn.commit()
    except Exception as exc:
        conn.rollback()
        if "PRIMARY KEY" in str(exc) or "UNIQUE" in str(exc) or "Violation" in str(exc):
            raise ValueError("Already linked") from exc
        raise
    return {"model_id": model_id, "procedure_id": procedure_id}


def remove_model_procedure(conn: pyodbc.Connection, model_id: int, procedure_id: int) -> bool:
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM [dbo].[EquipmentModelHasProcedures]"
        " WHERE [EquipmentModel_ID] = ? AND [Procedure_ID] = ?",
        model_id,
        procedure_id,
    )
    conn.commit()
    return cursor.rowcount > 0
