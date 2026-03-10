from datetime import datetime
from pathlib import Path

import pytest
from sqlalchemy import create_engine

from table_import.config import ScadaSqlStructure, ScadaVariable
from table_import.scada_sql_source import SqlServerSource
from table_import.tables import ValueTable

DB_PATH = Path(__file__).parent.parent / "test_data" / "scada_sql" / "float_table.db"
TAG_INDEX = 45  # a TagIndex value that appears in the fixture TSV


@pytest.fixture
def structure():
    return ScadaSqlStructure(
        server="unused",
        database="unused",
        credentials_path="unused",
        table="FloatTable_hedi",
        datetime_column="DateAndTime",
        tag_index_column="TagIndex",
        value_column="Val",
        timezone="America/Montreal",
    )


@pytest.fixture
def variable():
    return ScadaVariable(name="test_var", tag_index=TAG_INDEX, metadata_id=999, scaling_factor=1.0)


@pytest.fixture
def scada_engine():
    return create_engine(f"sqlite:///{DB_PATH}")


@pytest.fixture
def source(structure, variable, scada_engine):
    return SqlServerSource(structure=structure, variable=variable, engine=scada_engine)


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

    # Use a cutoff just before the last timestamp
    last_ts = all_rows["Timestamp"].max()
    cutoff_ts = float(last_ts) - 1.0  # 1 second before the latest

    partial = source.get_values_since(cutoff_ts)
    assert len(partial) < len(all_rows), (
        f"Expected fewer rows with cutoff near end, got {len(partial)} vs {len(all_rows)}"
    )


def test_values_schema(source):
    """ValueTable must have exactly the 6 acceptable columns."""
    vt = source.get_values_since(0.0)
    assert sorted(vt.columns.tolist()) == sorted(ValueTable.acceptable_columns)


def test_no_new_values(source):
    """Passing a far-future cutoff must return an empty ValueTable without error."""
    far_future_ts = datetime(2099, 1, 1).timestamp()
    vt = source.get_values_since(far_future_ts)
    assert isinstance(vt, ValueTable)
    assert vt.empty
