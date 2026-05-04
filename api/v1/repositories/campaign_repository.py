"""Data access for Campaign resources."""

from __future__ import annotations

import pyodbc

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
        SELECT sp.[SamplingPoint_ID], sp.[SamplingPoint], csl.[Role]
        FROM [dbo].[CampaignSamplingLocation] csl
        JOIN [dbo].[SamplingPoint] sp ON sp.[SamplingPoint_ID] = csl.[SamplingPoint_ID]
        WHERE csl.[Campaign_ID] = ?
        ORDER BY sp.[SamplingPoint_ID]
        """,
        campaign_id,
    )
    locations = [{"id": r[0], "name": r[1], "role": r[2]} for r in cursor.fetchall()]

    # Equipment
    cursor.execute(
        """
        SELECT e.[Equipment_ID], e.[Identifier], ce.[Role]
        FROM [dbo].[CampaignEquipment] ce
        JOIN [dbo].[Equipment] e ON e.[Equipment_ID] = ce.[Equipment_ID]
        WHERE ce.[Campaign_ID] = ?
        ORDER BY e.[Equipment_ID]
        """,
        campaign_id,
    )
    equipment = [
        {"id": r[0], "identifier": r[1], "role": r[2]} for r in cursor.fetchall()
    ]

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
            csl.[SamplingPoint_ID],
            sp.[SamplingPoint] AS sampling_point_name,
            ce.[Role],
            ei.[Installation_ID],
            ei.[InstalledDate]
        FROM [dbo].[CampaignEquipment] ce
        JOIN [dbo].[Equipment] e ON e.[Equipment_ID] = ce.[Equipment_ID]
        LEFT JOIN [dbo].[CampaignSamplingLocation] csl
            ON csl.[Campaign_ID] = ce.[Campaign_ID]
        LEFT JOIN [dbo].[SamplingPoint] sp
            ON sp.[SamplingPoint_ID] = csl.[SamplingPoint_ID]
        LEFT JOIN [dbo].[EquipmentInstallation] ei
            ON ei.[Equipment_ID] = ce.[Equipment_ID]
            AND ei.[SamplingPoint_ID] = csl.[SamplingPoint_ID]
            AND ei.[Campaign_ID] = ce.[Campaign_ID]
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
            "role": row[4],
            "installation_id": row[5],
            "installed_date": row[6],
        }
        for row in cursor.fetchall()
    ]


def create_campaign_deployment(
    conn: pyodbc.Connection,
    campaign_id: int,
    equipment_id: int,
    sampling_point_id: int,
    role: str | None,
    notes: str | None,
) -> int:
    """Link equipment and a sampling point to a campaign.

    Inserts into CampaignEquipment and CampaignSamplingLocation.
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
        INSERT INTO [dbo].[CampaignEquipment] ([Campaign_ID], [Equipment_ID], [Role])
        VALUES (?, ?, ?)
        """,
        campaign_id,
        equipment_id,
        role,
    )

    cursor.execute(
        """
        IF NOT EXISTS (
            SELECT 1 FROM [dbo].[CampaignSamplingLocation]
            WHERE [Campaign_ID] = ? AND [SamplingPoint_ID] = ?
        )
        INSERT INTO [dbo].[CampaignSamplingLocation]
            ([Campaign_ID], [SamplingPoint_ID], [Role])
        VALUES (?, ?, NULL)
        """,
        campaign_id,
        sampling_point_id,
        campaign_id,
        sampling_point_id,
    )

    conn.commit()
    return equipment_id


def delete_campaign_deployment(
    conn: pyodbc.Connection,
    campaign_id: int,
    equipment_id: int,
    sampling_point_id: int,
) -> None:
    """Delete a deployment: remove from EquipmentInstallation, CampaignEquipment,
    and CampaignSamplingLocation atomically."""
    cursor = conn.cursor()

    cursor.execute(
        """
        DELETE FROM [dbo].[EquipmentInstallation]
        WHERE [Campaign_ID] = ? AND [Equipment_ID] = ? AND [SamplingPoint_ID] = ?
        """,
        campaign_id,
        equipment_id,
        sampling_point_id,
    )

    cursor.execute(
        """
        DELETE FROM [dbo].[CampaignEquipment]
        WHERE [Campaign_ID] = ? AND [Equipment_ID] = ?
        """,
        campaign_id,
        equipment_id,
    )

    cursor.execute(
        """
        DELETE FROM [dbo].[CampaignSamplingLocation]
        WHERE [Campaign_ID] = ? AND [SamplingPoint_ID] = ?
        """,
        campaign_id,
        sampling_point_id,
    )

    conn.commit()


def delete_campaign_deployment_by_installation(
    conn: pyodbc.Connection,
    campaign_id: int,
    installation_id: int,
) -> bool:
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT [Equipment_ID], [SamplingPoint_ID]
        FROM [dbo].[EquipmentInstallation]
        WHERE [EquipmentInstallation_ID] = ? AND [Campaign_ID] = ?
        """,
        installation_id,
        campaign_id,
    )
    row = cursor.fetchone()
    if row is None:
        return False
    equipment_id, sampling_point_id = row
    delete_campaign_deployment(conn, campaign_id, equipment_id, sampling_point_id)
    return True
