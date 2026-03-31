"""End-to-end tests for the table_import system.

These tests verify that the import system can:
1. Read data from various file formats (CSV, TSDB, SCADA SQL)
2. Ingest data via the REST API
3. Store data correctly in the database

Requirements:
- Running MSSQL database (marked with @pytest.mark.db)
- API server running at the configured API_BASE_URL

Usage:
    # Start the database and apply migrations
    docker-compose up -d db

    # Start the API server (in another terminal)
    cd /path/to/project && uvicorn api.main:app --reload --port 8000

    # Run the e2e tests
    cd importer && pytest tests/test_e2e_import.py -v --db
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path

import pytest
import httpx

import sys
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from table_import.api_client import DateaubaseClient, ApiError
from table_import.config import (
    ApiConfig,
    Config,
    FileStructure,
    PilEAUteSCADAConfig,
    PilEAUteSCADAStructure,
    PilEAUteSCADAVariable,
    TaggedFileConfig,
    TaggedFileVariable,
    TaggedTsdbConfig,
    TaggedTsdbVariable,
    TaglessFileConfig,
    TaglessFileVariable,
    TaglessTsdbConfig,
    TaglessTsdbVariable,
    TsdbFileStructure,
)
from table_import.import_script import main as import_main

# -----------------------------------------------------------------------------
# Test Data Paths
# -----------------------------------------------------------------------------

TEST_DATA_DIR = Path(__file__).parent.parent / "test_data"
RODTOX_DO_PATH = TEST_DATA_DIR / "rodtox" / "DO"
TSDB_PATH = TEST_DATA_DIR / "basestation"
SCADA_DB_PATH = TEST_DATA_DIR / "scada_sql" / "float_table.db"

# -----------------------------------------------------------------------------
# Test Configuration
# -----------------------------------------------------------------------------

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000/api/v1")

TEST_DAS_NAME = "e2e_test_das"
TEST_TAG = "e2e/test/do"
TEST_EQUIPMENT_NAME = "e2e_test_equipment"
TEST_PARAMETER_NAME = "e2e_test_parameter"
TEST_UNIT_NAME = "e2e_test_unit"

# -----------------------------------------------------------------------------
# Fixtures
# -----------------------------------------------------------------------------


@pytest.fixture(scope="module")
def api_client():
    with DateaubaseClient(API_BASE_URL) as client:
        yield client


@pytest.fixture(scope="module")
def db_connection():
    import pyodbc
    from api.config import settings

    conn_str = (
        f"DRIVER={{{settings.db_driver}}};"
        f"SERVER={settings.db_host},{settings.db_port};"
        f"DATABASE={settings.db_name};"
        f"UID={settings.db_user};"
        f"PWD={settings.db_password};"
        "Encrypt=no;"
        "TrustServerCertificate=yes;"
    )
    conn = pyodbc.connect(conn_str)
    yield conn
    conn.close()


@pytest.fixture(scope="module", autouse=True)
def setup_test_data(db_connection):
    cursor = db_connection.cursor()
    cleanup_test_data(cursor)

    cursor.execute("INSERT INTO Unit (Unit) VALUES (?)", (TEST_UNIT_NAME,))
    db_connection.commit()

    cursor.execute(
        "INSERT INTO Parameter (Parameter_name, Unit_ID) SELECT ?, Unit_ID FROM Unit WHERE Unit = ?",
        (TEST_PARAMETER_NAME, TEST_UNIT_NAME),
    )
    db_connection.commit()

    yield

    cleanup_test_data(cursor)
    db_connection.commit()
    cursor.close()


def cleanup_test_data(cursor):
    cursor.execute("""
        DELETE FROM Value WHERE Channel_ID IN (
            SELECT c.Channel_ID FROM Channel c
            JOIN SignalPort sp ON c.SignalPort_ID = sp.SignalPort_ID
            JOIN DataAcquisitionSystem das ON sp.DAS_ID = das.DAS_ID
            WHERE das.DAS_Name = ?
        )
    """, (TEST_DAS_NAME,))
    cursor.execute("""
        DELETE FROM Channel WHERE SignalPort_ID IN (
            SELECT sp.SignalPort_ID FROM SignalPort sp
            JOIN DataAcquisitionSystem das ON sp.DAS_ID = das.DAS_ID
            WHERE das.DAS_Name = ?
        )
    """, (TEST_DAS_NAME,))
    cursor.execute("""
        DELETE FROM SignalPort WHERE DAS_ID IN (
            SELECT DAS_ID FROM DataAcquisitionSystem WHERE DAS_Name = ?
        )
    """, (TEST_DAS_NAME,))
    cursor.execute("DELETE FROM DataAcquisitionSystem WHERE DAS_Name = ?", (TEST_DAS_NAME,))
    cursor.execute("DELETE FROM Parameter WHERE Parameter_name = ?", (TEST_PARAMETER_NAME,))
    cursor.execute("DELETE FROM Unit WHERE Unit = ?", (TEST_UNIT_NAME,))


# -----------------------------------------------------------------------------
# Helper Functions
# -----------------------------------------------------------------------------


def count_values_for_channel(db_connection, channel_id: int) -> int:
    cursor = db_connection.cursor()
    cursor.execute("SELECT COUNT(*) FROM Value WHERE Channel_ID = ?", (channel_id,))
    result = cursor.fetchone()
    return result[0] if result else 0


def resolve_channel_id(api_client: DateaubaseClient, *, mode: str, **kwargs) -> int:
    """Resolve a channel_id via the API for a given set of stream-identity kwargs."""
    if mode == "tagless":
        channel_id, _ = api_client.resolve_channel_tagless(**kwargs)
    else:
        channel_id, _ = api_client.resolve_channel(**kwargs)
    return channel_id


# -----------------------------------------------------------------------------
# E2E Tests — tagless file (Rodtox CSV)
# -----------------------------------------------------------------------------


@pytest.mark.db
def test_e2e_rodtox_csv_import(api_client, db_connection):
    """Tagless file source: import Rodtox CSV and verify row count."""
    cfg = Config(
        api_config=ApiConfig(api_url=API_BASE_URL),
        file_configs=[
            TaglessFileConfig(
                name="rodtox",
                mode="tagless",
                das_name=TEST_DAS_NAME,
                file_structure=FileStructure(
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
                ),
                variables=[
                    TaglessFileVariable(
                        name="do",
                        directory_path=str(RODTOX_DO_PATH),
                        source_variable_name="HMI_DO",
                        equipment_name=TEST_EQUIPMENT_NAME,
                        parameter_name=TEST_PARAMETER_NAME,
                        source_unit_name=TEST_UNIT_NAME,
                        destination_unit_name=TEST_UNIT_NAME,
                    )
                ],
            )
        ],
    )

    import_main(cfg, dry_run=False)

    channel_id = resolve_channel_id(
        api_client,
        mode="tagless",
        das_name=TEST_DAS_NAME,
        equipment_name=TEST_EQUIPMENT_NAME,
        parameter_name=TEST_PARAMETER_NAME,
        unit_name=TEST_UNIT_NAME,
    )
    count = count_values_for_channel(db_connection, channel_id)
    assert count > 0, f"Expected values to be inserted, got {count}"
    print(f"✓ Rodtox CSV: {count} values imported")


# -----------------------------------------------------------------------------
# E2E Tests — tagless TSDB (basestation)
# -----------------------------------------------------------------------------


@pytest.mark.db
def test_e2e_tsdb_import(api_client, db_connection):
    """Tagless TSDB source: import basestation TSDB file and verify row count."""
    test_param = TEST_PARAMETER_NAME + "_tsdb"

    import pyodbc
    from api.config import settings
    conn_str = (
        f"DRIVER={{{settings.db_driver}}};"
        f"SERVER={settings.db_host},{settings.db_port};"
        f"DATABASE={settings.db_name};"
        f"UID={settings.db_user};"
        f"PWD={settings.db_password};"
        "Encrypt=no;TrustServerCertificate=yes;"
    )
    with pyodbc.connect(conn_str) as conn:
        conn.cursor().execute(
            "INSERT INTO Parameter (Parameter_name, Unit_ID) SELECT ?, Unit_ID FROM Unit WHERE Unit = ?",
            (test_param, TEST_UNIT_NAME),
        )
        conn.commit()

    try:
        cfg = Config(
            api_config=ApiConfig(api_url=API_BASE_URL),
            tsdb_configs=[
                TaglessTsdbConfig(
                    name="tsdb",
                    mode="tagless",
                    das_name=TEST_DAS_NAME,
                    tsdb_structure=TsdbFileStructure(timezone="America/Montreal"),
                    variables=[
                        TaglessTsdbVariable(
                            name="turb",
                            directory_path=str(TSDB_PATH),
                            equipment_name=TEST_EQUIPMENT_NAME,
                            parameter_name=test_param,
                            source_unit_name=TEST_UNIT_NAME,
                            destination_unit_name=TEST_UNIT_NAME,
                        )
                    ],
                )
            ],
        )

        import_main(cfg, dry_run=False)

        channel_id = resolve_channel_id(
            api_client,
            mode="tagless",
            das_name=TEST_DAS_NAME,
            equipment_name=TEST_EQUIPMENT_NAME,
            parameter_name=test_param,
            unit_name=TEST_UNIT_NAME,
        )
        count = count_values_for_channel(db_connection, channel_id)
        assert count > 0, f"Expected values to be inserted, got {count}"
        print(f"✓ TSDB: {count} values imported")

    finally:
        with pyodbc.connect(conn_str) as conn:
            conn.cursor().execute("DELETE FROM Parameter WHERE Parameter_name = ?", (test_param,))
            conn.commit()


# -----------------------------------------------------------------------------
# E2E Tests — tagged SCADA SQL (pilEAUte fixture)
# -----------------------------------------------------------------------------


@pytest.mark.db
def test_e2e_scada_sql_import(api_client, db_connection):
    """Tagged SCADA SQL source: import from SQLite fixture and verify row count."""
    test_param = TEST_PARAMETER_NAME + "_scada"

    import pyodbc
    from api.config import settings
    conn_str = (
        f"DRIVER={{{settings.db_driver}}};"
        f"SERVER={settings.db_host},{settings.db_port};"
        f"DATABASE={settings.db_name};"
        f"UID={settings.db_user};"
        f"PWD={settings.db_password};"
        "Encrypt=no;TrustServerCertificate=yes;"
    )
    with pyodbc.connect(conn_str) as conn:
        conn.cursor().execute(
            "INSERT INTO Parameter (Parameter_name, Unit_ID) SELECT ?, Unit_ID FROM Unit WHERE Unit = ?",
            (test_param, TEST_UNIT_NAME),
        )
        conn.commit()

    credentials_path = TEST_DATA_DIR / "scada_sql" / "test_credentials.txt"
    credentials_path.write_text("SA\nStrongPwd123!\n")

    try:
        # Monkey-patch engine to use SQLite fixture instead of SQL Server
        from sqlalchemy import create_engine
        from table_import import pilEAUte_scada_source as _mod
        _original_build = _mod._build_scada_engine

        def _sqlite_engine(_struct):
            return create_engine(f"sqlite:///{SCADA_DB_PATH}")

        _mod._build_scada_engine = _sqlite_engine

        cfg = Config(
            api_config=ApiConfig(api_url=API_BASE_URL),
            scada_sql_configs=[
                PilEAUteSCADAConfig(
                    name="scada",
                    das_name=TEST_DAS_NAME,
                    scada_structure=PilEAUteSCADAStructure(
                        server="localhost",
                        database="test",
                        credentials_path=str(credentials_path),
                        timezone="America/Montreal",
                    ),
                    variables=[
                        PilEAUteSCADAVariable(
                            name="do",
                            tag="HMI_DO",
                            parameter_name=test_param,
                            source_unit_name=TEST_UNIT_NAME,
                            destination_unit_name=TEST_UNIT_NAME,
                        )
                    ],
                )
            ],
        )

        import_main(cfg, dry_run=False)

        channel_id = resolve_channel_id(
            api_client,
            mode="tagged",
            das_name=TEST_DAS_NAME,
            tag="HMI_DO",
            parameter_name=test_param,
            unit_name=TEST_UNIT_NAME,
        )
        count = count_values_for_channel(db_connection, channel_id)
        assert count > 0, f"Expected values to be inserted, got {count}"
        print(f"✓ SCADA SQL: {count} values imported")

    finally:
        _mod._build_scada_engine = _original_build
        credentials_path.unlink(missing_ok=True)
        with pyodbc.connect(conn_str) as conn:
            conn.cursor().execute("DELETE FROM Parameter WHERE Parameter_name = ?", (test_param,))
            conn.commit()


# -----------------------------------------------------------------------------
# E2E Tests — watermark deduplication
# -----------------------------------------------------------------------------


@pytest.mark.db
def test_e2e_idempotent_import(api_client, db_connection):
    """Importing the same data twice must not create duplicate values."""
    test_param = TEST_PARAMETER_NAME + "_idempotent"

    import pyodbc
    from api.config import settings
    conn_str = (
        f"DRIVER={{{settings.db_driver}}};"
        f"SERVER={settings.db_host},{settings.db_port};"
        f"DATABASE={settings.db_name};"
        f"UID={settings.db_user};"
        f"PWD={settings.db_password};"
        "Encrypt=no;TrustServerCertificate=yes;"
    )
    with pyodbc.connect(conn_str) as conn:
        conn.cursor().execute(
            "INSERT INTO Parameter (Parameter_name, Unit_ID) SELECT ?, Unit_ID FROM Unit WHERE Unit = ?",
            (test_param, TEST_UNIT_NAME),
        )
        conn.commit()

    try:
        cfg = Config(
            api_config=ApiConfig(api_url=API_BASE_URL),
            file_configs=[
                TaglessFileConfig(
                    name="rodtox",
                    mode="tagless",
                    das_name=TEST_DAS_NAME,
                    file_structure=FileStructure(
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
                    ),
                    variables=[
                        TaglessFileVariable(
                            name="do",
                            directory_path=str(RODTOX_DO_PATH),
                            source_variable_name="HMI_DO",
                            equipment_name=TEST_EQUIPMENT_NAME,
                            parameter_name=test_param,
                            source_unit_name=TEST_UNIT_NAME,
                            destination_unit_name=TEST_UNIT_NAME,
                        )
                    ],
                )
            ],
        )

        import_main(cfg, dry_run=False)
        channel_id = resolve_channel_id(
            api_client,
            mode="tagless",
            das_name=TEST_DAS_NAME,
            equipment_name=TEST_EQUIPMENT_NAME,
            parameter_name=test_param,
            unit_name=TEST_UNIT_NAME,
        )
        count_first = count_values_for_channel(db_connection, channel_id)
        assert count_first > 0

        import_main(cfg, dry_run=False)
        count_second = count_values_for_channel(db_connection, channel_id)

        assert count_first == count_second, (
            f"Expected same count after second import, "
            f"got {count_first} then {count_second}"
        )
        print(f"✓ Idempotent import: {count_first} values, no duplicates")

    finally:
        with pyodbc.connect(conn_str) as conn:
            conn.cursor().execute("DELETE FROM Parameter WHERE Parameter_name = ?", (test_param,))
            conn.commit()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
