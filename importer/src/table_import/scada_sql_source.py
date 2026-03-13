from dataclasses import dataclass
from datetime import datetime, timezone
from urllib import parse

import numpy as np
import pandas as pd
import sqlalchemy
from sqlalchemy import create_engine, text

from table_import.config import ScadaSqlStructure, ScadaVariable
from table_import.tables import ValueTable


def _build_scada_engine(structure: ScadaSqlStructure) -> sqlalchemy.Engine:
    """Build a SQL Server engine from a credentials file (mirrors dateaubase.connect_remote)."""
    with open(structure.credentials_path) as f:
        username = f.readline().strip()
        password = parse.quote_plus(f.readline().strip())
    url = (
        f"mssql+pyodbc://{username}:{password}@{structure.server}:1433"
        f"/{structure.database}?driver=ODBC+Driver+17+for+SQL+Server"
    )
    return create_engine(url, connect_args={"connect_timeout": 2}, fast_executemany=True)


@dataclass
class SqlServerSource:
    structure: ScadaSqlStructure
    variable: ScadaVariable
    engine: sqlalchemy.Engine  # shared across variables; injected at construction

    def get_last_date(self) -> datetime:
        """Return the most recent DateAndTime for this variable as a naive UTC datetime."""
        tbl = self.structure.table
        dt_col = self.structure.datetime_column
        tag_col = self.structure.tag_index_column
        query = text(f"SELECT MAX({dt_col}) FROM {tbl} WHERE {tag_col} = :tag")
        with self.engine.connect() as conn:
            result = conn.execute(query, {"tag": self.variable.tag_index}).scalar()
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
        tbl = self.structure.table
        dt_col = self.structure.datetime_column
        val_col = self.structure.value_column
        tag_col = self.structure.tag_index_column

        # Convert cutoff from UTC Unix seconds to SCADA-local naive datetime for WHERE clause
        cutoff_utc = datetime.fromtimestamp(last_unix_ts, tz=timezone.utc)
        cutoff_local = (
            pd.Timestamp(cutoff_utc)
            .tz_convert(self.structure.timezone)
            .tz_localize(None)
            .to_pydatetime()
        )

        query = text(
            f"SELECT {dt_col}, {val_col} FROM {tbl} "
            f"WHERE {tag_col} = :tag AND {dt_col} > :cutoff"
        )
        with self.engine.connect() as conn:
            result = conn.execute(query, {"tag": self.variable.tag_index, "cutoff": cutoff_local})
            rows = result.fetchall()
            col_names = list(result.keys())

        if not rows:
            return ValueTable(pd.DataFrame(columns=ValueTable.acceptable_columns))

        df = pd.DataFrame(rows, columns=col_names)
        df[dt_col] = pd.to_datetime(df[dt_col])
        # Use .timestamp() to get Unix seconds — avoids datetime64[us] vs [ns] ambiguity
        # (pandas 2.x stores tz-aware datetimes as datetime64[us], so astype(int64) // 1e9 is wrong)
        df["Timestamp"] = (
            df[dt_col]
            .dt.tz_localize(self.structure.timezone, ambiguous="NaT", nonexistent="NaT")
            .dt.tz_convert("UTC")
            .map(lambda ts: ts.timestamp() if pd.notna(ts) else float("nan"))
        )
        df = df.dropna(subset=["Timestamp"])
        df["Value"] = pd.to_numeric(df[val_col]) * self.variable.conversion_factor
        df["Metadata_ID"] = self.variable.metadata_id
        df["Number_of_experiment"] = 1
        df["Comment_ID"] = np.nan
        df["Value_ID"] = range(len(df))
        return ValueTable(df[ValueTable.acceptable_columns])
