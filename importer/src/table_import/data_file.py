from __future__ import annotations

import csv
import math
import os
from abc import ABC, abstractmethod, abstractproperty
from dataclasses import dataclass
from datetime import datetime as dt
from datetime import timezone
from typing import Any, List

import numpy as np
import pandas as pd

from table_import.config import (
    BaseVariable,
    BinConfig,
    FileStructure,
    ImageFolderStructure,
    StatusMap,
    TimestampSource,
    VectorFileStructure,
)
from table_import.tables import ValueTable


class MissingFileTypeError(Exception):
    pass


# ---------------------------------------------------------------------------
# Quality code helpers
# ---------------------------------------------------------------------------


def _apply_status_map(
    status_value: str,
    status_map: StatusMap,
    label: str = "",
) -> tuple[bool, int | None]:
    """Map a status string to (keep, quality_code).

    Returns (True, code) if the row should be ingested, (False, None) to skip.
    """
    if status_value in status_map.map:
        return True, status_map.map[status_value]
    if status_map.default_quality_code is not None:
        return True, status_map.default_quality_code
    # Unmapped and no default → skip
    if label:
        print(f"[WARNING] {label}: unmapped status {status_value!r} — row skipped")
    return False, None


# ---------------------------------------------------------------------------
# Scalar DataFile hierarchy
# ---------------------------------------------------------------------------


@dataclass
class DataFile(ABC):
    filepath: str
    file_structure: Any  # FileStructure or TsdbFileStructure
    variable: BaseVariable

    @abstractproperty
    def raw_data(self) -> pd.DataFrame:
        """Returns the data found in the file as a DataFrame"""

    @abstractmethod
    def get_first_date(self) -> pd.Timestamp:
        """Returns the date of the first value in the file."""

    @abstractmethod
    def get_last_date(self) -> pd.Timestamp:
        """Returns the date of the last value in the file."""

    @abstractproperty
    def values(self) -> ValueTable:
        """Returns the values present in the file as a ValueTable"""


class TextDBFile(DataFile):
    def find_time_col_pos(self, header_row: List[Any], time_col_name: str) -> int:
        return header_row.index(time_col_name)

    def get_timestamp_from_row(self, filename: str, structure: FileStructure, row_index: int):
        with open(filename, "rb") as f:
            raw_bytes = f.read()
            cleaned_data = raw_bytes.replace(b"\x00", b"")

        decoded_data = cleaned_data.decode(structure.encoding, errors="ignore")
        rows = list(csv.reader(decoded_data.splitlines(), delimiter=structure.separator))
        time_col_pos = self.find_time_col_pos(rows[structure.header_row_idx], structure.time_column)
        return pd.to_datetime(rows[row_index][time_col_pos], format=structure.dt_format)

    @property
    def raw_data(self) -> pd.DataFrame:
        return pd.read_csv(
            self.filepath,
            sep=self.file_structure.separator,
            encoding=self.file_structure.encoding,
            on_bad_lines="skip",
            header=self.file_structure.header_row_idx,
        )

    def get_first_date(self) -> pd.Timestamp:
        return self.get_timestamp_from_row(
            self.filepath, self.file_structure, self.file_structure.first_valid_row_idx
        )

    def get_last_date(self) -> pd.Timestamp:
        return self.get_timestamp_from_row(
            self.filepath, self.file_structure, self.file_structure.last_valid_row_idx
        )


class RodtoxFile(TextDBFile):
    @property
    def values(self) -> ValueTable:
        df = self.raw_data.copy()
        structure = self.file_structure
        variable = self.variable

        # Row selector: keep only rows for this variable (multi-variable files)
        if structure.variable_column and variable.source_variable_name:
            df = df.loc[df[structure.variable_column] == variable.source_variable_name]

        # Resolve the value column — s::can .par files embed the measurement range
        # in the column name (e.g. "NH4-N [ppm]19.80-0.10_2") which changes on
        # recalibration. Fall back to prefix matching up to the first "]" so that
        # "NH4-N [ppm]71.94-0.10_1" in older files still matches "NH4-N [ppm]".
        value_col = structure.value_column
        if value_col not in df.columns and "]" in value_col:
            prefix = value_col.split("]")[0] + "]"
            matches = [c for c in df.columns if c.startswith(prefix)]
            if matches:
                value_col = matches[0]

        # Replace commas by dots so that values are treated as floats
        df[value_col] = df[value_col].replace({",": "."}, regex=True)
        df[value_col] = pd.to_numeric(df[value_col])

        # Timestamps
        df[structure.time_column] = pd.to_datetime(
            df[structure.time_column], format=structure.dt_format, utc=False
        )
        df[structure.time_column] = df[structure.time_column].dt.tz_localize(
            structure.timezone, nonexistent="shift_forward", ambiguous="NaT"
        )
        df = df.dropna(subset=[structure.time_column])
        df[structure.time_column] = df[structure.time_column].map(
            lambda ts: ts.timestamp() if pd.notna(ts) else float("nan")
        )

        # Quality codes via status_map
        quality_codes: list[int | None] = []
        keep_mask: list[bool] = []
        if structure.status_map is not None:
            for _, row in df.iterrows():
                status_val = str(row[structure.status_map.column])
                keep, code = _apply_status_map(status_val, structure.status_map, self.filepath)
                keep_mask.append(keep)
                quality_codes.append(code)
            df = df[keep_mask].copy()
            df["QualityCode"] = [c for c, k in zip(quality_codes, keep_mask) if k]
        else:
            df["QualityCode"] = None

        df = df.rename(
            columns={
                structure.time_column: "Timestamp",
                value_col: "Value",
            }
        )
        cols = ["Timestamp", "Value", "QualityCode"]
        return ValueTable(df[cols])


class AnaproFile(TextDBFile):
    @property
    def values(self) -> ValueTable:
        df = self.raw_data.copy()
        structure = self.file_structure
        variable = self.variable

        clean_names = {col: col.split("]")[0] for col in df.columns}
        for old, new in clean_names.items():
            if "[" in new:
                clean_names[old] = new + "]"
            if "Temp. " in new:
                clean_names[old] = "Temp."
        df.rename(columns=clean_names, inplace=True)
        df.fillna(0, inplace=True)

        df[structure.time_column] = pd.to_datetime(
            df[structure.time_column], format=structure.dt_format, utc=False
        )
        df[structure.time_column] = (
            df[structure.time_column]
            .dt.tz_localize(structure.timezone, ambiguous="infer")
            .map(lambda ts: ts.timestamp() if pd.notna(ts) else float("nan"))
        )

        # Quality codes via status_map
        quality_codes: list[int | None] = []
        keep_mask: list[bool] = []
        if structure.status_map is not None:
            for _, row in df.iterrows():
                status_val = str(row[structure.status_map.column])
                keep, code = _apply_status_map(status_val, structure.status_map, self.filepath)
                keep_mask.append(keep)
                quality_codes.append(code)
            df = df[keep_mask].copy()
            df["QualityCode"] = [c for c, k in zip(quality_codes, keep_mask) if k]
        else:
            df["QualityCode"] = None

        df = df.rename(
            columns={
                structure.time_column: "Timestamp",
                variable.source_variable_name: "Value",
            }
        )
        df["Value"] = df["Value"] * variable.conversion_factor
        cols = ["Timestamp", "Value", "QualityCode"]
        return ValueTable(df[cols])


class DataCombiner:
    def __init__(self, last_date: dt | None) -> None:
        self.last_db_date = last_date
        self.files: List[DataFile] = []

    @property
    def values(self) -> ValueTable:
        if not self.files:
            df = pd.DataFrame(columns=["Timestamp", "Value", "QualityCode"])
        else:
            dfs = [file.values for file in self.files]
            df = pd.concat(dfs, axis=0)
            df = df.reset_index(drop=True)
            df.sort_values("Timestamp", inplace=True)
            if self.last_db_date:
                df = df.loc[df["Timestamp"] > self.last_db_date.timestamp()]
            df = df.drop_duplicates(subset=["Timestamp"])
        return ValueTable(df[["Timestamp", "Value", "QualityCode"]])

    def add_file(self, file: DataFile) -> None:
        if not self.last_db_date:
            pass
        elif file.get_last_date() < self.last_db_date:
            return
        self.files.append(file)

    @property
    def first_date(self) -> pd.Timestamp:
        return min(file.get_first_date() for file in self.files)

    @property
    def last_date(self) -> pd.Timestamp:
        return max(file.get_last_date() for file in self.files)


def get_file_reader(file_type: str) -> DataFile:
    if file_type in {"rodtox"}:
        return RodtoxFile
    if file_type in {"anapro"}:
        return AnaproFile
    if file_type in {"tsdb"}:
        from table_import.tsdb_file import TsdbFile  # lazy import avoids circular dependency
        return TsdbFile
    raise MissingFileTypeError(f"{file_type} has no defined DataFile class.")


# ---------------------------------------------------------------------------
# Vector file reader (spectrophotometry .fp / .par files)
# ---------------------------------------------------------------------------


class SpectroFile:
    """Reader for tab-separated spectrophotometry files (.fp, .par).

    File format:
    - ``metadata_rows`` rows before the header (skipped)
    - 1 header row: dt_column, [status_column], then bin column labels
    - Data rows: timestamp, [status], float per bin (NaN allowed)
    """

    def __init__(self, filepath: str, structure: VectorFileStructure) -> None:
        self.filepath = filepath
        self.structure = structure
        self._df: pd.DataFrame | None = None

    def _load(self) -> pd.DataFrame:
        if self._df is not None:
            return self._df
        with open(self.filepath, "rb") as f:
            raw = f.read().replace(b"\x00", b"")
        decoded = raw.decode(self.structure.encoding, errors="ignore")
        self._df = pd.read_csv(
            pd.io.common.StringIO(decoded),
            sep=self.structure.separator,
            header=self.structure.header_row_idx,
            skiprows=list(range(self.structure.metadata_rows))
            if self.structure.metadata_rows > 0
            else None,
        )
        return self._df

    def get_last_date(self) -> dt | None:
        """Return timestamp of last row for watermark pre-filtering."""
        df = self._load()
        if df.empty:
            return None
        last_raw = df[self.structure.dt_column].iloc[-1]
        try:
            ts = dt.strptime(str(last_raw).strip(), self.structure.dt_format)
            import pytz
            tz = pytz.timezone(self.structure.timezone)
            ts = tz.localize(ts)
            return ts.astimezone(timezone.utc).replace(tzinfo=None)
        except (ValueError, KeyError):
            return None

    def observations(
        self,
        last_unix_ts: float,
        min_unix_ts: float | None,
        bins: list[BinConfig],
        status_map: StatusMap | None = None,
    ) -> list[dict]:
        """Return a list of vector observations filtered by watermark.

        Each observation: {timestamp: ISO 8601 str, bin_values: list[float|None],
                           quality_code: int|None}
        """
        import pytz

        df = self._load()
        if df.empty:
            return []

        tz = pytz.timezone(self.structure.timezone)
        results = []

        for _, row in df.iterrows():
            # Parse timestamp
            try:
                ts_naive = dt.strptime(str(row[self.structure.dt_column]).strip(), self.structure.dt_format)
            except ValueError:
                continue
            ts_local = tz.localize(ts_naive)
            ts_utc = ts_local.astimezone(timezone.utc)
            unix_ts = ts_utc.timestamp()

            # Watermark filter
            if unix_ts <= last_unix_ts:
                continue
            if min_unix_ts is not None and unix_ts < min_unix_ts:
                continue

            # Quality code from status map
            quality_code: int | None = None
            if status_map is not None:
                status_col = status_map.column
                status_val = str(row.get(status_col, ""))
                keep, quality_code = _apply_status_map(status_val, status_map, self.filepath)
                if not keep:
                    continue

            # Extract bin values
            bin_values: list[float | None] = []
            for b in bins:
                raw_val = row.get(b.source_column)
                if raw_val is None or (isinstance(raw_val, float) and math.isnan(raw_val)):
                    bin_values.append(None)
                else:
                    try:
                        bin_values.append(float(raw_val))
                    except (ValueError, TypeError):
                        bin_values.append(None)

            results.append(
                {
                    "timestamp": ts_utc.isoformat(),
                    "bin_values": bin_values,
                    "quality_code": quality_code,
                }
            )

        return results


# ---------------------------------------------------------------------------
# Image timestamp extraction
# ---------------------------------------------------------------------------


def extract_image_timestamp(
    filepath: str,
    structure: ImageFolderStructure,
) -> dt | None:
    """Extract a UTC-aware datetime from an image file.

    Strategy:
    1. EXIF ``DateTimeOriginal`` (or ``DateTime``) via Pillow.
    2. Filename stem parsed with ``structure.filename_format`` (strptime).
    3. Returns None — caller should log a warning and skip the file.
    """
    import pytz

    tz = pytz.timezone(structure.timezone)

    # --- Strategy 1: EXIF ---
    try:
        from PIL import Image
        from PIL.ExifTags import TAGS

        with Image.open(filepath) as img:
            exif_data = img._getexif()  # type: ignore[attr-defined]
            if exif_data:
                tag_map = {v: k for k, v in TAGS.items()}
                for field in ("DateTimeOriginal", "DateTime"):
                    tag_id = tag_map.get(field)
                    if tag_id and tag_id in exif_data:
                        raw = exif_data[tag_id]
                        ts_naive = dt.strptime(raw, "%Y:%m:%d %H:%M:%S")
                        return tz.localize(ts_naive).astimezone(timezone.utc)
    except Exception:
        pass

    # --- Strategy 2: filename stem ---
    if structure.filename_format:
        stem = os.path.splitext(os.path.basename(filepath))[0]
        try:
            ts_naive = dt.strptime(stem, structure.filename_format)
            return tz.localize(ts_naive).astimezone(timezone.utc)
        except ValueError:
            pass

    # --- Strategy 3: file mtime (opt-in via timestamp_source=mtime) ---
    if structure.timestamp_source == TimestampSource.mtime:
        try:
            mtime = os.path.getmtime(filepath)
            ts_naive = dt.fromtimestamp(mtime)
            return tz.localize(ts_naive).astimezone(timezone.utc)
        except Exception:
            pass

    return None
