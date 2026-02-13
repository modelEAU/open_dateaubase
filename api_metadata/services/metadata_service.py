from datetime import datetime
import pandas as pd

from api_metadata.services.db_client import get_db_connection

def fetch_metadata(limit: int = 200) -> pd.DataFrame:
    conn = get_db_connection()
    try:
        return pd.read_sql(
            f"""
            SELECT TOP {int(limit)}
                Metadata_ID,
                Parameter_ID,
                Unit_ID,
                Purpose_ID,
                Equipment_ID,
                Procedure_ID,
                Condition_ID,
                Sampling_point_ID,
                Contact_ID,
                Project_ID,
                StartDate,
                EndDate
            FROM metadata
            ORDER BY Metadata_ID
            """,
            conn,
        )
    finally:
        conn.close()

def fetch_pairs(query: str):
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(query)
        return cur.fetchall()
    finally:
        conn.close()

def create_or_get_id(table: str, id_col: str, name_col: str, name_value: str) -> int:
    name_value = (name_value or "").strip()
    if not name_value:
        raise ValueError(f"Le champ '{name_col}' est obligatoire.")

    conn = get_db_connection()
    try:
        cur = conn.cursor()

        cur.execute(f"SELECT {id_col} FROM {table} WHERE {name_col} = ?", name_value)
        row = cur.fetchone()
        if row:
            return int(row[0])

        cur.execute(f"SELECT ISNULL(MAX({id_col}), 0) FROM {table}")
        new_id = int(cur.fetchone()[0] or 0) + 1

        cur.execute(
            f"INSERT INTO {table} ({id_col}, {name_col}) VALUES (?, ?)",
            (new_id, name_value),
        )
        conn.commit()
        return new_id
    except:
        conn.rollback()
        raise
    finally:
        conn.close()

def create_metadata(
    equipment_id: int,
    parameter_id: int,
    unit_id: int,
    purpose_id: int,
    sampling_point_id: int,
    project_id: int,
    procedure_id: int,
    contact_id: int,
    condition_id: int,
    start_date,
    end_date=None,
) -> int:
    conn = get_db_connection()
    try:
        cur = conn.cursor()

        cur.execute("SELECT ISNULL(MAX(Metadata_ID), 0) FROM metadata")
        new_metadata_id = int(cur.fetchone()[0] or 0) + 1

        start_ts = int(datetime.combine(start_date, datetime.min.time()).timestamp())
        end_ts = None
        if end_date:
            end_ts = int(datetime.combine(end_date, datetime.min.time()).timestamp())

        cur.execute(
            """
            INSERT INTO metadata
            (Metadata_ID,
            Parameter_ID, Unit_ID, Purpose_ID,
            Equipment_ID, Procedure_ID, Condition_ID,
            Sampling_point_ID, Contact_ID, Project_ID,
            StartDate, EndDate)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                new_metadata_id,
                parameter_id,
                unit_id,
                purpose_id,
                equipment_id,
                procedure_id,
                condition_id,
                sampling_point_id,
                contact_id,
                project_id,
                start_ts,
                end_ts,
            ),
        )

        conn.commit()
        return new_metadata_id
    except:
        conn.rollback()
        raise
    finally:
        conn.close()