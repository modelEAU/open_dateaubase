"""Repository functions for ValueBinningAxis and ValueBin CRUD."""

from __future__ import annotations

import pyodbc


def list_binning_axes(conn: pyodbc.Connection) -> list[dict]:
    """Return all ValueBinningAxis rows with unit names."""
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT vba.ValueBinningAxis_ID, vba.Name, vba.Description,
               vba.NumberOfBins, vba.Unit_ID, u.Unit AS UnitName,
               bm.Name AS BinModeName
        FROM [dbo].[ValueBinningAxis] vba
        LEFT JOIN [dbo].[Unit] u ON u.Unit_ID = vba.Unit_ID
        LEFT JOIN [dbo].[BinMode] bm ON bm.BinMode_ID = vba.BinMode_ID
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
            "bin_mode": row[6],
        }
        for row in cursor.fetchall()
    ]


def get_binning_axis(conn: pyodbc.Connection, axis_id: int) -> dict | None:
    """Return a single ValueBinningAxis with its bins."""
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT vba.ValueBinningAxis_ID, vba.Name, vba.Description,
               vba.NumberOfBins, vba.Unit_ID, u.Unit AS UnitName,
               bm.Name AS BinModeName
        FROM [dbo].[ValueBinningAxis] vba
        LEFT JOIN [dbo].[Unit] u ON u.Unit_ID = vba.Unit_ID
        LEFT JOIN [dbo].[BinMode] bm ON bm.BinMode_ID = vba.BinMode_ID
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
        "bin_mode": row[6],
        "bins": [],
    }

    cursor.execute(
        """
        SELECT BinIndex, LowerBound, UpperBound, NominalValue
        FROM [dbo].[ValueBin]
        WHERE ValueBinningAxis_ID = ?
        ORDER BY BinIndex
        """,
        axis_id,
    )
    result["bins"] = [
        {
            "bin_index": r[0],
            "lower_bound": r[1],
            "upper_bound": r[2],
            "nominal_value": r[3],
        }
        for r in cursor.fetchall()
    ]
    return result


def _resolve_bin_mode_id(cursor: pyodbc.Cursor, bin_mode_name: str) -> int:
    """Look up BinMode_ID by name. Raises ValueError if not found."""
    cursor.execute(
        "SELECT BinMode_ID FROM [dbo].[BinMode] WHERE Name = ?",
        bin_mode_name,
    )
    row = cursor.fetchone()
    if row is None:
        raise ValueError(f"Unknown bin_mode: {bin_mode_name!r}")
    return int(row[0])


def insert_binning_axis(conn: pyodbc.Connection, data: dict) -> int:
    """Insert a new ValueBinningAxis and its bins. Returns the new axis ID."""
    cursor = conn.cursor()
    bins = data["bins"]
    number_of_bins = len(bins)
    bin_mode_id = _resolve_bin_mode_id(cursor, data["bin_mode"])

    cursor.execute(
        """
        INSERT INTO [dbo].[ValueBinningAxis] (Name, Description, NumberOfBins, Unit_ID, BinMode_ID)
        VALUES (?, ?, ?, ?, ?)
        """,
        data["name"],
        data.get("description"),
        number_of_bins,
        data["unit_id"],
        bin_mode_id,
    )
    cursor.execute("SELECT @@IDENTITY")
    axis_id = int(cursor.fetchone()[0])

    for bin_item in bins:
        cursor.execute(
            """
            INSERT INTO [dbo].[ValueBin]
                (ValueBinningAxis_ID, BinIndex, LowerBound, UpperBound, NominalValue)
            VALUES (?, ?, ?, ?, ?)
            """,
            axis_id,
            bin_item["bin_index"],
            bin_item.get("lower_bound"),
            bin_item.get("upper_bound"),
            bin_item.get("nominal_value"),
        )

    conn.commit()
    return axis_id


def patch_binning_axis(conn: pyodbc.Connection, axis_id: int, data: dict) -> dict | None:
    """Partial update of a ValueBinningAxis. Replaces bins if 'bins' key is present."""
    if get_binning_axis(conn, axis_id) is None:
        return None

    cursor = conn.cursor()
    fields: list[str] = []
    values: list = []

    if "name" in data:
        fields.append("[Name]=?")
        values.append(data["name"])
    if "description" in data:
        fields.append("[Description]=?")
        values.append(data["description"])
    if "unit_id" in data:
        fields.append("[Unit_ID]=?")
        values.append(data["unit_id"])
    if "bin_mode" in data:
        bin_mode_id = _resolve_bin_mode_id(cursor, data["bin_mode"])
        fields.append("[BinMode_ID]=?")
        values.append(bin_mode_id)

    bins = data.get("bins")
    if bins is not None:
        fields.append("[NumberOfBins]=?")
        values.append(len(bins))

    if fields:
        values.append(axis_id)
        cursor.execute(
            f"UPDATE [dbo].[ValueBinningAxis] SET {', '.join(fields)} WHERE [ValueBinningAxis_ID]=?",
            *values,
        )

    if bins is not None:
        cursor.execute(
            "DELETE FROM [dbo].[ValueBin] WHERE ValueBinningAxis_ID=?",
            axis_id,
        )
        for bin_item in bins:
            cursor.execute(
                """
                INSERT INTO [dbo].[ValueBin]
                    (ValueBinningAxis_ID, BinIndex, LowerBound, UpperBound, NominalValue)
                VALUES (?, ?, ?, ?, ?)
                """,
                axis_id,
                bin_item["bin_index"],
                bin_item.get("lower_bound"),
                bin_item.get("upper_bound"),
                bin_item.get("nominal_value"),
            )

    conn.commit()
    return get_binning_axis(conn, axis_id)


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


def resolve_binning_axis(conn: pyodbc.Connection, data: dict) -> dict:
    """Find-or-create a ValueBinningAxis by name + bin fingerprint.

    - Resolves unit_name → Unit_ID.
    - If no axis with that name exists: creates it, returns {axis_id, created=True}.
    - If an axis exists: compares each bin field that the request provides.
      DB having extra fields (e.g. bounds when request only has nominal) is OK.
      Any mismatch raises ValueError (caller maps to HTTP 409).
    - Returns {axis_id, created=False, warnings=[]} on match.
    """
    cursor = conn.cursor()

    # Resolve unit_name → Unit_ID
    cursor.execute("SELECT Unit_ID FROM [dbo].[Unit] WHERE Unit = ?", data["unit_name"])
    unit_row = cursor.fetchone()
    if unit_row is None:
        raise ValueError(f"Unit not found: {data['unit_name']!r}")
    unit_id = int(unit_row[0])

    # Look up axis by name
    cursor.execute(
        "SELECT ValueBinningAxis_ID FROM [dbo].[ValueBinningAxis] WHERE Name = ?",
        data["name"],
    )
    existing = cursor.fetchone()

    if existing is None:
        # Create new axis
        axis_id = insert_binning_axis(
            conn,
            {
                "name": data["name"],
                "description": data.get("description"),
                "unit_id": unit_id,
                "bin_mode": data["bin_mode"],
                "bins": data["bins"],
            },
        )
        return {"axis_id": axis_id, "created": True, "warnings": []}

    axis_id = int(existing[0])

    # Fetch existing bins
    cursor.execute(
        """
        SELECT BinIndex, LowerBound, UpperBound, NominalValue
        FROM [dbo].[ValueBin]
        WHERE ValueBinningAxis_ID = ?
        ORDER BY BinIndex
        """,
        axis_id,
    )
    db_bins = {
        row[0]: {"lower_bound": row[1], "upper_bound": row[2], "nominal_value": row[3]}
        for row in cursor.fetchall()
    }

    request_bins = data["bins"]
    TOL = 1e-6

    for req_bin in request_bins:
        idx = req_bin["bin_index"]
        if idx not in db_bins:
            raise ValueError(
                f"Axis {data['name']!r} fingerprint mismatch: "
                f"bin_index {idx} not found in DB"
            )
        db_bin = db_bins[idx]
        for field in ("lower_bound", "upper_bound", "nominal_value"):
            req_val = req_bin.get(field)
            if req_val is None:
                continue  # not provided in request — DB superset allowed
            db_val = db_bin[field]
            if db_val is None or abs(float(req_val) - float(db_val)) > TOL:
                raise ValueError(
                    f"Axis {data['name']!r} fingerprint mismatch at bin_index {idx}: "
                    f"{field} request={req_val} DB={db_val}"
                )

    return {"axis_id": axis_id, "created": False, "warnings": []}


def lookup_binning_axes(conn: pyodbc.Connection) -> list[dict]:
    """Return lightweight list for dropdowns."""
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT vba.ValueBinningAxis_ID, vba.Name, vba.NumberOfBins, bm.Name AS BinModeName
        FROM [dbo].[ValueBinningAxis] vba
        LEFT JOIN [dbo].[BinMode] bm ON bm.BinMode_ID = vba.BinMode_ID
        ORDER BY vba.Name
        """
    )
    return [
        {
            "value_binning_axis_id": row[0],
            "name": row[1],
            "number_of_bins": row[2],
            "bin_mode": row[3],
        }
        for row in cursor.fetchall()
    ]
