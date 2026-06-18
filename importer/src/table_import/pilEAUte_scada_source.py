from dataclasses import dataclass
from datetime import datetime, timezone
from urllib import parse

import pandas as pd
import sqlalchemy
from sqlalchemy import create_engine, text

from table_import.config import PilEAUteSCADAStructure, PilEAUteSCADAVariable
from table_import.tables import ValueTable

_DATETIME_COL = "DateAndTime"
_MILLITM_COL  = "Millitm"
_TAG_INDEX_COL = "TagIndex"
_VALUE_COL = "Val"
_TAG_TABLE = "TagTable"
_TAG_NAME_COL = "TagName"


def _build_scada_engine(structure: PilEAUteSCADAStructure) -> sqlalchemy.Engine:
    """Build a database engine — SQLite when sqlite_path is set, SQL Server otherwise.

    SQL Server connections use a raw ODBC connect string so that named instances
    (e.g. SERVER\\INSTANCE) are handled correctly without port-based resolution.
    """
    if structure.sqlite_path:
        return create_engine(f"sqlite:///{structure.sqlite_path}")
    with open(structure.credentials_path) as f:
        username = f.readline().strip()
        password = f.readline().strip()
    odbc = (
        f"DRIVER={{ODBC Driver 17 for SQL Server}};"
        f"SERVER={structure.server};"
        f"DATABASE={structure.database};"
        f"UID={username};"
        f"PWD={password};"
        f"TrustServerCertificate=yes;"
    )
    url = f"mssql+pyodbc:///?odbc_connect={parse.quote_plus(odbc)}"
    return create_engine(url, fast_executemany=True)


@dataclass
class PilEAUteSCADASource:
    structure: PilEAUteSCADAStructure
    variable: PilEAUteSCADAVariable
    engine: sqlalchemy.Engine  # shared across variables; injected at construction

    def _resolve_tag_index(self, tag: str) -> int:
        """Look up TagIndex from TagTable by TagName."""
        query = text(
            f"SELECT {_TAG_INDEX_COL} FROM {_TAG_TABLE} WHERE {_TAG_NAME_COL} = :tag"
        )
        with self.engine.connect() as conn:
            result = conn.execute(query, {"tag": tag}).scalar()
        if result is None:
            raise ValueError(
                f"Tag {tag!r} not found in {_TAG_TABLE}. "
                "Add the tag to the tag lookup table before importing."
            )
        return int(result)

    def get_last_date(self) -> datetime:
        """Return the most recent DateAndTime for this variable as a naive UTC datetime."""
        tag_index = self._resolve_tag_index(self.variable.tag)
        query = text(
            f"SELECT MAX({_DATETIME_COL}) FROM {self.structure.float_table} "
            f"WHERE {_TAG_INDEX_COL} = :tag"
        )
        with self.engine.connect() as conn:
            result = conn.execute(query, {"tag": tag_index}).scalar()
        if result is None:
            return datetime(1970, 1, 1)
        ts = pd.Timestamp(result)
        if ts.tzinfo is None:
            ts = ts.tz_localize(self.structure.timezone)
        return ts.tz_convert("UTC").tz_localize(None).to_pydatetime()

    def get_values_since(self, last_unix_ts: float) -> ValueTable:
        """
        Fetch all rows for this variable with DateAndTime > last_unix_ts.
        Timestamps are stored in the SCADA timezone; they are converted to UTC Unix seconds.
        """
        tag_index = self._resolve_tag_index(self.variable.tag)

        # Convert cutoff from UTC Unix seconds to SCADA-local naive datetime for WHERE clause
        cutoff_utc = datetime.fromtimestamp(last_unix_ts, tz=timezone.utc)
        cutoff_local = (
            pd.Timestamp(cutoff_utc)
            .tz_convert(self.structure.timezone)
            .tz_localize(None)
            .to_pydatetime()
        )

        query = text(
            f"SELECT {_DATETIME_COL}, {_MILLITM_COL}, {_VALUE_COL} "
            f"FROM {self.structure.float_table} "
            f"WHERE {_TAG_INDEX_COL} = :tag AND {_DATETIME_COL} > :cutoff"
        )
        with self.engine.connect() as conn:
            result = conn.execute(query, {"tag": tag_index, "cutoff": cutoff_local})
            rows = result.fetchall()
            col_names = list(result.keys())

        if not rows:
            return ValueTable(pd.DataFrame(columns=["Timestamp", "Value", "QualityCode"]))

        df = pd.DataFrame(rows, columns=col_names)
        df[_DATETIME_COL] = pd.to_datetime(df[_DATETIME_COL])
        df["Timestamp"] = (
            df[_DATETIME_COL]
            .dt.tz_localize(self.structure.timezone, ambiguous="NaT", nonexistent="NaT")
            .dt.tz_convert("UTC")
            .map(lambda ts: ts.timestamp() if pd.notna(ts) else float("nan"))
            + df[_MILLITM_COL] / 1000.0
        )
        df = df.dropna(subset=["Timestamp"])
        df["Value"] = pd.to_numeric(df[_VALUE_COL]) * self.variable.conversion_factor
        df["QualityCode"] = None
        return ValueTable(df[["Timestamp", "Value", "QualityCode"]])
