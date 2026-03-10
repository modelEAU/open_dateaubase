import struct
from dataclasses import dataclass
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

from table_import.data_file import DataFile
from table_import.tables import ValueTable

_STRUCT_FORMAT = "<qqBBBBd"
_RECORD_SIZE = 28
_NET_EPOCH = datetime(1, 1, 1)
_TICKS_PER_SECOND = 10_000_000
_UNIX_OFFSET_SECONDS = 62_135_596_800.0


def _ticks_to_datetime(ticks: int) -> datetime:
    """Convert .NET ticks (100-ns intervals since 0001-01-01) to a naive UTC datetime."""
    return _NET_EPOCH + timedelta(microseconds=ticks // 10)


def _ticks_to_unix_seconds(ticks: int) -> float:
    """Convert .NET ticks to Unix seconds (seconds since 1970-01-01 UTC)."""
    return ticks / _TICKS_PER_SECOND - _UNIX_OFFSET_SECONDS


@dataclass
class TsdbFile(DataFile):
    """
    DataFile subclass for TSDB binary files (28-byte records, .NET ticks).

    Binary record layout (struct '<qqBBBBd'):
      - dateLong1 (int64): .NET ticks (100-ns since 0001-01-01)
      - dateLong2 (int64): always 0
      - metadata_byte (uint8): embedded metadata byte
      - 3 × reserved (uint8)
      - value (float64)
    """

    @property
    def raw_data(self) -> pd.DataFrame:
        records = []
        with open(self.filepath, "rb") as f:
            data = f.read()
        n_records = len(data) // _RECORD_SIZE
        for i in range(n_records):
            chunk = data[i * _RECORD_SIZE : (i + 1) * _RECORD_SIZE]
            ticks, _, metadata_byte, _, _, _, value = struct.unpack(_STRUCT_FORMAT, chunk)
            records.append((ticks, metadata_byte, value))
        return pd.DataFrame(records, columns=["ticks", "metadata_byte", "value"])

    def get_first_date(self) -> datetime:
        with open(self.filepath, "rb") as f:
            chunk = f.read(_RECORD_SIZE)
        ticks, *_ = struct.unpack(_STRUCT_FORMAT, chunk)
        return _ticks_to_datetime(ticks)

    def get_last_date(self) -> datetime:
        """Reads only the last record (seek to end) — O(1) regardless of file size."""
        with open(self.filepath, "rb") as f:
            f.seek(-_RECORD_SIZE, 2)
            chunk = f.read(_RECORD_SIZE)
        ticks, *_ = struct.unpack(_STRUCT_FORMAT, chunk)
        return _ticks_to_datetime(ticks)

    @property
    def values(self) -> ValueTable:
        df = self.raw_data.copy()
        df["Timestamp"] = df["ticks"].apply(_ticks_to_unix_seconds)
        df["Value"] = df["value"] * self.variable.scaling_factor
        df["Metadata_ID"] = self.variable.metadata_id
        df["Number_of_experiment"] = 1
        df["Comment_ID"] = np.nan
        df["Value_ID"] = df.index
        return ValueTable(df[ValueTable.acceptable_columns])
