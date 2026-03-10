import os
import time
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from table_import.config import TsdbFileStructure, TsdbVariable
from table_import.tables import ValueTable
from table_import.tsdb_file import (
    TsdbFile,
    _NET_EPOCH,
    _RECORD_SIZE,
    _ticks_to_datetime,
    _ticks_to_unix_seconds,
)

TSDB_PATH = str(
    Path(__file__).parent.parent / "test_data" / "basestation" / "100924-135506_TurbR300_2025.tsdb"
)


def _make_file(scaling_factor: float = 1.0) -> TsdbFile:
    struct = TsdbFileStructure(timezone="America/Montreal")
    var = TsdbVariable(name="turb", directory_path=".", metadata_id=1, scaling_factor=scaling_factor)
    return TsdbFile(filepath=TSDB_PATH, file_structure=struct, variable=var)


def test_record_size():
    """File size must be an exact multiple of 28 bytes."""
    size = os.path.getsize(TSDB_PATH)
    assert size % _RECORD_SIZE == 0, f"File size {size} is not divisible by {_RECORD_SIZE}"


def test_get_last_date_returns_plausible_timestamp():
    """dateLong1 ticks → datetime must land in a reasonable range (2020–2030)."""
    f = _make_file()
    last = f.get_last_date()
    assert isinstance(last, datetime)
    assert datetime(2020, 1, 1) <= last <= datetime(2030, 12, 31), (
        f"get_last_date() returned {last}, which is outside the expected range"
    )


def test_get_last_date_faster_than_full_read():
    """get_last_date() seeks to the last record only — should be much faster than reading all records."""
    f = _make_file()

    t0 = time.perf_counter()
    f.get_last_date()
    t_seek = time.perf_counter() - t0

    t0 = time.perf_counter()
    _ = f.raw_data  # reads every record
    t_full = time.perf_counter() - t0

    assert t_seek < t_full, (
        f"get_last_date() took {t_seek:.4f}s but full read took {t_full:.4f}s"
    )


def test_values_returns_valid_value_table():
    """values property must return a ValueTable with all 6 acceptable columns and no NaN timestamps."""
    f = _make_file()
    vt = f.values
    assert isinstance(vt, ValueTable)
    assert sorted(vt.columns.tolist()) == sorted(ValueTable.acceptable_columns)
    assert vt["Timestamp"].notna().all(), "Some Timestamp values are NaN"
    assert len(vt) > 0


def test_values_scaling_factor():
    """scaling_factor=2.0 must double every non-NaN Value compared to scaling_factor=1.0."""
    f1 = _make_file(scaling_factor=1.0)
    f2 = _make_file(scaling_factor=2.0)
    v1 = f1.values["Value"].reset_index(drop=True)
    v2 = f2.values["Value"].reset_index(drop=True)
    # TSDB files may contain NaN float records (legitimate "no data" markers);
    # NaN == NaN is always False, so compare only finite values
    mask = v1.notna() & v2.notna()
    assert mask.any(), "No non-NaN values found to compare"
    assert (v2[mask] == v1[mask] * 2).all(), "scaling_factor=2.0 did not double all values"


def test_tick_conversion_roundtrip():
    """datetime → ticks → datetime must round-trip within 1 second."""
    test_dt = datetime(2025, 6, 15, 10, 30, 0)
    delta = test_dt - _NET_EPOCH
    ticks = int(delta.total_seconds() * 10_000_000)
    recovered = _ticks_to_datetime(ticks)
    assert abs((recovered - test_dt).total_seconds()) < 1, (
        f"Round-trip failed: original={test_dt}, recovered={recovered}"
    )
