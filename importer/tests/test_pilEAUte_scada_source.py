"""Tests for PilEAUteSCADASource using a SQLite fixture database."""

from datetime import datetime
from pathlib import Path

import pytest
from sqlalchemy import create_engine

from table_import.config import PilEAUteSCADAStructure, PilEAUteSCADAVariable
from table_import.pilEAUte_scada_source import PilEAUteSCADASource
from table_import.tables import ValueTable

DB_PATH = Path(__file__).parent.parent / "test_data" / "scada_sql" / "float_table.db"
TAG_NAME = "HMI_DO"  # maps to TagIndex=45 in the fixture TagTable


@pytest.fixture
def structure():
    return PilEAUteSCADAStructure(
        server="unused",
        database="unused",
        credentials_path="unused",
        timezone="America/Montreal",
    )


@pytest.fixture
def variable():
    return PilEAUteSCADAVariable(
        name="test_var",
        tag=TAG_NAME,
        parameter_name="test_parameter",
        source_unit_name="mg/L",
        destination_unit_name="mg/L",
    )


@pytest.fixture
def scada_engine():
    return create_engine(f"sqlite:///{DB_PATH}")


@pytest.fixture
def source(structure, variable, scada_engine):
    return PilEAUteSCADASource(structure=structure, variable=variable, engine=scada_engine)


def test_resolve_tag_index(source):
    """_resolve_tag_index must return the integer TagIndex for a known tag name."""
    idx = source._resolve_tag_index(TAG_NAME)
    assert isinstance(idx, int)
    assert idx == 45


def test_resolve_tag_index_unknown_raises(source):
    """_resolve_tag_index must raise ValueError for an unknown tag name."""
    with pytest.raises(ValueError, match="not found"):
        source._resolve_tag_index("NONEXISTENT_TAG_XYZ")


def test_get_last_date(source):
    """get_last_date() must return a valid datetime, not None or epoch."""
    last = source.get_last_date()
    assert isinstance(last, datetime)
    assert last > datetime(2000, 1, 1), f"get_last_date() returned suspiciously old date: {last}"


def test_get_values_since_zero(source):
    """Passing last_ts=0 must return all rows for this tag as a valid ValueTable."""
    vt = source.get_values_since(0.0)
    assert isinstance(vt, ValueTable)
    assert len(vt) > 0
    assert sorted(vt.columns.tolist()) == sorted(ValueTable.acceptable_columns)


def test_get_values_since_cutoff(source):
    """A cutoff near the end must return fewer rows than last_ts=0."""
    all_rows = source.get_values_since(0.0)

    last_ts = all_rows["Timestamp"].max()
    cutoff_ts = float(last_ts) - 1.0  # 1 second before the latest

    partial = source.get_values_since(cutoff_ts)
    assert len(partial) < len(all_rows), (
        f"Expected fewer rows with cutoff near end, got {len(partial)} vs {len(all_rows)}"
    )


def test_values_schema(source):
    """ValueTable must have exactly the 2 acceptable columns."""
    vt = source.get_values_since(0.0)
    assert sorted(vt.columns.tolist()) == sorted(ValueTable.acceptable_columns)


def test_no_new_values(source):
    """Passing a far-future cutoff must return an empty ValueTable without error."""
    far_future_ts = datetime(2099, 1, 1).timestamp()
    vt = source.get_values_since(far_future_ts)
    assert isinstance(vt, ValueTable)
    assert vt.empty
