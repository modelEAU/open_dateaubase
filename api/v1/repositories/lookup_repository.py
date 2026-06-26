"""Lookup queries for dropdown/reference data across all ingest forms."""

from __future__ import annotations

import pyodbc


# ---------------------------------------------------------------------------
# Generic CRUD for (ID, Name, Description) "kind" vocabulary tables.
# ponytail: table/id_col/id_key are hardcoded literals passed by the named
# wrappers below — never user input — so f-string interpolation is injection-safe;
# the actual values stay parameterized with ?.
# ---------------------------------------------------------------------------


def _list_kinds(conn: pyodbc.Connection, table: str, id_col: str, id_key: str) -> list[dict]:
    cursor = conn.cursor()
    cursor.execute(
        f"SELECT [{id_col}], [Name], [Description]"
        f" FROM [dbo].[{table}] ORDER BY [{id_col}]"
    )
    return [
        {id_key: row[0], "name": row[1], "description": row[2]}
        for row in cursor.fetchall()
    ]


def _insert_kind(
    conn: pyodbc.Connection, table: str, id_col: str, id_key: str,
    name: str, description: str | None = None,
) -> dict:
    cursor = conn.cursor()
    try:
        cursor.execute(
            f"INSERT INTO [dbo].[{table}] ([Name], [Description])"
            f" OUTPUT inserted.[{id_col}], inserted.[Name], inserted.[Description]"
            f" VALUES (?, ?)",
            name,
            description,
        )
        row = cursor.fetchone()
        conn.commit()
        return {id_key: row[0], "name": row[1], "description": row[2]}
    except Exception:
        conn.rollback()
        raise


def _update_kind(
    conn: pyodbc.Connection, table: str, id_col: str, id_key: str,
    kind_id: int, name: str, description: str | None = None,
) -> dict | None:
    cursor = conn.cursor()
    try:
        cursor.execute(
            f"UPDATE [dbo].[{table}]"
            f" SET [Name]=?, [Description]=?"
            f" OUTPUT inserted.[{id_col}], inserted.[Name], inserted.[Description]"
            f" WHERE [{id_col}]=?",
            name,
            description,
            kind_id,
        )
        row = cursor.fetchone()
        conn.commit()
        if row is None:
            return None
        return {id_key: row[0], "name": row[1], "description": row[2]}
    except Exception:
        conn.rollback()
        raise


def _delete_kind(conn: pyodbc.Connection, table: str, id_col: str, kind_id: int) -> bool:
    cursor = conn.cursor()
    try:
        cursor.execute(f"DELETE FROM [dbo].[{table}] WHERE [{id_col}]=?", kind_id)
        conn.commit()
        return cursor.rowcount > 0
    except Exception:
        conn.rollback()
        raise


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
               COALESCE(sp.SamplingPoint, 'Point ' + CAST(sp.SamplingPoint_ID AS NVARCHAR)) AS Label
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
        "SELECT DataProvenanceKind_ID, Name, Description FROM [dbo].[DataProvenanceKind] ORDER BY DataProvenanceKind_ID"
    )
    return [
        {"data_provenance_kind_id": row[0], "name": row[1], "description": row[2]}
        for row in cursor.fetchall()
    ]


def get_data_provenance_kind_by_id(
    conn: pyodbc.Connection, provenance_id: int
) -> dict | None:
    """Return a single data provenance kind by ID."""
    cursor = conn.cursor()
    cursor.execute(
        "SELECT DataProvenanceKind_ID, Name, Description FROM [dbo].[DataProvenanceKind] WHERE DataProvenanceKind_ID = ?",
        provenance_id,
    )
    row = cursor.fetchone()
    if row:
        return {"data_provenance_kind_id": row[0], "name": row[1], "description": row[2]}
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
        "SELECT [Person_ID], [FirstName], [LastName], [Company], [Role],"
        " [AssignedFunctions], [Email], [Phone], [Linkedin], [Website]"
        " FROM [dbo].[Person] ORDER BY [LastName], [FirstName]"
    )
    return [
        {
            "person_id": row[0],
            "first_name": row[1],
            "last_name": row[2],
            "company": row[3],
            "role": row[4],
            "assigned_functions": row[5],
            "email": row[6],
            "phone": row[7],
            "linkedin": row[8],
            "website": row[9],
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
    return _list_kinds(conn, "BinKind", "BinKind_ID", "bin_kind_id")


# ---------------------------------------------------------------------------
# ChannelKind (read-only — fixed seeded IDs)
# ---------------------------------------------------------------------------


def get_channel_kinds(conn: pyodbc.Connection) -> list[dict]:
    return _list_kinds(conn, "ChannelKind", "ChannelKind_ID", "channel_kind_id")


# ---------------------------------------------------------------------------
# OperationKind (read-only — classifies a ProcessingStep / ChannelTrait, ADR 0005)
# ---------------------------------------------------------------------------


def get_operation_kinds(conn: pyodbc.Connection) -> list[dict]:
    return _list_kinds(conn, "OperationKind", "OperationKind_ID", "operation_kind_id")


# ---------------------------------------------------------------------------
# CampaignKind
# ---------------------------------------------------------------------------


def insert_campaign_kind(conn: pyodbc.Connection, name: str, description: str | None = None) -> dict:
    return _insert_kind(conn, "CampaignKind", "CampaignKind_ID", "campaign_kind_id", name, description)


def update_campaign_kind(
    conn: pyodbc.Connection, campaign_kind_id: int, name: str, description: str | None = None
) -> dict | None:
    return _update_kind(
        conn, "CampaignKind", "CampaignKind_ID", "campaign_kind_id",
        campaign_kind_id, name, description,
    )


def delete_campaign_kind(conn: pyodbc.Connection, campaign_kind_id: int) -> bool:
    return _delete_kind(conn, "CampaignKind", "CampaignKind_ID", campaign_kind_id)


# EquipmentEventKind CRUD lives in equipment_repository (the live path); the
# duplicate copies that used to be here were dead and have been removed.


# ---------------------------------------------------------------------------
# ProcedureKind
# ---------------------------------------------------------------------------


def get_procedure_kinds(conn: pyodbc.Connection) -> list[dict]:
    return _list_kinds(conn, "ProcedureKind", "ProcedureKind_ID", "procedure_kind_id")


def insert_procedure_kind(conn: pyodbc.Connection, name: str, description: str | None = None) -> dict:
    return _insert_kind(conn, "ProcedureKind", "ProcedureKind_ID", "procedure_kind_id", name, description)


def update_procedure_kind(
    conn: pyodbc.Connection, procedure_kind_id: int, name: str, description: str | None = None
) -> dict | None:
    return _update_kind(
        conn, "ProcedureKind", "ProcedureKind_ID", "procedure_kind_id",
        procedure_kind_id, name, description,
    )


def delete_procedure_kind(conn: pyodbc.Connection, procedure_kind_id: int) -> bool:
    return _delete_kind(conn, "ProcedureKind", "ProcedureKind_ID", procedure_kind_id)


# ---------------------------------------------------------------------------
# Procedures
# ---------------------------------------------------------------------------


def get_procedures(conn: pyodbc.Connection) -> list[dict]:
    cursor = conn.cursor()
    cursor.execute(
        "SELECT [Procedure_ID], ProcedureName, ProcedureKind_ID, [Description], ProcedureLocation"
        " FROM [dbo].[Procedures] ORDER BY ProcedureName"
    )
    return [
        {
            "procedure_id": row[0],
            "procedure_name": row[1],
            "procedure_kind_id": row[2],
            "description": row[3],
            "procedure_location": row[4],
        }
        for row in cursor.fetchall()
    ]


def insert_procedure(
    conn: pyodbc.Connection,
    procedure_name: str | None,
    procedure_kind_id: int | None,
    description: str | None,
    procedure_location: str | None,
) -> dict:
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO [dbo].[Procedures]"
            " (ProcedureName, ProcedureKind_ID, [Description], ProcedureLocation)"
            " OUTPUT inserted.[Procedure_ID], inserted.ProcedureName,"
            "        inserted.ProcedureKind_ID, inserted.[Description], inserted.ProcedureLocation"
            " VALUES (?, ?, ?, ?)",
            procedure_name,
            procedure_kind_id,
            description,
            procedure_location,
        )
        row = cursor.fetchone()
        conn.commit()
        return {
            "procedure_id": row[0],
            "procedure_name": row[1],
            "procedure_kind_id": row[2],
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
    procedure_kind_id: int | None,
    description: str | None,
    procedure_location: str | None,
) -> dict | None:
    cursor = conn.cursor()
    try:
        cursor.execute(
            "UPDATE [dbo].[Procedures]"
            " SET ProcedureName=?, ProcedureKind_ID=?, [Description]=?, ProcedureLocation=?"
            " OUTPUT inserted.[Procedure_ID], inserted.ProcedureName,"
            "        inserted.ProcedureKind_ID, inserted.[Description], inserted.ProcedureLocation"
            " WHERE [Procedure_ID]=?",
            procedure_name,
            procedure_kind_id,
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
            "procedure_kind_id": row[2],
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
        " ConcentrationTime, ImperviousSurface, ParentWatershed_ID, GeometryGeoJSON"
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
            "parent_watershed_id": row[6],
            "geometry_geojson": row[7],
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
    parent_watershed_id: int | None = None,
    geometry_geojson: str | None = None,
) -> dict:
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO [dbo].[Watershed]"
            " (Name, [Description], SurfaceArea, ConcentrationTime, ImperviousSurface,"
            "  ParentWatershed_ID, GeometryGeoJSON)"
            " OUTPUT inserted.[Watershed_ID], inserted.Name, inserted.[Description],"
            "        inserted.SurfaceArea, inserted.ConcentrationTime, inserted.ImperviousSurface,"
            "        inserted.ParentWatershed_ID, inserted.GeometryGeoJSON"
            " VALUES (?, ?, ?, ?, ?, ?, ?)",
            name,
            description,
            surface_area,
            concentration_time,
            impervious_surface,
            parent_watershed_id,
            geometry_geojson,
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
            "parent_watershed_id": row[6],
            "geometry_geojson": row[7],
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
    parent_watershed_id: int | None = None,
    geometry_geojson: str | None = None,
) -> dict | None:
    cursor = conn.cursor()
    try:
        cursor.execute(
            "UPDATE [dbo].[Watershed]"
            " SET Name=?, [Description]=?, SurfaceArea=?,"
            "     ConcentrationTime=?, ImperviousSurface=?,"
            "     ParentWatershed_ID=?, GeometryGeoJSON=?"
            " OUTPUT inserted.[Watershed_ID], inserted.Name, inserted.[Description],"
            "        inserted.SurfaceArea, inserted.ConcentrationTime, inserted.ImperviousSurface,"
            "        inserted.ParentWatershed_ID, inserted.GeometryGeoJSON"
            " WHERE [Watershed_ID]=?",
            name,
            description,
            surface_area,
            concentration_time,
            impervious_surface,
            parent_watershed_id,
            geometry_geojson,
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
            "parent_watershed_id": row[6],
            "geometry_geojson": row[7],
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


def _land_use_row(row) -> dict:
    return {
        "watershed_id": row[0],
        "commercial": row[1],
        "green_spaces": row[2],
        "industrial": row[3],
        "institutional": row[4],
        "residential": row[5],
        "agricultural": row[6],
        "recreational": row[7],
    }


def get_land_use(conn: pyodbc.Connection, watershed_id: int) -> dict | None:
    cursor = conn.cursor()
    cursor.execute(
        "SELECT [Watershed_ID], [Commercial], [GreenSpaces], [Industrial],"
        "       [Institutional], [Residential], [Agricultural], [Recreational]"
        " FROM [dbo].[LandUse] WHERE [Watershed_ID]=?",
        watershed_id,
    )
    row = cursor.fetchone()
    return _land_use_row(row) if row else None


def upsert_land_use(
    conn: pyodbc.Connection,
    watershed_id: int,
    commercial: float | None,
    green_spaces: float | None,
    industrial: float | None,
    institutional: float | None,
    residential: float | None,
    agricultural: float | None,
    recreational: float | None,
) -> dict:
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT 1 FROM [dbo].[LandUse] WHERE [Watershed_ID]=?", watershed_id
        )
        exists = cursor.fetchone() is not None
        if exists:
            cursor.execute(
                "UPDATE [dbo].[LandUse]"
                " SET [Commercial]=?, [GreenSpaces]=?, [Industrial]=?,"
                "     [Institutional]=?, [Residential]=?, [Agricultural]=?, [Recreational]=?"
                " WHERE [Watershed_ID]=?",
                commercial, green_spaces, industrial,
                institutional, residential, agricultural, recreational,
                watershed_id,
            )
        else:
            cursor.execute(
                "INSERT INTO [dbo].[LandUse]"
                " ([Watershed_ID], [Commercial], [GreenSpaces], [Industrial],"
                "  [Institutional], [Residential], [Agricultural], [Recreational])"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                watershed_id, commercial, green_spaces, industrial,
                institutional, residential, agricultural, recreational,
            )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    return get_land_use(conn, watershed_id)  # type: ignore[return-value]


# ---------------------------------------------------------------------------
# DataAcquisitionSystemKind (read-only seed vocabulary)
# ---------------------------------------------------------------------------


def get_tags_lookup(conn: pyodbc.Connection, das_id: int) -> list[dict]:
    """Return SignalInterface names for a DAS, for strict-mode tag dropdowns."""
    cursor = conn.cursor()
    cursor.execute(
        "SELECT [SignalInterface_ID], [Name]"
        " FROM [dbo].[SignalInterface]"
        " WHERE [DataAcquisitionSystem_ID] = ?"
        " ORDER BY [Name]",
        das_id,
    )
    return [{"signal_interface_id": row[0], "name": row[1]} for row in cursor.fetchall()]


def get_das_kinds(conn: pyodbc.Connection) -> list[dict]:
    return _list_kinds(
        conn, "DataAcquisitionSystemKind", "DataAcquisitionSystemKind_ID", "das_kind_id"
    )


# ---------------------------------------------------------------------------
# ControllerKind (read-only seed vocabulary)
# ---------------------------------------------------------------------------


def get_controller_kinds(conn: pyodbc.Connection) -> list[dict]:
    return _list_kinds(conn, "ControllerKind", "ControllerKind_ID", "controller_kind_id")
