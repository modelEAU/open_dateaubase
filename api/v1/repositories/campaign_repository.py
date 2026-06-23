"""Data access for Campaign resources."""

from __future__ import annotations

from datetime import datetime, timezone

import pyodbc

from . import temporal_history_repository

_CAMPAIGN_SELECT = """
    SELECT
        c.[Campaign_ID],
        c.[CampaignKind_ID],
        ct.[Name],
        c.[Site_ID],
        s.[Name]            AS SiteName,
        c.[Name],
        c.[Description],
        c.[CampaignStartDateTime],
        c.[CampaignEndDateTime],
        c.[ResponsiblePerson_ID],
        CONCAT(p.[FirstName], ' ', p.[LastName]) AS ResponsiblePersonName
    FROM [dbo].[Campaign] c
    LEFT JOIN [dbo].[CampaignKind] ct ON ct.[CampaignKind_ID] = c.[CampaignKind_ID]
    LEFT JOIN [dbo].[Site]         s  ON s.[Site_ID]          = c.[Site_ID]
    LEFT JOIN [dbo].[Person]       p  ON p.[Person_ID]        = c.[ResponsiblePerson_ID]
"""


def _row_to_dict(row) -> dict:
    return {
        "campaign_id": row[0],
        "campaign_kind_id": row[1],
        "campaign_kind_name": row[2],
        "site_id": row[3],
        "site_name": row[4],
        "name": row[5],
        "description": row[6],
        "start_date": row[7],
        "end_date": row[8],
        "responsible_person_id": row[9],
        "responsible_person_name": row[10],
    }


def list_campaigns(
    conn: pyodbc.Connection,
    *,
    site_id: int | None = None,
    campaign_kind_id: int | None = None,
) -> list[dict]:
    where_parts = []
    params = []
    if site_id is not None:
        where_parts.append("c.[Site_ID] = ?")
        params.append(site_id)
    if campaign_kind_id is not None:
        where_parts.append("c.[CampaignKind_ID] = ?")
        params.append(campaign_kind_id)

    where_clause = ("WHERE " + " AND ".join(where_parts)) if where_parts else ""
    cursor = conn.cursor()
    cursor.execute(
        _CAMPAIGN_SELECT + where_clause + " ORDER BY c.[Campaign_ID]", *params
    )
    return [_row_to_dict(row) for row in cursor.fetchall()]


def get_campaign_by_id(conn: pyodbc.Connection, campaign_id: int) -> dict | None:
    cursor = conn.cursor()
    cursor.execute(_CAMPAIGN_SELECT + " WHERE c.[Campaign_ID] = ?", campaign_id)
    row = cursor.fetchone()
    return _row_to_dict(row) if row else None


def insert_campaign(conn: pyodbc.Connection, data: dict) -> dict | None:
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO [dbo].[Campaign]"
        " ([Name], [CampaignKind_ID], [Site_ID], [Description],"
        " [CampaignStartDateTime], [CampaignEndDateTime], [ResponsiblePerson_ID])"
        " VALUES (?, ?, ?, ?, ?, ?, ?)",
        data.get("name"),
        data.get("campaign_kind_id"),
        data.get("site_id"),
        data.get("description"),
        data.get("start_date"),
        data.get("end_date"),
        data.get("responsible_person_id"),
    )
    cursor.execute("SELECT @@IDENTITY")
    _row = cursor.fetchone()
    assert _row is not None
    new_id = int(_row[0])
    conn.commit()
    return get_campaign_by_id(conn, new_id)


def update_campaign(
    conn: pyodbc.Connection, campaign_id: int, data: dict
) -> dict | None:
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE [dbo].[Campaign]"
        " SET [Name]=?, [CampaignKind_ID]=?, [Site_ID]=?, [Description]=?,"
        " [CampaignStartDateTime]=?, [CampaignEndDateTime]=?, [ResponsiblePerson_ID]=?"
        " WHERE [Campaign_ID]=?",
        data.get("name"),
        data.get("campaign_kind_id"),
        data.get("site_id"),
        data.get("description"),
        data.get("start_date"),
        data.get("end_date"),
        data.get("responsible_person_id"),
        campaign_id,
    )
    conn.commit()
    return get_campaign_by_id(conn, campaign_id)


def delete_campaign(conn: pyodbc.Connection, campaign_id: int) -> bool:
    cursor = conn.cursor()
    cursor.execute("DELETE FROM [dbo].[Campaign] WHERE [Campaign_ID]=?", campaign_id)
    conn.commit()
    return cursor.rowcount > 0


def patch_campaign(
    conn: pyodbc.Connection, campaign_id: int, data: dict
) -> dict | None:
    """Partial update of a campaign - only updates fields that are present in data."""
    existing = get_campaign_by_id(conn, campaign_id)
    if existing is None:
        return None

    fields = []
    values = []

    if "name" in data:
        fields.append("[Name]=?")
        values.append(data.get("name"))
    if "campaign_kind_id" in data:
        fields.append("[CampaignKind_ID]=?")
        values.append(data.get("campaign_kind_id"))
    if "site_id" in data:
        fields.append("[Site_ID]=?")
        values.append(data.get("site_id"))
    if "description" in data:
        fields.append("[Description]=?")
        values.append(data.get("description"))
    if "start_date" in data:
        fields.append("[CampaignStartDateTime]=?")
        values.append(data.get("start_date"))
    if "end_date" in data:
        fields.append("[CampaignEndDateTime]=?")
        values.append(data.get("end_date"))
    if "responsible_person_id" in data:
        fields.append("[ResponsiblePerson_ID]=?")
        values.append(data.get("responsible_person_id"))

    if not fields:
        return existing

    values.append(campaign_id)
    cursor = conn.cursor()
    cursor.execute(
        f"UPDATE [dbo].[Campaign] SET {', '.join(fields)} WHERE [Campaign_ID]=?",
        *values,
    )
    conn.commit()
    return get_campaign_by_id(conn, campaign_id)


def get_campaign_kinds(conn: pyodbc.Connection) -> list[dict]:
    """Return all campaign kinds for dropdowns."""
    cursor = conn.cursor()
    cursor.execute(
        "SELECT [CampaignKind_ID], [Name], [Description] FROM [dbo].[CampaignKind] ORDER BY [Name]"
    )
    return [{"campaign_kind_id": row[0], "name": row[1], "description": row[2]} for row in cursor.fetchall()]


def get_campaign_context(conn: pyodbc.Connection, campaign_id: int) -> dict:
    """Aggregate full context for a campaign."""
    cursor = conn.cursor()

    # Sampling locations
    cursor.execute(
        """
        SELECT sp.[SamplingPoint_ID], sp.[SamplingPoint]
        FROM [dbo].[CampaignSamplingLocation] csl
        JOIN [dbo].[SamplingPoint] sp ON sp.[SamplingPoint_ID] = csl.[SamplingPoint_ID]
        WHERE csl.[Campaign_ID] = ?
        ORDER BY sp.[SamplingPoint_ID]
        """,
        campaign_id,
    )
    locations = [{"id": r[0], "name": r[1]} for r in cursor.fetchall()]

    # Equipment
    cursor.execute(
        """
        SELECT e.[Equipment_ID], e.[Identifier]
        FROM [dbo].[CampaignEquipment] ce
        JOIN [dbo].[Equipment] e ON e.[Equipment_ID] = ce.[Equipment_ID]
        WHERE ce.[Campaign_ID] = ?
        ORDER BY e.[Equipment_ID]
        """,
        campaign_id,
    )
    equipment = [{"id": r[0], "identifier": r[1]} for r in cursor.fetchall()]

    # Parameters (distinct parameters across channels linked via campaign equipment)
    cursor.execute(
        """
        SELECT DISTINCT p.[Parameter_ID], p.[Parameter]
        FROM [dbo].[Channel] ch
        JOIN [dbo].[CampaignEquipment] ce ON ce.[Equipment_ID] = ch.[Equipment_ID]
        JOIN [dbo].[Parameter] p ON p.[Parameter_ID] = ch.[Parameter_ID]
        WHERE ce.[Campaign_ID] = ?
        ORDER BY p.[Parameter_ID]
        """,
        campaign_id,
    )
    parameters = [{"id": r[0], "name": r[1]} for r in cursor.fetchall()]

    # Channel count and time range (via CampaignEquipment)
    cursor.execute(
        """
        SELECT COUNT(DISTINCT ch.[Channel_ID]), MIN(v.[Timestamp]), MAX(v.[Timestamp])
        FROM [dbo].[Channel] ch
        JOIN [dbo].[CampaignEquipment] ce ON ce.[Equipment_ID] = ch.[Equipment_ID]
        LEFT JOIN [dbo].[Value] v ON v.[Channel_ID] = ch.[Channel_ID]
        WHERE ce.[Campaign_ID] = ?
        """,
        campaign_id,
    )
    row = cursor.fetchone()
    channel_count = row[0] if row else 0
    time_start = row[1] if row else None
    time_end = row[2] if row else None

    return {
        "sampling_locations": locations,
        "equipment": equipment,
        "parameters": parameters,
        "channel_count": channel_count,
        "time_range_start": time_start,
        "time_range_end": time_end,
    }


def list_campaign_deployments(conn: pyodbc.Connection, campaign_id: int) -> list[dict]:
    """Return all deployments (equipment + sampling point pairs) for a campaign."""
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT
            ce.[Equipment_ID],
            e.[Identifier] AS equipment_identifier,
            elh.[SamplingPoint_ID],
            sp.[SamplingPoint] AS sampling_point_name,
            ce.[Equipment_ID] AS installation_id,
            elh.[ValidFrom] AS installed_date
        FROM [dbo].[CampaignEquipment] ce
        JOIN [dbo].[Equipment] e ON e.[Equipment_ID] = ce.[Equipment_ID]
        LEFT JOIN [dbo].[EquipmentLocationHistory] elh
            ON elh.[Equipment_ID] = ce.[Equipment_ID]
            AND elh.[Campaign_ID] = ce.[Campaign_ID]
            AND elh.[ValidTo] IS NULL
        LEFT JOIN [dbo].[SamplingPoint] sp
            ON sp.[SamplingPoint_ID] = elh.[SamplingPoint_ID]
        WHERE ce.[Campaign_ID] = ?
        """,
        campaign_id,
    )
    return [
        {
            "equipment_id": row[0],
            "equipment_identifier": row[1],
            "sampling_point_id": row[2],
            "sampling_point_name": row[3],
            "installation_id": row[4],
            "installed_date": row[5],
        }
        for row in cursor.fetchall()
    ]


def create_campaign_deployment(
    conn: pyodbc.Connection,
    campaign_id: int,
    equipment_id: int,
    sampling_point_id: int,
    valid_from: datetime | None = None,
    notes: str | None = None,
) -> int:
    """Link equipment and a sampling point to a campaign and physically place
    the equipment at the sampling point (BUG-5).

    Three writes inside a single transaction:
      1. ``CampaignEquipment`` row (campaign↔equipment linkage).
      2. ``CampaignSamplingLocation`` row (campaign↔SP linkage, idempotent).
      3. ``EquipmentLocationHistory`` row tagged with ``Campaign_ID`` (the
         actual physical placement — previously omitted, so equipment was
         never queryable via ``GET /equipment/{id}/location-at``).

    Returns equipment_id as a stable deployment identifier (EquipmentInstallation
    was dropped in v3.0.0; location tracking is now via EquipmentLocationHistory).

    Raises ValueError if equipment is already deployed in this campaign."""
    cursor = conn.cursor()

    # Check duplicate via CampaignEquipment (the authoritative linkage table)
    cursor.execute(
        """
        SELECT COUNT(*) FROM [dbo].[CampaignEquipment]
        WHERE [Campaign_ID] = ? AND [Equipment_ID] = ?
        """,
        campaign_id,
        equipment_id,
    )
    _count_row = cursor.fetchone()
    assert _count_row is not None
    if _count_row[0] > 0:
        raise ValueError(
            f"Equipment {equipment_id} is already deployed in this campaign"
        )

    cursor.execute(
        """
        INSERT INTO [dbo].[CampaignEquipment] ([Campaign_ID], [Equipment_ID])
        VALUES (?, ?)
        """,
        campaign_id,
        equipment_id,
    )

    cursor.execute(
        """
        IF NOT EXISTS (
            SELECT 1 FROM [dbo].[CampaignSamplingLocation]
            WHERE [Campaign_ID] = ? AND [SamplingPoint_ID] = ?
        )
        INSERT INTO [dbo].[CampaignSamplingLocation]
            ([Campaign_ID], [SamplingPoint_ID])
        VALUES (?, ?)
        """,
        campaign_id,
        sampling_point_id,
        campaign_id,
        sampling_point_id,
    )

    # Physically place the equipment at the sampling point (BUG-5).
    # open_location_for_campaign does not commit — we own the transaction.
    temporal_history_repository.open_location_for_campaign(
        conn,
        equipment_id=equipment_id,
        sampling_point_id=sampling_point_id,
        start_time=valid_from or datetime.now(timezone.utc),
        campaign_id=campaign_id,
        notes=notes,
    )

    conn.commit()
    return equipment_id


def delete_campaign_deployment(
    conn: pyodbc.Connection,
    campaign_id: int,
    equipment_id: int,
    sampling_point_id: int | None,
) -> None:
    """Reverse a deployment created by :func:`create_campaign_deployment`.

    In one transaction:
      1. Delete the active (``ValidTo IS NULL``) ``EquipmentLocationHistory`` row
         tagged with this campaign for the equipment (the physical placement that
         create opened). EquipmentInstallation was dropped — placement lives here.
      2. Delete the ``CampaignEquipment`` link.
      3. Delete the ``CampaignSamplingLocation`` link **only if** no other equipment
         remains placed at that sampling point under this campaign (the link is
         campaign-level and shared across deployments).
    """
    cursor = conn.cursor()

    cursor.execute(
        """
        DELETE FROM [dbo].[EquipmentLocationHistory]
        WHERE [Campaign_ID] = ? AND [Equipment_ID] = ? AND [ValidTo] IS NULL
        """,
        campaign_id,
        equipment_id,
    )

    cursor.execute(
        """
        DELETE FROM [dbo].[CampaignEquipment]
        WHERE [Campaign_ID] = ? AND [Equipment_ID] = ?
        """,
        campaign_id,
        equipment_id,
    )

    if sampling_point_id is not None:
        cursor.execute(
            """
            DELETE FROM [dbo].[CampaignSamplingLocation]
            WHERE [Campaign_ID] = ? AND [SamplingPoint_ID] = ?
            AND NOT EXISTS (
                SELECT 1 FROM [dbo].[EquipmentLocationHistory] elh
                WHERE elh.[Campaign_ID] = ?
                  AND elh.[SamplingPoint_ID] = ?
                  AND elh.[ValidTo] IS NULL
            )
            """,
            campaign_id,
            sampling_point_id,
            campaign_id,
            sampling_point_id,
        )

    conn.commit()


def delete_campaign_deployment_by_installation(
    conn: pyodbc.Connection,
    campaign_id: int,
    installation_id: int,
) -> bool:
    """Delete a deployment by its handle. ``installation_id`` is the Equipment_ID
    (what :func:`create_campaign_deployment` returns). Returns False if the
    equipment is not deployed in this campaign."""
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT 1 FROM [dbo].[CampaignEquipment]
        WHERE [Campaign_ID] = ? AND [Equipment_ID] = ?
        """,
        campaign_id,
        installation_id,
    )
    if cursor.fetchone() is None:
        return False

    # Resolve the active campaign placement to know which SP link to clean up.
    cursor.execute(
        """
        SELECT [SamplingPoint_ID]
        FROM [dbo].[EquipmentLocationHistory]
        WHERE [Campaign_ID] = ? AND [Equipment_ID] = ? AND [ValidTo] IS NULL
        """,
        campaign_id,
        installation_id,
    )
    row = cursor.fetchone()
    sampling_point_id = row[0] if row else None
    delete_campaign_deployment(conn, campaign_id, installation_id, sampling_point_id)
    return True


# ---------------------------------------------------------------------------
# Campaign Story overview — read-only aggregate for the Campaign Story page.
# Each block is an independent, simple query (mirrors get_campaign_context's
# style) so the SQL stays legible and individually verifiable.
# ---------------------------------------------------------------------------


def get_campaign_overview(conn: pyodbc.Connection, campaign_id: int) -> dict:
    """Assemble the read-only story data for a campaign in one round-trip.

    Returns watershed, data acquisition systems, deployed equipment (with a
    coarse DB-backed status), lab series, lab panels, campaign-scoped
    annotations, and per-stream freshness (last data point). The combined plot
    is fed separately by the existing per-channel timeseries loaders.
    """
    cur = conn.cursor()

    # --- Watershed (via the campaign's site) ------------------------------
    cur.execute(
        """
        SELECT w.[Watershed_ID], w.[Name]
        FROM [dbo].[Campaign] c
        JOIN [dbo].[Site] s ON s.[Site_ID] = c.[Site_ID]
        LEFT JOIN [dbo].[Watershed] w ON w.[Watershed_ID] = s.[Watershed_ID]
        WHERE c.[Campaign_ID] = ?
        """,
        campaign_id,
    )
    row = cur.fetchone()
    watershed = {"id": row[0], "name": row[1]} if row and row[0] is not None else None

    # --- Sampling points monitored (the "sites surveilled") ---------------
    cur.execute(
        """
        SELECT sp.[SamplingPoint_ID], sp.[SamplingPoint],
               sp.[LatitudeWGS84], sp.[LongitudeWGS84], csl.[Role]
        FROM [dbo].[CampaignSamplingLocation] csl
        JOIN [dbo].[SamplingPoint] sp ON sp.[SamplingPoint_ID] = csl.[SamplingPoint_ID]
        WHERE csl.[Campaign_ID] = ?
        ORDER BY sp.[SamplingPoint]
        """,
        campaign_id,
    )
    sampling_points = [
        {"id": r[0], "name": r[1], "lat": r[2], "lon": r[3], "role": r[4]}
        for r in cur.fetchall()
    ]

    # --- Data acquisition systems deployed in this campaign ---------------
    cur.execute(
        """
        SELECT DISTINCT das.[DataAcquisitionSystem_ID], das.[Name],
               dk.[Name] AS kind, dlh.[ValidFrom]
        FROM [dbo].[DASLocationHistory] dlh
        JOIN [dbo].[DataAcquisitionSystem] das
            ON das.[DataAcquisitionSystem_ID] = dlh.[DataAcquisitionSystem_ID]
        LEFT JOIN [dbo].[DataAcquisitionSystemKind] dk
            ON dk.[DataAcquisitionSystemKind_ID] = das.[DataAcquisitionSystemKind_ID]
        WHERE dlh.[Campaign_ID] = ?
        ORDER BY das.[Name]
        """,
        campaign_id,
    )
    das = [
        {"id": r[0], "name": r[1], "kind": r[2], "valid_from": r[3]}
        for r in cur.fetchall()
    ]

    # --- Equipment deployed, with a coarse status -------------------------
    # Status is DB-backed (not a guess): an ongoing, non-instantaneous
    # EquipmentEvent => that event kind; else IsActive => in service.
    cur.execute(
        """
        SELECT
            e.[Equipment_ID], e.[Identifier], em.[EquipmentModel] AS model,
            ce.[Role], sp.[SamplingPoint] AS location, e.[IsActive],
            (SELECT TOP 1 eek.[Name]
             FROM [dbo].[EquipmentEvent] ev
             JOIN [dbo].[EquipmentEventKind] eek
                 ON eek.[EquipmentEventKind_ID] = ev.[EquipmentEventKind_ID]
             WHERE ev.[Equipment_ID] = e.[Equipment_ID]
               AND ev.[EventDateTimeEnd] IS NULL
               AND ev.[IsInstantaneous] = 0
             ORDER BY ev.[EventDateTimeStart] DESC) AS ongoing_event
        FROM [dbo].[CampaignEquipment] ce
        JOIN [dbo].[Equipment] e ON e.[Equipment_ID] = ce.[Equipment_ID]
        LEFT JOIN [dbo].[EquipmentModel] em ON em.[EquipmentModel_ID] = e.[EquipmentModel_ID]
        LEFT JOIN [dbo].[EquipmentLocationHistory] elh
            ON elh.[Equipment_ID] = e.[Equipment_ID]
            AND elh.[Campaign_ID] = ce.[Campaign_ID] AND elh.[ValidTo] IS NULL
        LEFT JOIN [dbo].[SamplingPoint] sp ON sp.[SamplingPoint_ID] = elh.[SamplingPoint_ID]
        WHERE ce.[Campaign_ID] = ?
        ORDER BY e.[Identifier]
        """,
        campaign_id,
    )
    equipment = [
        {
            "equipment_id": r[0], "identifier": r[1], "model": r[2], "role": r[3],
            "location": r[4], "is_active": bool(r[5]), "ongoing_event": r[6],
        }
        for r in cur.fetchall()
    ]

    # --- Lab series scoped to this campaign -------------------------------
    cur.execute(
        """
        SELECT a.[Stream_ID], a.[Name], p.[Parameter], u.[Unit], vk.[Name] AS value_kind,
               sp.[SamplingPoint] AS location
        FROM [dbo].[AnalysisSeries] a
        LEFT JOIN [dbo].[Parameter] p ON p.[Parameter_ID] = a.[Parameter_ID]
        LEFT JOIN [dbo].[Unit] u ON u.[Unit_ID] = a.[Unit_ID]
        LEFT JOIN [dbo].[ValueKind] vk ON vk.[ValueKind_ID] = a.[ValueKind_ID]
        LEFT JOIN [dbo].[SamplingPoint] sp ON sp.[SamplingPoint_ID] = a.[SamplingPoint_ID]
        WHERE a.[Campaign_ID] = ?
        ORDER BY a.[Name]
        """,
        campaign_id,
    )
    lab_series = [
        {
            "stream_id": r[0], "name": r[1], "parameter_name": r[2], "unit_name": r[3],
            "value_kind_name": r[4], "sampling_point_label": r[5],
        }
        for r in cur.fetchall()
    ]

    # --- Lab panels used by this campaign's experiments -------------------
    cur.execute(
        """
        SELECT DISTINCT lp.[LabPanel_ID], lp.[Name],
               (SELECT COUNT(*) FROM [dbo].[LabPanelSeries] lps
                WHERE lps.[LabPanel_ID] = lp.[LabPanel_ID]) AS series_count
        FROM [dbo].[LabExperiment] le
        JOIN [dbo].[LabPanel] lp ON lp.[LabPanel_ID] = le.[LabPanel_ID]
        WHERE le.[Campaign_ID] = ?
        ORDER BY lp.[Name]
        """,
        campaign_id,
    )
    lab_panels = [
        {"id": r[0], "name": r[1], "series_count": r[2]} for r in cur.fetchall()
    ]

    # --- Annotations attached to this campaign ----------------------------
    cur.execute(
        """
        SELECT a.[Annotation_ID], ak.[Name] AS kind, ak.[Color], a.[Title],
               a.[Comment], a.[StartTime], a.[EndTime]
        FROM [dbo].[Annotation] a
        LEFT JOIN [dbo].[AnnotationKind] ak ON ak.[AnnotationKind_ID] = a.[AnnotationKind_ID]
        WHERE a.[Campaign_ID] = ?
        ORDER BY a.[StartTime] DESC
        """,
        campaign_id,
    )
    annotations = [
        {
            "id": r[0], "kind": r[1], "color": r[2], "title": r[3],
            "comment": r[4], "start_time": r[5], "end_time": r[6],
        }
        for r in cur.fetchall()
    ]

    # --- Freshness: last data point per stream (sensor + lab) -------------
    # ponytail: wiring match on SignalInterface_ID + active row only — good
    # enough for "last point"; the precise port disambiguation that list_channels
    # does is not needed here. Upgrade if a campaign reuses one interface across
    # ports with diverging freshness.
    cur.execute(
        """
        SELECT c.[Stream_ID], p.[Parameter] AS label,
               MIN(o.[Timestamp]) AS first_point, MAX(o.[Timestamp]) AS last_point
        FROM [dbo].[Channel] c
        LEFT JOIN [dbo].[Parameter] p ON p.[Parameter_ID] = c.[Parameter_ID]
        JOIN [dbo].[EquipmentWiringHistory] ewh
            ON ewh.[SignalInterface_ID] = c.[SignalInterface_ID] AND ewh.[ValidTo] IS NULL
        JOIN [dbo].[CampaignEquipment] ce
            ON ce.[Equipment_ID] = ewh.[Equipment_ID] AND ce.[Campaign_ID] = ?
        LEFT JOIN [dbo].[Observation] o ON o.[Channel_ID] = c.[Stream_ID]
        GROUP BY c.[Stream_ID], p.[Parameter]
        """,
        campaign_id,
    )
    freshness = [
        {"stream_id": r[0], "kind": "sensor", "label": r[1],
         "first_point": r[2], "last_point": r[3]}
        for r in cur.fetchall()
    ]
    cur.execute(
        """
        SELECT a.[Stream_ID], a.[Name] AS label,
               MIN(o.[Timestamp]) AS first_point, MAX(o.[Timestamp]) AS last_point
        FROM [dbo].[AnalysisSeries] a
        LEFT JOIN [dbo].[LabAnalysis] la ON la.[AnalysisSeries_ID] = a.[Stream_ID]
        LEFT JOIN [dbo].[Observation] o ON o.[LabAnalysis_ID] = la.[LabAnalysis_ID]
        WHERE a.[Campaign_ID] = ?
        GROUP BY a.[Stream_ID], a.[Name]
        """,
        campaign_id,
    )
    freshness += [
        {"stream_id": r[0], "kind": "lab", "label": r[1],
         "first_point": r[2], "last_point": r[3]}
        for r in cur.fetchall()
    ]

    return {
        "watershed": watershed,
        "sampling_points": sampling_points,
        "data_acquisition_systems": das,
        "equipment": equipment,
        "lab_series": lab_series,
        "lab_panels": lab_panels,
        "annotations": annotations,
        "freshness": freshness,
    }
