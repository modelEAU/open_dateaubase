"""End-to-end tests for the table_import system.

These tests verify that the import system can:
1. Read data from various file formats (CSV, TSDB, SQL)
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

# Add project root to path for importing table_import modules
import sys
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from table_import.api_client import DateaubaseClient, ApiError
from table_import.config import (
    ApiConfig,
    Config,
    FileStructure,
    FileType,
    TsdbFileStructure,
    TsdbSource,
    TsdbVariable,
    ScadaSqlStructure,
    ScadaSqlSource,
    ScadaVariable,
    Variable,
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

# Get API URL from environment or use default
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000/api/v1")

# Test identifiers - these will be created in the database
TEST_EQUIPMENT_NAME = "e2e_test_equipment"
TEST_PARAMETER_NAME = "e2e_test_parameter"
TEST_UNIT_NAME = "e2e_test_unit"

# -----------------------------------------------------------------------------
# Fixtures
# -----------------------------------------------------------------------------


@pytest.fixture(scope="module")
def api_client():
    """Provide a DateaubaseClient for the test module."""
    with DateaubaseClient(API_BASE_URL) as client:
        yield client


@pytest.fixture(scope="module")
def db_connection():
    """Provide a direct database connection for setup/teardown."""
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
    """Create test equipment, parameter, and unit in the database."""
    cursor = db_connection.cursor()
    
    # Clean up any existing test data first
    cleanup_test_data(cursor)
    
    # Insert test unit
    cursor.execute(
        "INSERT INTO Unit (Unit) VALUES (?)",
        (TEST_UNIT_NAME,)
    )
    db_connection.commit()
    
    # Insert test parameter
    cursor.execute(
        "INSERT INTO Parameter (Parameter_name, Unit_ID) SELECT ?, Unit_ID FROM Unit WHERE Unit = ?",
        (TEST_PARAMETER_NAME, TEST_UNIT_NAME)
    )
    db_connection.commit()
    
    # Insert test equipment (requires a site first)
    cursor.execute(
        "IF NOT EXISTS (SELECT 1 FROM Site WHERE Site_name = 'e2e_test_site') "
        "INSERT INTO Site (Site_name) VALUES ('e2e_test_site')"
    )
    cursor.execute(
        "INSERT INTO Equipment (Identifier, Site_ID) SELECT ?, Site_ID FROM Site WHERE Site_name = 'e2e_test_site'",
        (TEST_EQUIPMENT_NAME,)
    )
    db_connection.commit()
    
    yield
    
    # Cleanup after tests
    cleanup_test_data(cursor)
    db_connection.commit()
    cursor.close()


def cleanup_test_data(cursor):
    """Remove all test data from the database."""
    # Delete values first (foreign key constraints)
    cursor.execute("""
        DELETE FROM Value WHERE Channel_ID IN (
            SELECT c.Channel_ID FROM Channel c
            JOIN Equipment e ON c.Equipment_ID = e.Equipment_ID
            WHERE e.Identifier = ?
        )
    """, (TEST_EQUIPMENT_NAME,))
    
    # Delete channels
    cursor.execute("""
        DELETE FROM Channel WHERE Equipment_ID IN (
            SELECT Equipment_ID FROM Equipment WHERE Identifier = ?
        )
    """, (TEST_EQUIPMENT_NAME,))
    
    # Delete equipment
    cursor.execute("DELETE FROM Equipment WHERE Identifier = ?", (TEST_EQUIPMENT_NAME,))
    
    # Delete site
    cursor.execute("DELETE FROM Site WHERE Site_name = 'e2e_test_site'")
    
    # Delete parameter
    cursor.execute("DELETE FROM Parameter WHERE Parameter_name = ?", (TEST_PARAMETER_NAME,))
    
    # Delete unit
    cursor.execute("DELETE FROM Unit WHERE Unit = ?", (TEST_UNIT_NAME,))


# -----------------------------------------------------------------------------
# Helper Functions
# -----------------------------------------------------------------------------


def count_values_for_channel(api_client: DateaubaseClient, equipment_id: int, parameter_id: int) -> int:
    """Count the number of values in a channel via API."""
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
    
    with pyodbc.connect(conn_str) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT COUNT(*) FROM Value v
            JOIN Channel c ON v.Channel_ID = c.Channel_ID
            WHERE c.Equipment_ID = ? AND c.Parameter_ID = ?
        """, (equipment_id, parameter_id))
        result = cursor.fetchone()
        return result[0] if result else 0


def get_channel_id(api_client: DateaubaseClient, equipment_id: int, parameter_id: int) -> int | None:
    """Get the channel ID for a given equipment/parameter combination."""
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
    
    with pyodbc.connect(conn_str) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT Channel_ID FROM Channel
            WHERE Equipment_ID = ? AND Parameter_ID = ?
            AND Data_Provenance_ID = 1 AND Processing_Degree_ID = 1
        """, (equipment_id, parameter_id))
        result = cursor.fetchone()
        return result[0] if result else None


# -----------------------------------------------------------------------------
# E2E Tests
# -----------------------------------------------------------------------------


@pytest.mark.db
def test_e2e_rodtox_csv_import(api_client: DateaubaseClient):
    """Test importing Rodtox CSV data via the import script.
    
    This test uses the test data from importer/test_data/rodtox/DO/DO_log0.csv
    and verifies that the data is correctly inserted into the database.
    """
    # Resolve IDs for our test entities
    equipment_id = api_client.resolve_equipment_id(TEST_EQUIPMENT_NAME)
    parameter_id = api_client.resolve_parameter_id(TEST_PARAMETER_NAME)
    unit_id = api_client.resolve_unit_id(TEST_UNIT_NAME)
    
    # Verify no data exists initially
    initial_count = count_values_for_channel(api_client, equipment_id, parameter_id)
    assert initial_count == 0, "Expected no values before import"
    
    # Build config for Rodtox import
    config_obj = Config(
        api_config=ApiConfig(api_url=API_BASE_URL),
        file_configs=[
            FileType(
                name="rodtox",
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
                    Variable(
                        name="do",
                        directory_path=str(RODTOX_DO_PATH),
                        variable_name="HMI_DO",
                        equipment_name=TEST_EQUIPMENT_NAME,
                        parameter_name=TEST_PARAMETER_NAME,
                        source_unit_name=TEST_UNIT_NAME,
                        channel_unit_name=TEST_UNIT_NAME,
                        conversion_factor=1.0,
                        data_provenance_id=1,
                        processing_degree_id=1,
                    )
                ],
            )
        ],
    )
    
    # Run the import
    import_main(config_obj, dry_run=False)
    
    # Verify data was inserted
    final_count = count_values_for_channel(api_client, equipment_id, parameter_id)
    assert final_count > 0, f"Expected values to be inserted, got {final_count}"
    
    # Verify channel was created
    channel_id = get_channel_id(api_client, equipment_id, parameter_id)
    assert channel_id is not None, "Channel should have been created"
    
    print(f"✓ Successfully imported {final_count} Rodtox CSV values")


@pytest.mark.db
def test_e2e_tsdb_import(api_client: DateaubaseClient):
    """Test importing TSDB binary data via the import script.
    
    This test uses the test data from importer/test_data/basestation/*.tsdb
    and verifies that the data is correctly inserted into the database.
    """
    # Use a different parameter for TSDB to avoid conflicts
    test_param = TEST_PARAMETER_NAME + "_tsdb"
    
    # Create the parameter in DB
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
    
    with pyodbc.connect(conn_str) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO Parameter (Parameter_name, Unit_ID) SELECT ?, Unit_ID FROM Unit WHERE Unit = ?",
            (test_param, TEST_UNIT_NAME)
        )
        conn.commit()
    
    try:
        # Resolve IDs
        equipment_id = api_client.resolve_equipment_id(TEST_EQUIPMENT_NAME)
        parameter_id = api_client.resolve_parameter_id(test_param)
        unit_id = api_client.resolve_unit_id(TEST_UNIT_NAME)
        
        # Verify no data exists initially
        initial_count = count_values_for_channel(api_client, equipment_id, parameter_id)
        assert initial_count == 0, "Expected no values before import"
        
        # Build config for TSDB import
        config_obj = Config(
            api_config=ApiConfig(api_url=API_BASE_URL),
            file_configs=[],  # No file-based configs
            tsdb_configs=[
                TsdbSource(
                    name="tsdb",
                    tsdb_structure=TsdbFileStructure(timezone="America/Montreal"),
                    variables=[
                        TsdbVariable(
                            name="turb",
                            directory_path=str(TSDB_PATH),
                            equipment_name=TEST_EQUIPMENT_NAME,
                            parameter_name=test_param,
                            source_unit_name=TEST_UNIT_NAME,
                            channel_unit_name=TEST_UNIT_NAME,
                            conversion_factor=1.0,
                            data_provenance_id=1,
                            processing_degree_id=1,
                        )
                    ],
                )
            ],
        )
        
        # Run the import
        import_main(config_obj, dry_run=False)
        
        # Verify data was inserted
        final_count = count_values_for_channel(api_client, equipment_id, parameter_id)
        assert final_count > 0, f"Expected values to be inserted, got {final_count}"
        
        print(f"✓ Successfully imported {final_count} TSDB values")
        
    finally:
        # Cleanup
        with pyodbc.connect(conn_str) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM Parameter WHERE Parameter_name = ?", (test_param,))
            conn.commit()


@pytest.mark.db
def test_e2e_scada_sql_import(api_client: DateaubaseClient):
    """Test importing SCADA SQL data via the import script.
    
    This test uses the test data from importer/test_data/scada_sql/float_table.db
    and verifies that the data is correctly inserted into the database.
    """
    # Use a different parameter for SCADA to avoid conflicts
    test_param = TEST_PARAMETER_NAME + "_scada"
    
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
    
    # Create the parameter in DB
    with pyodbc.connect(conn_str) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO Parameter (Parameter_name, Unit_ID) SELECT ?, Unit_ID FROM Unit WHERE Unit = ?",
            (test_param, TEST_UNIT_NAME)
        )
        conn.commit()
    
    # Create a credentials file for the SQLite "SCADA" database
    credentials_path = TEST_DATA_DIR / "scada_sql" / "test_credentials.txt"
    credentials_path.write_text("SA\nStrongPwd123!\n")
    
    try:
        # Resolve IDs
        equipment_id = api_client.resolve_equipment_id(TEST_EQUIPMENT_NAME)
        
        # We need to refresh the cache to get the new parameter
        api_client._parameter_by_name = None
        parameter_id = api_client.resolve_parameter_id(test_param)
        unit_id = api_client.resolve_unit_id(TEST_UNIT_NAME)
        
        # Verify no data exists initially
        initial_count = count_values_for_channel(api_client, equipment_id, parameter_id)
        assert initial_count == 0, "Expected no values before import"
        
        # Create a SQLAlchemy engine for the SQLite test database
        from sqlalchemy import create_engine
        scada_engine = create_engine(f"sqlite:///{SCADA_DB_PATH}")
        
        # Build config for SCADA SQL import
        from table_import.import_script import _resolve_variable_ids, _last_unix_ts, build_api_payload, ingest_via_api
        from table_import.scada_sql_source import SqlServerSource
        
        structure = ScadaSqlStructure(
            server="localhost",
            database="test",
            credentials_path=str(credentials_path),
            table="FloatTable_hedi",
            datetime_column="DateAndTime",
            tag_index_column="TagIndex",
            value_column="Val",
            timezone="America/Montreal",
        )
        
        variable = ScadaVariable(
            name="test_var",
            tag_index=45,  # A tag index that exists in the test data
            equipment_name=TEST_EQUIPMENT_NAME,
            parameter_name=test_param,
            source_unit_name=TEST_UNIT_NAME,
            channel_unit_name=TEST_UNIT_NAME,
            conversion_factor=1.0,
            data_provenance_id=1,
            processing_degree_id=1,
        )
        
        # Create source and get values
        source = SqlServerSource(structure=structure, variable=variable, engine=scada_engine)
        data = source.get_values_since(0.0)
        
        # Build payload and ingest
        payload = build_api_payload(data, last_unix_ts=0.0, min_unix_ts=None, conversion_factor=1.0)
        
        ingest_via_api(
            api_client,
            equipment_id=equipment_id,
            parameter_id=parameter_id,
            unit_id=unit_id,
            data_provenance_id=1,
            processing_degree_id=1,
            payload=payload,
            label="scada/test_var",
            dry_run=False,
        )
        
        # Verify data was inserted
        final_count = count_values_for_channel(api_client, equipment_id, parameter_id)
        assert final_count > 0, f"Expected values to be inserted, got {final_count}"
        
        print(f"✓ Successfully imported {final_count} SCADA SQL values")
        
    finally:
        # Cleanup
        credentials_path.unlink(missing_ok=True)
        with pyodbc.connect(conn_str) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM Parameter WHERE Parameter_name = ?", (test_param,))
            conn.commit()


@pytest.mark.db
def test_e2e_idempotent_import(api_client: DateaubaseClient):
    """Test that importing the same data twice is idempotent (no duplicates).
    
    This verifies the watermark-based deduplication is working correctly.
    """
    # Use a unique parameter for this test
    test_param = TEST_PARAMETER_NAME + "_idempotent"
    
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
    
    # Create the parameter in DB
    with pyodbc.connect(conn_str) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO Parameter (Parameter_name, Unit_ID) SELECT ?, Unit_ID FROM Unit WHERE Unit = ?",
            (test_param, TEST_UNIT_NAME)
        )
        conn.commit()
    
    try:
        # Resolve IDs
        equipment_id = api_client.resolve_equipment_id(TEST_EQUIPMENT_NAME)
        api_client._parameter_by_name = None  # Refresh cache
        parameter_id = api_client.resolve_parameter_id(test_param)
        
        # Build config for Rodtox import
        config_obj = Config(
            api_config=ApiConfig(api_url=API_BASE_URL),
            file_configs=[
                FileType(
                    name="rodtox",
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
                        Variable(
                            name="do",
                            directory_path=str(RODTOX_DO_PATH),
                            variable_name="HMI_DO",
                            equipment_name=TEST_EQUIPMENT_NAME,
                            parameter_name=test_param,
                            source_unit_name=TEST_UNIT_NAME,
                            channel_unit_name=TEST_UNIT_NAME,
                            conversion_factor=1.0,
                            data_provenance_id=1,
                            processing_degree_id=1,
                        )
                    ],
                )
            ],
        )
        
        # First import
        import_main(config_obj, dry_run=False)
        count_after_first = count_values_for_channel(api_client, equipment_id, parameter_id)
        assert count_after_first > 0, "Expected values after first import"
        
        # Second import - should be idempotent
        import_main(config_obj, dry_run=False)
        count_after_second = count_values_for_channel(api_client, equipment_id, parameter_id)
        
        assert count_after_first == count_after_second, (
            f"Expected same count after second import, "
            f"got {count_after_first} then {count_after_second}"
        )
        
        print(f"✓ Idempotent import verified: {count_after_first} values, no duplicates")
        
    finally:
        # Cleanup
        with pyodbc.connect(conn_str) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM Parameter WHERE Parameter_name = ?", (test_param,))
            conn.commit()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
