"""Bridge between open_dateaubase and the metEAUdata processing library.

Provides two public functions:

* ``load_signal_context`` — pull full resolved context for a MetaData row
  so that metEAUdata can reconstruct a DataProvenance object without manual
  metadata_id strings.

* ``record_processing`` — persist a ProcessingStep + DataLineage rows after
  metEAUdata has applied a transformation, closing the full provenance loop.

Both functions accept a plain pyodbc connection and are transport-agnostic:
the caller (e.g. OpenDateaubaseAdapter in meteaudata) manages connection
lifecycle and transaction boundaries.
"""

from __future__ import annotations

import json
from datetime import datetime


def load_signal_context(metadata_id: int, conn) -> dict:
    """Load the full resolved context for a MetaData row.

    Queries MetaData and JOIN-resolves all foreign keys (Site via
    SamplingPoints, SamplingPoints, Equipment, Parameter, Unit, Campaign,
    CampaignType, DataProvenance, Laboratory, Person-as-analyst,
    Person-as-contact, Purpose, Project).

    Args:
        metadata_id: Primary key of the MetaData row.
        conn: A pyodbc connection to open_dateaubase.

    Returns:
        A dict with the following keys (all nullable values may be None):
          metadata_id, parameter, unit, location, site, equipment, campaign,
          laboratory, analyst, contact, data_provenance, processing_degree,
          project, purpose

    Raises:
        KeyError: If the metadata_id does not exist.
    """
    sql = """
        SELECT
            m.[Metadata_ID],
            -- Parameter
            p.[Parameter_ID],
            p.[Name]               AS [ParameterName],
            -- Unit
            u.[Unit_ID],
            u.[Name]               AS [UnitName],
            -- SamplingPoint (location)
            sp.[Sampling_point_ID],
            sp.[Name]              AS [LocationName],
            -- Site
            s.[Site_ID],
            s.[Name]               AS [SiteName],
            -- Equipment
            e.[Equipment_ID],
            e.[identifier]         AS [EquipmentName],
            -- Campaign
            c.[Campaign_ID],
            c.[Name]               AS [CampaignName],
            ct.[Name]              AS [CampaignTypeName],
            -- DataProvenance
            dp.[Name]              AS [DataProvenanceName],
            -- Laboratory
            lab.[Laboratory_ID],
            lab.[Name]             AS [LaboratoryName],
            -- Analyst
            an.[Person_ID]         AS [AnalystID],
            CONCAT(an.[First_name], ' ', an.[Last_name]) AS [AnalystName],
            -- Contact (project lead)
            co.[Person_ID]         AS [ContactID],
            CONCAT(co.[First_name], ' ', co.[Last_name]) AS [ContactName],
            -- Project
            proj.[Name]            AS [ProjectName],
            -- Purpose
            pur.[Name]             AS [PurposeName],
            -- ProcessingDegree
            m.[ProcessingDegree]
        FROM [dbo].[MetaData] m
        LEFT JOIN [dbo].[Parameter]     p    ON p.[Parameter_ID]      = m.[Parameter_ID]
        LEFT JOIN [dbo].[Unit]          u    ON u.[Unit_ID]           = m.[Unit_ID]
        LEFT JOIN [dbo].[SamplingPoints] sp  ON sp.[Sampling_point_ID] = m.[Sampling_point_ID]
        LEFT JOIN [dbo].[Site]          s    ON s.[Site_ID]           = sp.[Site_ID]
        LEFT JOIN [dbo].[Equipment]     e    ON e.[Equipment_ID]      = m.[Equipment_ID]
        LEFT JOIN [dbo].[Campaign]      c    ON c.[Campaign_ID]       = m.[Campaign_ID]
        LEFT JOIN [dbo].[CampaignType]  ct   ON ct.[CampaignType_ID]  = c.[CampaignType_ID]
        LEFT JOIN [dbo].[DataProvenance] dp  ON dp.[DataProvenance_ID] = m.[DataProvenance_ID]
        LEFT JOIN [dbo].[Laboratory]    lab  ON lab.[Laboratory_ID]   = m.[Laboratory_ID]
        LEFT JOIN [dbo].[Person]        an   ON an.[Person_ID]        = m.[AnalystPerson_ID]
        LEFT JOIN [dbo].[Person]        co   ON co.[Person_ID]        = m.[Contact_ID]
        LEFT JOIN [dbo].[Project]       proj ON proj.[Project_ID]     = m.[Project_ID]
        LEFT JOIN [dbo].[Purpose]       pur  ON pur.[Purpose_ID]      = m.[Purpose_ID]
        WHERE m.[Metadata_ID] = ?
    """
    cursor = conn.cursor()
    cursor.execute(sql, metadata_id)
    row = cursor.fetchone()

    if row is None:
        raise KeyError(f"MetaData row not found: metadata_id={metadata_id}")

    (
        md_id,
        param_id, param_name,
        unit_id, unit_name,
        sp_id, location_name,
        site_id, site_name,
        equip_id, equip_name,
        campaign_id, campaign_name, campaign_type_name,
        data_provenance_name,
        lab_id, lab_name,
        analyst_id, analyst_name,
        contact_id, contact_name,
        project_name,
        purpose_name,
        processing_degree,
    ) = row

    return {
        "metadata_id": md_id,
        "parameter": {"id": param_id, "name": param_name} if param_id else None,
        "unit": unit_name,
        "location": {"id": sp_id, "name": location_name} if sp_id else None,
        "site": {"id": site_id, "name": site_name} if site_id else None,
        "equipment": {"id": equip_id, "name": equip_name} if equip_id else None,
        "campaign": (
            {"id": campaign_id, "name": campaign_name, "type": campaign_type_name}
            if campaign_id else None
        ),
        "laboratory": {"id": lab_id, "name": lab_name} if lab_id else None,
        "analyst": {"id": analyst_id, "name": analyst_name} if analyst_id else None,
        "contact": {"id": contact_id, "name": contact_name} if contact_id else None,
        "data_provenance": data_provenance_name,
        "processing_degree": processing_degree,
        "project": project_name,
        "purpose": purpose_name,
    }


def record_processing(
    source_metadata_ids: list[int],
    method_name: str,
    method_version: str | None,
    processing_type: str,
    parameters: dict,
    executed_at: datetime,
    executed_by_person_id: int | None,
    output_metadata_id: int,
    conn,
) -> int:
    """Insert a ProcessingStep row and its DataLineage edges.

    Idempotent: if a ProcessingStep with the same MethodName, ProcessingType,
    Parameters (JSON-serialised), ExecutedAt, and the same set of source and
    output metadata IDs already exists, the function returns its ID without
    inserting duplicates.

    Args:
        source_metadata_ids: MetaData IDs that were consumed as inputs.
        method_name: Machine-readable method identifier (e.g. 'outlier_removal').
        method_version: Library/method version string, or None.
        processing_type: ProcessingType enum value string (e.g. 'Smoothing').
        parameters: Dict of method parameters; serialised to JSON for storage.
        executed_at: UTC datetime when the processing ran.
        executed_by_person_id: Person_ID of the operator, or None.
        output_metadata_id: MetaData ID of the result time series.
        conn: A pyodbc connection to open_dateaubase.

    Returns:
        The ProcessingStep_ID of the (new or existing) row.
    """
    params_json = json.dumps(parameters, default=str) if parameters else None

    # ----------------------------------------------------------------
    # Idempotency check: look for an existing step with identical
    # fingerprint that already links the same source→output pair.
    # ----------------------------------------------------------------
    check_sql = """
        SELECT DISTINCT ps.[ProcessingStep_ID]
        FROM [dbo].[ProcessingStep] ps
        JOIN [dbo].[DataLineage] out_dl
            ON out_dl.[ProcessingStep_ID] = ps.[ProcessingStep_ID]
           AND out_dl.[Role] = 'Output'
           AND out_dl.[Metadata_ID] = ?
        WHERE ps.[MethodName]       = ?
          AND ps.[ProcessingType]   = ?
          AND ISNULL(ps.[Parameters], '')   = ISNULL(?, '')
          AND ISNULL(CONVERT(NVARCHAR(30), ps.[ExecutedAt], 126), '')
            = ISNULL(CONVERT(NVARCHAR(30), CAST(? AS DATETIME2(7)), 126), '')
    """
    cursor = conn.cursor()
    cursor.execute(
        check_sql,
        output_metadata_id,
        method_name,
        processing_type,
        params_json,
        executed_at,
    )
    existing = cursor.fetchone()
    if existing is not None:
        return existing[0]

    # ----------------------------------------------------------------
    # Insert ProcessingStep
    # ----------------------------------------------------------------
    insert_step_sql = """
        INSERT INTO [dbo].[ProcessingStep]
            ([Name], [MethodName], [MethodVersion], [ProcessingType],
             [Parameters], [ExecutedAt], [ExecutedByPerson_ID])
        OUTPUT INSERTED.[ProcessingStep_ID]
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """
    name = method_name or processing_type or "Processing step"
    cursor.execute(
        insert_step_sql,
        name,
        method_name,
        method_version,
        processing_type,
        params_json,
        executed_at,
        executed_by_person_id,
    )
    step_id: int = cursor.fetchone()[0]

    # ----------------------------------------------------------------
    # Insert DataLineage rows — Inputs
    # ----------------------------------------------------------------
    for src_id in source_metadata_ids:
        cursor.execute(
            "INSERT INTO [dbo].[DataLineage] ([ProcessingStep_ID], [Metadata_ID], [Role]) "
            "VALUES (?, ?, 'Input')",
            step_id,
            src_id,
        )

    # ----------------------------------------------------------------
    # Insert DataLineage row — Output
    # ----------------------------------------------------------------
    cursor.execute(
        "INSERT INTO [dbo].[DataLineage] ([ProcessingStep_ID], [Metadata_ID], [Role]) "
        "VALUES (?, ?, 'Output')",
        step_id,
        output_metadata_id,
    )

    return step_id
