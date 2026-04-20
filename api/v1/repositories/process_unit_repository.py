"""Data access for ProcessUnit and ProcessUnitType."""

from __future__ import annotations

import pyodbc


# ---------------------------------------------------------------------------
# ProcessUnitType
# ---------------------------------------------------------------------------


def get_all_process_unit_types(conn: pyodbc.Connection) -> list[dict]:
    cursor = conn.cursor()
    cursor.execute(
        "SELECT [ProcessUnitType_ID], [Name], [Description] "
        "FROM [dbo].[ProcessUnitType] ORDER BY [Name]"
    )
    return [{"id": row[0], "name": row[1], "description": row[2]} for row in cursor.fetchall()]


def insert_process_unit_type(
    conn: pyodbc.Connection, name: str, description: str | None
) -> dict:
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO [dbo].[ProcessUnitType] ([Name], [Description])
        OUTPUT inserted.[ProcessUnitType_ID], inserted.[Name], inserted.[Description]
        VALUES (?, ?)
        """,
        name,
        description,
    )
    row = cursor.fetchone()
    conn.commit()
    return {"id": row[0], "name": row[1], "description": row[2]}


def update_process_unit_type(
    conn: pyodbc.Connection, process_unit_type_id: int, name: str, description: str | None
) -> dict | None:
    cursor = conn.cursor()
    cursor.execute(
        """
        UPDATE [dbo].[ProcessUnitType]
        SET [Name]=?, [Description]=?
        OUTPUT inserted.[ProcessUnitType_ID], inserted.[Name], inserted.[Description]
        WHERE [ProcessUnitType_ID]=?
        """,
        name,
        description,
        process_unit_type_id,
    )
    row = cursor.fetchone()
    conn.commit()
    if row is None:
        return None
    return {"id": row[0], "name": row[1], "description": row[2]}


def delete_process_unit_type(conn: pyodbc.Connection, process_unit_type_id: int) -> bool:
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM [dbo].[ProcessUnitType] WHERE [ProcessUnitType_ID]=?",
        process_unit_type_id,
    )
    cursor.execute("SELECT @@ROWCOUNT")
    deleted = cursor.fetchone()[0] > 0
    conn.commit()
    return deleted


# ---------------------------------------------------------------------------
# ProcessUnit
# ---------------------------------------------------------------------------

_SELECT_UNIT = """
    SELECT
        pu.[ProcessUnit_ID],
        pu.[Site_ID],
        pu.[Tag],
        pu.[Name],
        pu.[Description],
        pu.[ProcessUnitType_ID],
        put.[Name] AS TypeName,
        pu.[Parent_ID],
        p.[Name]   AS ParentName
    FROM [dbo].[ProcessUnit] pu
    LEFT JOIN [dbo].[ProcessUnitType] put
        ON pu.[ProcessUnitType_ID] = put.[ProcessUnitType_ID]
    LEFT JOIN [dbo].[ProcessUnit] p
        ON pu.[Parent_ID] = p.[ProcessUnit_ID]
"""


def _row_to_dict(row) -> dict:
    return {
        "id": row[0],
        "site_id": row[1],
        "tag": row[2],
        "name": row[3],
        "description": row[4],
        "process_unit_type_id": row[5],
        "process_unit_type_name": row[6],
        "parent_id": row[7],
        "parent_name": row[8],
    }


def get_all_process_units(
    conn: pyodbc.Connection, site_id: int | None = None
) -> list[dict]:
    cursor = conn.cursor()
    if site_id is not None:
        cursor.execute(
            _SELECT_UNIT + " WHERE pu.[Site_ID]=? ORDER BY pu.[ProcessUnit_ID]",
            site_id,
        )
    else:
        cursor.execute(_SELECT_UNIT + " ORDER BY pu.[ProcessUnit_ID]")
    return [_row_to_dict(row) for row in cursor.fetchall()]


def get_process_unit_by_id(conn: pyodbc.Connection, process_unit_id: int) -> dict | None:
    cursor = conn.cursor()
    cursor.execute(
        _SELECT_UNIT + " WHERE pu.[ProcessUnit_ID]=?",
        process_unit_id,
    )
    row = cursor.fetchone()
    return None if row is None else _row_to_dict(row)


def get_process_units_lookup(
    conn: pyodbc.Connection, site_id: int | None = None
) -> list[dict]:
    cursor = conn.cursor()
    if site_id is not None:
        cursor.execute(
            "SELECT [ProcessUnit_ID], [Name], [Tag], [Site_ID] "
            "FROM [dbo].[ProcessUnit] WHERE [Site_ID]=? ORDER BY [Name]",
            site_id,
        )
    else:
        cursor.execute(
            "SELECT [ProcessUnit_ID], [Name], [Tag], [Site_ID] "
            "FROM [dbo].[ProcessUnit] ORDER BY [Name]"
        )
    return [
        {"id": row[0], "name": row[1], "tag": row[2], "site_id": row[3]}
        for row in cursor.fetchall()
    ]


def get_process_unit_tree(conn: pyodbc.Connection, site_id: int) -> list[dict]:
    """Return the process unit hierarchy for a site as a nested tree."""
    flat = get_all_process_units(conn, site_id=site_id)
    nodes: dict[int, dict] = {row["id"]: {**row, "children": []} for row in flat}
    roots: list[dict] = []
    for node in nodes.values():
        if node["parent_id"] and node["parent_id"] in nodes:
            nodes[node["parent_id"]]["children"].append(node)
        else:
            roots.append(node)
    return roots


def insert_process_unit(conn: pyodbc.Connection, data: dict) -> dict:
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO [dbo].[ProcessUnit]
            ([Site_ID], [Tag], [Name], [Description], [ProcessUnitType_ID], [Parent_ID])
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        data["site_id"],
        data["tag"],
        data["name"],
        data.get("description"),
        data.get("process_unit_type_id"),
        data.get("parent_id"),
    )
    cursor.execute("SELECT @@IDENTITY")
    new_id = int(cursor.fetchone()[0])
    conn.commit()
    return get_process_unit_by_id(conn, new_id)


def update_process_unit(
    conn: pyodbc.Connection, process_unit_id: int, data: dict
) -> dict | None:
    existing = get_process_unit_by_id(conn, process_unit_id)
    if existing is None:
        return None
    cursor = conn.cursor()
    cursor.execute(
        """
        UPDATE [dbo].[ProcessUnit]
        SET [Site_ID]=?, [Tag]=?, [Name]=?, [Description]=?,
            [ProcessUnitType_ID]=?, [Parent_ID]=?
        WHERE [ProcessUnit_ID]=?
        """,
        data["site_id"],
        data["tag"],
        data["name"],
        data.get("description"),
        data.get("process_unit_type_id"),
        data.get("parent_id"),
        process_unit_id,
    )
    conn.commit()
    return get_process_unit_by_id(conn, process_unit_id)


def patch_process_unit(
    conn: pyodbc.Connection, process_unit_id: int, data: dict
) -> dict | None:
    existing = get_process_unit_by_id(conn, process_unit_id)
    if existing is None:
        return None
    if not data:
        return existing

    column_map = {
        "tag": "[Tag]",
        "name": "[Name]",
        "description": "[Description]",
        "process_unit_type_id": "[ProcessUnitType_ID]",
        "parent_id": "[Parent_ID]",
    }
    fields = []
    values = []
    for key, col in column_map.items():
        if key in data:
            fields.append(f"{col}=?")
            values.append(data[key])

    cursor = conn.cursor()
    cursor.execute(
        f"UPDATE [dbo].[ProcessUnit] SET {', '.join(fields)} WHERE [ProcessUnit_ID]=?",
        *values,
        process_unit_id,
    )
    conn.commit()
    return get_process_unit_by_id(conn, process_unit_id)


def delete_process_unit(conn: pyodbc.Connection, process_unit_id: int) -> bool:
    cursor = conn.cursor()

    cursor.execute(
        "SELECT COUNT(*) FROM [dbo].[ProcessUnit] WHERE [Parent_ID]=?",
        process_unit_id,
    )
    child_count = cursor.fetchone()[0]
    if child_count > 0:
        raise ValueError(
            f"ProcessUnit {process_unit_id} has {child_count} child unit(s). "
            "Delete or re-parent them first."
        )

    cursor.execute(
        "SELECT COUNT(*) FROM [dbo].[SamplingPoint] WHERE [ProcessUnit_ID]=?",
        process_unit_id,
    )
    sp_count = cursor.fetchone()[0]
    if sp_count > 0:
        raise ValueError(
            f"ProcessUnit {process_unit_id} is linked to {sp_count} sampling point(s). "
            "Unlink them first."
        )

    cursor.execute(
        "DELETE FROM [dbo].[ProcessUnit] WHERE [ProcessUnit_ID]=?",
        process_unit_id,
    )
    cursor.execute("SELECT @@ROWCOUNT")
    deleted = cursor.fetchone()[0] > 0
    conn.commit()
    return deleted
