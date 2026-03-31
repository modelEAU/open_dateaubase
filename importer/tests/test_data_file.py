from datetime import datetime
from pathlib import Path

import pandas as pd

from table_import.config import FileStructure, TaggedFileVariable
from table_import.data_file import RodtoxFile
from table_import.tables import ValueTable

RODTOX_PATH = str(
    Path(__file__).parent.parent / "test_data" / "rodtox" / "DO" / "DO_log0.csv"
)

RODTOX_STRUCTURE = FileStructure(
    extension=".csv",
    separator=";",
    encoding="UTF-8",
    dt_format="%d.%m.%Y %H:%M:%S",
    time_column="TimeString",
    timezone="US/Eastern",
    value_column="VarValue",
    variable_column="VarName",
    validity_column="Validity",
    validity_flag=1,
    first_valid_row_idx=1,
    last_valid_row_idx=-2,
    header_row_idx=0,
)

RODTOX_VARIABLE = TaggedFileVariable(
    name="do",
    directory_path=str(Path(__file__).parent.parent / "test_data" / "rodtox" / "DO"),
    source_variable_name="HMI_DO",
    tag="HMI_DO",
    parameter_name="Dissolved oxygen",
    source_unit_name="mg/L",
    destination_unit_name="mg/L",
)


def _make_file() -> RodtoxFile:
    return RodtoxFile(
        filepath=RODTOX_PATH, file_structure=RODTOX_STRUCTURE, variable=RODTOX_VARIABLE
    )


def test_rodtox_values_schema():
    """RodtoxFile.values must return a ValueTable with the correct 6 columns."""
    f = _make_file()
    vt = f.values
    assert isinstance(vt, ValueTable)
    assert sorted(vt.columns.tolist()) == sorted(ValueTable.acceptable_columns)
    assert len(vt) > 0


def test_rodtox_get_last_date():
    """get_last_date() must return a Timestamp, not raise an error."""
    f = _make_file()
    last = f.get_last_date()
    assert isinstance(last, pd.Timestamp)
