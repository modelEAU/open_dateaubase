"""Repository functions for ValueBinningAxis and ValueBin CRUD."""

from __future__ import annotations

import pyodbc


def list_binning_axes(conn: pyodbc.Connection) -> list[dict]:
    """Return all ValueBinningAxis rows with unit names."""
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT vba.ValueBinningAxis_ID, vba.Name, vba.Description,
               vba.NumberOfBins, vba.Unit_ID, u.Unit AS UnitName
        FROM [dbo].[ValueBinningAxis] vba
        LEFT JOIN [dbo].[Unit] u ON u.Unit_ID = vba.Unit_ID
        ORDER BY vba.Name
        """
    )
    return [
        {
            "value_binning_axis_id": row[0],
            "name": row[1],
            "description": row[2],
            "number_of_bins": row[3],
            "unit_id": row[4],
            "unit_name": row[5],
        }
        for row in cursor.fetchall()
    ]


def get_binning_axis(conn: pyodbc.Connection, axis_id: int) -> dict | None:
    """Return a single ValueBinningAxis with its bins."""
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT vba.ValueBinningAxis_ID, vba.Name, vba.Description,
               vba.NumberOfBins, vba.Unit_ID, u.Unit AS UnitName
        FROM [dbo].[ValueBinningAxis] vba
        LEFT JOIN [dbo].[Unit] u ON u.Unit_ID = vba.Unit_ID
        WHERE vba.ValueBinningAxis_ID = ?
        """,
        axis_id,
    )
    row = cursor.fetchone()
    if row is None:
        return None

    result = {
        "value_binning_axis_id": row[0],
        "name": row[1],
        "description": row[2],
        "number_of_bins": row[3],
        "unit_id": row[4],
        "unit_name": row[5],
        "bins": [],
    }

    cursor.execute(
        """
        SELECT BinIndex, LowerBound, UpperBound
        FROM [dbo].[ValueBin]
        WHERE ValueBinningAxis_ID = ?
        ORDER BY BinIndex
        """,
        axis_id,
    )
    result["bins"] = [
        {"bin_index": r[0], "lower_bound": r[1], "upper_bound": r[2]}
        for r in cursor.fetchall()
    ]
    return result


def insert_binning_axis(conn: pyodbc.Connection, data: dict) -> int:
    """Insert a new ValueBinningAxis and its bins. Returns the new axis ID."""
    cursor = conn.cursor()
    bins = data["bins"]
    number_of_bins = len(bins)

    cursor.execute(
        """
        INSERT INTO [dbo].[ValueBinningAxis] (Name, Description, NumberOfBins, Unit_ID)
        VALUES (?, ?, ?, ?)
        """,
        data["name"],
        data.get("description"),
        number_of_bins,
        data["unit_id"],
    )
    cursor.execute("SELECT @@IDENTITY")
    axis_id = int(cursor.fetchone()[0])

    for bin_item in bins:
        cursor.execute(
            """
            INSERT INTO [dbo].[ValueBin] (ValueBinningAxis_ID, BinIndex, LowerBound, UpperBound)
            VALUES (?, ?, ?, ?)
            """,
            axis_id,
            bin_item["bin_index"],
            bin_item["lower_bound"],
            bin_item["upper_bound"],
        )

    conn.commit()
    return axis_id


def delete_binning_axis(conn: pyodbc.Connection, axis_id: int) -> None:
    """Delete a ValueBinningAxis and its bins. Raises ValueError if axis is in use."""
    cursor = conn.cursor()

    # Check if axis is referenced by any channels
    cursor.execute(
        "SELECT COUNT(*) FROM [dbo].[ChannelAxis] WHERE ValueBinningAxis_ID = ?",
        axis_id,
    )
    count = cursor.fetchone()[0]
    if count > 0:
        raise ValueError("Axis is in use by channels — cannot delete")

    # Delete bins first, then the axis
    cursor.execute(
        "DELETE FROM [dbo].[ValueBin] WHERE ValueBinningAxis_ID = ?",
        axis_id,
    )
    cursor.execute(
        "DELETE FROM [dbo].[ValueBinningAxis] WHERE ValueBinningAxis_ID = ?",
        axis_id,
    )
    conn.commit()


def lookup_binning_axes(conn: pyodbc.Connection) -> list[dict]:
    """Return lightweight list for dropdowns."""
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT ValueBinningAxis_ID, Name, NumberOfBins
        FROM [dbo].[ValueBinningAxis]
        ORDER BY Name
        """
    )
    return [
        {
            "value_binning_axis_id": row[0],
            "name": row[1],
            "number_of_bins": row[2],
        }
        for row in cursor.fetchall()
    ]
