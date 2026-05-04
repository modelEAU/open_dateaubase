"""Lookup queries for dropdown/reference data across all ingest forms."""

from __future__ import annotations

import pyodbc


def get_unit_by_id(conn: pyodbc.Connection, unit_id: int) -> dict | None:
    cursor = conn.cursor()
    cursor.execute(
        "SELECT [Unit_ID], [Unit], [QUDT_IRI], [UnitVector], [SI_Multiplier], [SI_Offset]"
        " FROM [dbo].[Unit] WHERE [Unit_ID] = ?",
        unit_id,
    )
    row = cursor.fetchone()
    if row is None:
        return None
    return {
        "unit_id": row[0],
        "unit": row[1],
        "qudt_iri": row[2],
        "unit_vector": row[3],
        "si_multiplier": row[4],
        "si_offset": row[5],
    }


def get_units_valid_for_parameter(conn: pyodbc.Connection, parameter_id: int) -> list[dict]:
    cursor = conn.cursor()
    cursor.execute(
        "SELECT u.[Unit_ID], u.[Unit], u.[QUDT_IRI], u.[UnitVector], u.[SI_Multiplier], u.[SI_Offset]"
        " FROM [dbo].[Unit] u"
        " JOIN [dbo].[ParameterHasUnit] phu ON phu.[Unit_ID] = u.[Unit_ID]"
        " WHERE phu.[Parameter_ID] = ?"
        " ORDER BY u.[Unit_ID]",
        parameter_id,
    )
    return [
        {
            "unit_id": row[0],
            "unit": row[1],
            "qudt_iri": row[2],
            "unit_vector": row[3],
            "si_multiplier": row[4],
            "si_offset": row[5],
        }
        for row in cursor.fetchall()
    ]


def add_parameter_unit(conn: pyodbc.Connection, parameter_id: int, unit_id: int) -> dict:
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO [dbo].[ParameterHasUnit] ([Parameter_ID], [Unit_ID]) VALUES (?, ?)",
            parameter_id,
            unit_id,
        )
        conn.commit()
    except Exception as exc:
        conn.rollback()
        if "PRIMARY KEY" in str(exc) or "UNIQUE" in str(exc) or "Violation" in str(exc):
            raise ValueError("Already linked") from exc
        raise
    return {"parameter_id": parameter_id, "unit_id": unit_id}


def remove_parameter_unit(conn: pyodbc.Connection, parameter_id: int, unit_id: int) -> bool:
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM [dbo].[ParameterHasUnit] WHERE [Parameter_ID] = ? AND [Unit_ID] = ?",
        parameter_id,
        unit_id,
    )
    conn.commit()
    return cursor.rowcount > 0


def get_units_lookup(conn: pyodbc.Connection) -> list[dict]:
    cursor = conn.cursor()
    cursor.execute(
        "SELECT [Unit_ID], [Unit], [QUDT_IRI], [UnitVector] FROM [dbo].[Unit] ORDER BY [Unit_ID]"
    )
    return [
        {"unit_id": row[0], "unit": row[1], "qudt_iri": row[2], "unit_vector": row[3]}
        for row in cursor.fetchall()
    ]


def insert_unit(conn: pyodbc.Connection, unit: str, qudt_iri: str | None = None, unit_vector: str | None = None) -> dict:
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO [dbo].[Unit] ([Unit], [QUDT_IRI], [UnitVector]) VALUES (?, ?, ?)",
        unit,
        qudt_iri,
        unit_vector,
    )
    cursor.execute("SELECT @@IDENTITY")
    new_id = int(cursor.fetchone()[0])
    conn.commit()
    return {"unit_id": new_id, "unit": unit, "qudt_iri": qudt_iri, "unit_vector": unit_vector}


def update_unit(conn: pyodbc.Connection, unit_id: int, unit: str, qudt_iri: str | None = None, unit_vector: str | None = None) -> dict | None:
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE [dbo].[Unit] SET [Unit]=?, [QUDT_IRI]=?, [UnitVector]=? WHERE [Unit_ID]=?",
        unit,
        qudt_iri,
        unit_vector,
        unit_id,
    )
    conn.commit()
    if cursor.rowcount == 0:
        return None
    return {"unit_id": unit_id, "unit": unit, "qudt_iri": qudt_iri, "unit_vector": unit_vector}


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
        {
            "laboratory_id": row[0],
            "name": row[1],
            "site_id": row[2],
            "description": row[3],
        }
        for row in cursor.fetchall()
    ]


def insert_laboratory(
    conn: pyodbc.Connection,
    name: str,
    site_id: int | None = None,
    description: str | None = None,
) -> dict:
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
        return {
            "laboratory_id": row[0],
            "name": row[1],
            "site_id": row[2],
            "description": row[3],
        }
    except Exception:
        conn.rollback()
        raise


def update_laboratory(
    conn: pyodbc.Connection,
    laboratory_id: int,
    name: str,
    site_id: int | None = None,
    description: str | None = None,
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
        return {
            "laboratory_id": row[0],
            "name": row[1],
            "site_id": row[2],
            "description": row[3],
        }
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
               et.Name + ' \u2014 ' + e.Identifier
                 + ' (' + CONVERT(NVARCHAR, ee.EventDateTimeStart, 120) + ')' AS Label
        FROM [dbo].[EquipmentEvent] ee
        JOIN [dbo].[EquipmentEventKind] et
          ON et.EquipmentEventKind_ID = ee.EquipmentEventKind_ID
        JOIN [dbo].[Equipment] e ON e.Equipment_ID = ee.Equipment_ID
        ORDER BY ee.EventDateTimeStart DESC
        """
    )
    return [
        {"equipment_event_id": row[0], "label": row[1]} for row in cursor.fetchall()
    ]


def get_data_provenance_kind_lookup(conn: pyodbc.Connection) -> list[dict]:
    """Return all data provenance kinds for dropdowns."""
    cursor = conn.cursor()
    cursor.execute(
        "SELECT DataProvenanceKind_ID, Name FROM [dbo].[DataProvenanceKind] ORDER BY DataProvenanceKind_ID"
    )
    return [
        {"data_provenance_kind_id": row[0], "name": row[1]}
        for row in cursor.fetchall()
    ]


def get_data_provenance_kind_by_id(
    conn: pyodbc.Connection, provenance_id: int
) -> dict | None:
    """Return a single data provenance kind by ID."""
    cursor = conn.cursor()
    cursor.execute(
        "SELECT DataProvenanceKind_ID, Name FROM [dbo].[DataProvenanceKind] WHERE DataProvenanceKind_ID = ?",
        provenance_id,
    )
    row = cursor.fetchone()
    if row:
        return {"data_provenance_kind_id": row[0], "name": row[1]}
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
# SampleKind
# ---------------------------------------------------------------------------


def get_sample_kinds(conn: pyodbc.Connection) -> list[dict]:
    cursor = conn.cursor()
    cursor.execute(
        "SELECT [SampleKind_ID], [Name], [Description]"
        " FROM [dbo].[SampleKind] ORDER BY [Name]"
    )
    return [
        {"sample_kind_id": row[0], "name": row[1], "description": row[2]}
        for row in cursor.fetchall()
    ]


def insert_sample_kind(
    conn: pyodbc.Connection, name: str, description: str | None
) -> dict:
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO [dbo].[SampleKind] ([Name], [Description])"
            " OUTPUT inserted.[SampleKind_ID], inserted.[Name], inserted.[Description]"
            " VALUES (?, ?)",
            name,
            description,
        )
        row = cursor.fetchone()
        conn.commit()
        return {"sample_kind_id": row[0], "name": row[1], "description": row[2]}
    except Exception:
        conn.rollback()
        raise


def update_sample_kind(
    conn: pyodbc.Connection, sample_kind_id: int, name: str, description: str | None
) -> dict | None:
    cursor = conn.cursor()
    try:
        cursor.execute(
            "UPDATE [dbo].[SampleKind]"
            " SET [Name]=?, [Description]=?"
            " OUTPUT inserted.[SampleKind_ID], inserted.[Name], inserted.[Description]"
            " WHERE [SampleKind_ID]=?",
            name,
            description,
            sample_kind_id,
        )
        row = cursor.fetchone()
        conn.commit()
        if row is None:
            return None
        return {"sample_kind_id": row[0], "name": row[1], "description": row[2]}
    except Exception:
        conn.rollback()
        raise


def delete_sample_kind(conn: pyodbc.Connection, sample_kind_id: int) -> bool:
    cursor = conn.cursor()
    try:
        cursor.execute(
            "DELETE FROM [dbo].[SampleKind] WHERE [SampleKind_ID]=?",
            sample_kind_id,
        )
        conn.commit()
        return cursor.rowcount > 0
    except Exception:
        conn.rollback()
        raise


# ---------------------------------------------------------------------------
# SampleCollectionKind
# ---------------------------------------------------------------------------


def get_sample_collection_kinds(conn: pyodbc.Connection) -> list[dict]:
    cursor = conn.cursor()
    cursor.execute(
        "SELECT [SampleCollectionKind_ID], [Name], [Description]"
        " FROM [dbo].[SampleCollectionKind] ORDER BY [Name]"
    )
    return [
        {"sample_collection_kind_id": row[0], "name": row[1], "description": row[2]}
        for row in cursor.fetchall()
    ]


def insert_sample_collection_kind(
    conn: pyodbc.Connection, name: str, description: str | None
) -> dict:
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO [dbo].[SampleCollectionKind] ([Name], [Description])"
            " OUTPUT inserted.[SampleCollectionKind_ID], inserted.[Name], inserted.[Description]"
            " VALUES (?, ?)",
            name,
            description,
        )
        row = cursor.fetchone()
        conn.commit()
        return {"sample_collection_kind_id": row[0], "name": row[1], "description": row[2]}
    except Exception:
        conn.rollback()
        raise


def update_sample_collection_kind(
    conn: pyodbc.Connection, sample_collection_kind_id: int, name: str, description: str | None
) -> dict | None:
    cursor = conn.cursor()
    try:
        cursor.execute(
            "UPDATE [dbo].[SampleCollectionKind]"
            " SET [Name]=?, [Description]=?"
            " OUTPUT inserted.[SampleCollectionKind_ID], inserted.[Name], inserted.[Description]"
            " WHERE [SampleCollectionKind_ID]=?",
            name,
            description,
            sample_collection_kind_id,
        )
        row = cursor.fetchone()
        conn.commit()
        if row is None:
            return None
        return {"sample_collection_kind_id": row[0], "name": row[1], "description": row[2]}
    except Exception:
        conn.rollback()
        raise


def delete_sample_collection_kind(conn: pyodbc.Connection, sample_collection_kind_id: int) -> bool:
    cursor = conn.cursor()
    try:
        cursor.execute(
            "DELETE FROM [dbo].[SampleCollectionKind] WHERE [SampleCollectionKind_ID]=?",
            sample_collection_kind_id,
        )
        conn.commit()
        return cursor.rowcount > 0
    except Exception:
        conn.rollback()
        raise


# ---------------------------------------------------------------------------
# BinKind (read-only — fixed seeded IDs)
# ---------------------------------------------------------------------------


def get_bin_kinds(conn: pyodbc.Connection) -> list[dict]:
    cursor = conn.cursor()
    cursor.execute(
        "SELECT [BinKind_ID], [Name], [Description] FROM [dbo].[BinKind] ORDER BY [BinKind_ID]"
    )
    return [
        {"bin_kind_id": row[0], "name": row[1], "description": row[2]}
        for row in cursor.fetchall()
    ]


# ---------------------------------------------------------------------------
# SignalInterfaceKind
# ---------------------------------------------------------------------------


def get_signal_interface_kinds(conn: pyodbc.Connection) -> list[dict]:
    cursor = conn.cursor()
    cursor.execute(
        "SELECT [SignalInterfaceKind_ID], [Name], [Description]"
        " FROM [dbo].[SignalInterfaceKind] ORDER BY [SignalInterfaceKind_ID]"
    )
    return [
        {"signal_interface_kind_id": row[0], "name": row[1], "description": row[2]}
        for row in cursor.fetchall()
    ]


def insert_signal_interface_kind(
    conn: pyodbc.Connection, name: str, description: str | None
) -> dict:
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO [dbo].[SignalInterfaceKind] ([Name], [Description])"
            " OUTPUT inserted.[SignalInterfaceKind_ID], inserted.[Name], inserted.[Description]"
            " VALUES (?, ?)",
            name,
            description,
        )
        row = cursor.fetchone()
        conn.commit()
        return {
            "signal_interface_kind_id": row[0],
            "name": row[1],
            "description": row[2],
        }
    except Exception:
        conn.rollback()
        raise


def update_signal_interface_kind(
    conn: pyodbc.Connection,
    signal_interface_kind_id: int,
    name: str,
    description: str | None,
) -> dict | None:
    cursor = conn.cursor()
    try:
        cursor.execute(
            "UPDATE [dbo].[SignalInterfaceKind]"
            " SET [Name]=?, [Description]=?"
            " OUTPUT inserted.[SignalInterfaceKind_ID], inserted.[Name], inserted.[Description]"
            " WHERE [SignalInterfaceKind_ID]=?",
            name,
            description,
            signal_interface_kind_id,
        )
        row = cursor.fetchone()
        conn.commit()
        if row is None:
            return None
        return {
            "signal_interface_kind_id": row[0],
            "name": row[1],
            "description": row[2],
        }
    except Exception:
        conn.rollback()
        raise


def delete_signal_interface_kind(
    conn: pyodbc.Connection, signal_interface_kind_id: int
) -> bool:
    cursor = conn.cursor()
    try:
        cursor.execute(
            "DELETE FROM [dbo].[SignalInterfaceKind] WHERE [SignalInterfaceKind_ID]=?",
            signal_interface_kind_id,
        )
        conn.commit()
        return cursor.rowcount > 0
    except Exception:
        conn.rollback()
        raise


# ---------------------------------------------------------------------------
# SignalInterfacePortKind (read-only — fixed seeded IDs)
# ---------------------------------------------------------------------------


def get_signal_interface_port_kinds(conn: pyodbc.Connection) -> list[dict]:
    cursor = conn.cursor()
    cursor.execute(
        "SELECT [SignalInterfacePortKind_ID], [Name], [Description]"
        " FROM [dbo].[SignalInterfacePortKind] ORDER BY [SignalInterfacePortKind_ID]"
    )
    return [
        {"signal_interface_port_kind_id": row[0], "name": row[1], "description": row[2]}
        for row in cursor.fetchall()
    ]


# ---------------------------------------------------------------------------
# ChannelKind (read-only — fixed seeded IDs)
# ---------------------------------------------------------------------------


def get_channel_kinds(conn: pyodbc.Connection) -> list[dict]:
    cursor = conn.cursor()
    cursor.execute(
        "SELECT [ChannelKind_ID], [Name], [Description]"
        " FROM [dbo].[ChannelKind] ORDER BY [ChannelKind_ID]"
    )
    return [
        {"channel_kind_id": row[0], "name": row[1], "description": row[2]}
        for row in cursor.fetchall()
    ]


# ---------------------------------------------------------------------------
# ProcessingKind (read-only — tightly coupled to Channel)
# ---------------------------------------------------------------------------


def get_processing_kinds(conn: pyodbc.Connection) -> list[dict]:
    cursor = conn.cursor()
    cursor.execute(
        "SELECT [ProcessingKind_ID], [Name], [Description] FROM [dbo].[ProcessingKind] ORDER BY [ProcessingKind_ID]"
    )
    return [
        {"processing_kind_id": row[0], "name": row[1], "description": row[2]} for row in cursor.fetchall()
    ]


# ---------------------------------------------------------------------------
# CampaignKind
# ---------------------------------------------------------------------------


def insert_campaign_kind(conn: pyodbc.Connection, name: str, description: str | None = None) -> dict:
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO [dbo].[CampaignKind] ([Name], [Description])"
            " OUTPUT inserted.[CampaignKind_ID], inserted.[Name], inserted.[Description]"
            " VALUES (?, ?)",
            name,
            description,
        )
        row = cursor.fetchone()
        conn.commit()
        return {"campaign_kind_id": row[0], "name": row[1], "description": row[2]}
    except Exception:
        conn.rollback()
        raise


def update_campaign_kind(
    conn: pyodbc.Connection, campaign_kind_id: int, name: str, description: str | None = None
) -> dict | None:
    cursor = conn.cursor()
    try:
        cursor.execute(
            "UPDATE [dbo].[CampaignKind]"
            " SET [Name]=?, [Description]=?"
            " OUTPUT inserted.[CampaignKind_ID], inserted.[Name], inserted.[Description]"
            " WHERE [CampaignKind_ID]=?",
            name,
            description,
            campaign_kind_id,
        )
        row = cursor.fetchone()
        conn.commit()
        if row is None:
            return None
        return {"campaign_kind_id": row[0], "name": row[1], "description": row[2]}
    except Exception:
        conn.rollback()
        raise


def delete_campaign_kind(conn: pyodbc.Connection, campaign_kind_id: int) -> bool:
    cursor = conn.cursor()
    try:
        cursor.execute(
            "DELETE FROM [dbo].[CampaignKind] WHERE [CampaignKind_ID]=?",
            campaign_kind_id,
        )
        conn.commit()
        return cursor.rowcount > 0
    except Exception:
        conn.rollback()
        raise


# ---------------------------------------------------------------------------
# EquipmentEventKind
# ---------------------------------------------------------------------------


def get_equipment_event_kinds(conn: pyodbc.Connection) -> list[dict]:
    cursor = conn.cursor()
    cursor.execute(
        "SELECT [EquipmentEventKind_ID], [Name], [Description]"
        " FROM [dbo].[EquipmentEventKind] ORDER BY [EquipmentEventKind_ID]"
    )
    return [
        {"equipment_event_kind_id": row[0], "name": row[1], "description": row[2]} for row in cursor.fetchall()
    ]


def insert_equipment_event_kind(conn: pyodbc.Connection, name: str, description: str | None = None) -> dict:
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO [dbo].[EquipmentEventKind] ([Name], [Description])"
            " OUTPUT inserted.[EquipmentEventKind_ID], inserted.[Name], inserted.[Description]"
            " VALUES (?, ?)",
            name,
            description,
        )
        row = cursor.fetchone()
        conn.commit()
        return {"equipment_event_kind_id": row[0], "name": row[1], "description": row[2]}
    except Exception:
        conn.rollback()
        raise


def update_equipment_event_kind(
    conn: pyodbc.Connection, equipment_event_kind_id: int, name: str, description: str | None = None
) -> dict | None:
    cursor = conn.cursor()
    try:
        cursor.execute(
            "UPDATE [dbo].[EquipmentEventKind]"
            " SET [Name]=?, [Description]=?"
            " OUTPUT inserted.[EquipmentEventKind_ID], inserted.[Name], inserted.[Description]"
            " WHERE [EquipmentEventKind_ID]=?",
            name,
            description,
            equipment_event_kind_id,
        )
        row = cursor.fetchone()
        conn.commit()
        if row is None:
            return None
        return {"equipment_event_kind_id": row[0], "name": row[1], "description": row[2]}
    except Exception:
        conn.rollback()
        raise


def delete_equipment_event_kind(
    conn: pyodbc.Connection, equipment_event_kind_id: int
) -> bool:
    cursor = conn.cursor()
    try:
        cursor.execute(
            "DELETE FROM [dbo].[EquipmentEventKind] WHERE [EquipmentEventKind_ID]=?",
            equipment_event_kind_id,
        )
        conn.commit()
        return cursor.rowcount > 0
    except Exception:
        conn.rollback()
        raise


# ---------------------------------------------------------------------------
# Procedures
# ---------------------------------------------------------------------------


def get_procedures(conn: pyodbc.Connection) -> list[dict]:
    cursor = conn.cursor()
    cursor.execute(
        "SELECT [Procedure_ID], ProcedureName, ProcedureType, [Description], ProcedureLocation"
        " FROM [dbo].[Procedures] ORDER BY ProcedureName"
    )
    return [
        {
            "procedure_id": row[0],
            "procedure_name": row[1],
            "procedure_type": row[2],
            "description": row[3],
            "procedure_location": row[4],
        }
        for row in cursor.fetchall()
    ]


def insert_procedure(
    conn: pyodbc.Connection,
    procedure_name: str | None,
    procedure_type: str | None,
    description: str | None,
    procedure_location: str | None,
) -> dict:
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO [dbo].[Procedures]"
            " (ProcedureName, ProcedureType, [Description], ProcedureLocation)"
            " OUTPUT inserted.[Procedure_ID], inserted.ProcedureName,"
            "        inserted.ProcedureType, inserted.[Description], inserted.ProcedureLocation"
            " VALUES (?, ?, ?, ?)",
            procedure_name,
            procedure_type,
            description,
            procedure_location,
        )
        row = cursor.fetchone()
        conn.commit()
        return {
            "procedure_id": row[0],
            "procedure_name": row[1],
            "procedure_type": row[2],
            "description": row[3],
            "procedure_location": row[4],
        }
    except Exception:
        conn.rollback()
        raise


def update_procedure(
    conn: pyodbc.Connection,
    procedure_id: int,
    procedure_name: str | None,
    procedure_type: str | None,
    description: str | None,
    procedure_location: str | None,
) -> dict | None:
    cursor = conn.cursor()
    try:
        cursor.execute(
            "UPDATE [dbo].[Procedures]"
            " SET ProcedureName=?, ProcedureType=?, [Description]=?, ProcedureLocation=?"
            " OUTPUT inserted.[Procedure_ID], inserted.ProcedureName,"
            "        inserted.ProcedureType, inserted.[Description], inserted.ProcedureLocation"
            " WHERE [Procedure_ID]=?",
            procedure_name,
            procedure_type,
            description,
            procedure_location,
            procedure_id,
        )
        row = cursor.fetchone()
        conn.commit()
        if row is None:
            return None
        return {
            "procedure_id": row[0],
            "procedure_name": row[1],
            "procedure_type": row[2],
            "description": row[3],
            "procedure_location": row[4],
        }
    except Exception:
        conn.rollback()
        raise


def delete_procedure(conn: pyodbc.Connection, procedure_id: int) -> bool:
    cursor = conn.cursor()
    try:
        cursor.execute(
            "DELETE FROM [dbo].[Procedures] WHERE [Procedure_ID]=?", procedure_id
        )
        conn.commit()
        return cursor.rowcount > 0
    except Exception:
        conn.rollback()
        raise


# ---------------------------------------------------------------------------
# Watershed
# ---------------------------------------------------------------------------


def get_watersheds(conn: pyodbc.Connection) -> list[dict]:
    cursor = conn.cursor()
    cursor.execute(
        "SELECT [Watershed_ID], Name, [Description], SurfaceArea,"
        " ConcentrationTime, ImperviousSurface"
        " FROM [dbo].[Watershed] ORDER BY Name"
    )
    return [
        {
            "watershed_id": row[0],
            "name": row[1],
            "description": row[2],
            "surface_area": row[3],
            "concentration_time": row[4],
            "impervious_surface": row[5],
        }
        for row in cursor.fetchall()
    ]


def insert_watershed(
    conn: pyodbc.Connection,
    name: str | None,
    description: str | None,
    surface_area: float | None,
    concentration_time: int | None,
    impervious_surface: float | None,
) -> dict:
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO [dbo].[Watershed]"
            " (Name, [Description], SurfaceArea, ConcentrationTime, ImperviousSurface)"
            " OUTPUT inserted.[Watershed_ID], inserted.Name, inserted.[Description],"
            "        inserted.SurfaceArea, inserted.ConcentrationTime, inserted.ImperviousSurface"
            " VALUES (?, ?, ?, ?, ?)",
            name,
            description,
            surface_area,
            concentration_time,
            impervious_surface,
        )
        row = cursor.fetchone()
        conn.commit()
        return {
            "watershed_id": row[0],
            "name": row[1],
            "description": row[2],
            "surface_area": row[3],
            "concentration_time": row[4],
            "impervious_surface": row[5],
        }
    except Exception:
        conn.rollback()
        raise


def update_watershed(
    conn: pyodbc.Connection,
    watershed_id: int,
    name: str | None,
    description: str | None,
    surface_area: float | None,
    concentration_time: int | None,
    impervious_surface: float | None,
) -> dict | None:
    cursor = conn.cursor()
    try:
        cursor.execute(
            "UPDATE [dbo].[Watershed]"
            " SET Name=?, [Description]=?, SurfaceArea=?,"
            "     ConcentrationTime=?, ImperviousSurface=?"
            " OUTPUT inserted.[Watershed_ID], inserted.Name, inserted.[Description],"
            "        inserted.SurfaceArea, inserted.ConcentrationTime, inserted.ImperviousSurface"
            " WHERE [Watershed_ID]=?",
            name,
            description,
            surface_area,
            concentration_time,
            impervious_surface,
            watershed_id,
        )
        row = cursor.fetchone()
        conn.commit()
        if row is None:
            return None
        return {
            "watershed_id": row[0],
            "name": row[1],
            "description": row[2],
            "surface_area": row[3],
            "concentration_time": row[4],
            "impervious_surface": row[5],
        }
    except Exception:
        conn.rollback()
        raise


def delete_watershed(conn: pyodbc.Connection, watershed_id: int) -> bool:
    cursor = conn.cursor()
    try:
        cursor.execute(
            "DELETE FROM [dbo].[Watershed] WHERE [Watershed_ID]=?", watershed_id
        )
        conn.commit()
        return cursor.rowcount > 0
    except Exception:
        conn.rollback()
        raise
