import pytest
import csv
from pathlib import Path
from io import StringIO
import sys
import os

# Add hooks directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'docs/hooks'))

from generate_docs import (
    parse_parts_table, 
    generate_sql_schema, 
    generate_field_definition, 
    generate_foreign_key_constraint,
    validate_no_circular_fks,
    get_db_config,
    extract_field_name
)
from fixtures import sample_csv_data

@pytest.fixture
def sample_csv_file(tmp_path, sample_csv_data):
    """Create a temporary CSV file."""
    csv_file = tmp_path / "test_parts.csv"
    csv_file.write_text(sample_csv_data)
    return csv_file


class TestGenerateSQLSchema:
    """Tests for SQL schema generation."""
    
    def test_generates_create_table_statement(self, sample_csv_file):
        data = parse_parts_table(sample_csv_file)
        sql = generate_sql_schema(data)
        
        assert 'CREATE TABLE [TestTable]' in sql
    
    def test_includes_all_fields(self, sample_csv_file):
        data = parse_parts_table(sample_csv_file)
        sql = generate_sql_schema(data)

        # Field names (no table prefixes since TestTable is mixed-case)
        assert '[TestTable_ID]' in sql  # ID field keeps full name
        assert '[Name]' in sql  # Regular field
        assert '[Status]' in sql  # Regular field
    
    def test_generates_primary_key_constraint(self, sample_csv_file):
        data = parse_parts_table(sample_csv_file)
        sql = generate_sql_schema(data)

        assert 'CONSTRAINT [PK_TestTable] PRIMARY KEY' in sql
        assert '[TestTable_ID]' in sql

    def test_marks_required_fields_not_null(self, sample_csv_file):
        data = parse_parts_table(sample_csv_file)
        sql = generate_sql_schema(data)

        # Required field should have NOT NULL
        lines = [l for l in sql.split('\n') if '[TestTable_ID]' in l and 'PRIMARY KEY' not in l]
        assert any('NOT NULL' in l for l in lines)

    def test_marks_optional_fields_null(self, sample_csv_file):
        data = parse_parts_table(sample_csv_file)
        sql = generate_sql_schema(data)

        # Optional field should have NULL
        lines = [l for l in sql.split('\n') if '[Status]' in l]
        assert any('NULL' in l for l in lines)
    
    def test_generates_foreign_key_constraints(self, sample_csv_file):
        data = parse_parts_table(sample_csv_file)
        sql = generate_sql_schema(data)

        assert 'ALTER TABLE [TestTable]' in sql
        assert 'FOREIGN KEY ([Parent_ID])' in sql  # Field name is Parent_ID (no prefix)
        assert 'REFERENCES [TestTable] ([TestTable_ID])' in sql  # References TestTable_ID
    
    def test_handles_composite_keys(self, tmp_path):
        csv_content = """Part_ID,Label,Description,Part_type,Value_set_part_ID,Member_of_set_part_ID,SQL_data_type,Is_required,Default_value,Sort_order,JunctionTable_present,JunctionTable_required,JunctionTable_order
JunctionTable,Junction Table,Many-to-many junction,table,,,,,,,,,
Table1_ID,Table1 ID,"Identifier for Table1, used in junction",key,,,int,True,,1,compositeKeyFirst,True,1
Table2_ID,Table2 ID,"Identifier for Table2, used in junction",key,,,int,True,,2,compositeKeySecond,True,2
"""
        csv_file = tmp_path / "composite_key.csv"
        csv_file.write_text(csv_content)

        data = parse_parts_table(csv_file)
        sql = generate_sql_schema(data)

        # Should have composite primary key
        assert 'PRIMARY KEY ([Table1_ID], [Table2_ID])' in sql
    
    def test_sql_is_executable(self, sample_csv_file):
        """Basic syntax check - should not have obvious SQL errors."""
        data = parse_parts_table(sample_csv_file)
        sql = generate_sql_schema(data)
        
        # Check balanced brackets
        assert sql.count('[') == sql.count(']')
        
        # Check balanced parentheses
        assert sql.count('(') == sql.count(')')
        
        # Should end statements with semicolons
        assert 'CREATE TABLE' in sql
        create_statements = [s for s in sql.split(';') if 'CREATE TABLE' in s]
        assert all(');' in s or s.strip().endswith(')') for s in create_statements)
    
    def test_includes_target_db_in_header(self, sample_csv_file):
        data = parse_parts_table(sample_csv_file)
        sql = generate_sql_schema(data, target_db='mssql')
        
        assert 'Target database: MSSQL' in sql


class TestGenerateFieldDefinition:
    """Tests for individual field SQL generation."""
    
    def test_generates_simple_field(self, sample_csv_file):
        data = parse_parts_table(sample_csv_file)
        db_config = get_db_config('mssql')
        field = data['tables']['TestTable']['fields'][1]  # Name field (TestTable_Name)

        field_sql = generate_field_definition(field, data, db_config)

        # TestTable_Name -> Name (table prefix removed)
        assert '[Name]' in field_sql or '[TestTable_Name]' in field_sql  # Accept both
        assert 'nvarchar(255)' in field_sql
        assert 'NOT NULL' in field_sql
    
    def test_handles_default_values(self, tmp_path):
        csv_content = """Part_ID,Label,Description,Part_type,Value_set_part_ID,Member_of_set_part_ID,SQL_data_type,Is_required,Default_value,Sort_order,TestTable_present,TestTable_order
TestTable,Test,Test,table,,,,,,,,
Active,Active,Is active,property,,,bit,False,False,1,property,1
"""
        csv_file = tmp_path / "default.csv"
        csv_file.write_text(csv_content)

        data = parse_parts_table(csv_file)
        db_config = get_db_config('mssql')
        field = data['tables']['TestTable']['fields'][0]

        field_sql = generate_field_definition(field, data, db_config)

        assert 'DEFAULT 0' in field_sql

    def test_applies_type_mappings(self, tmp_path):
        csv_content = """Part_ID,Label,Description,Part_type,Value_set_part_ID,Member_of_set_part_ID,SQL_data_type,Is_required,Default_value,Sort_order,TestTable_present,TestTable_order
TestTable,Test,Test,table,,,,,,,,
Notes,Notes,Long text,property,,,ntext,False,,1,property,1
"""
        csv_file = tmp_path / "ntext.csv"
        csv_file.write_text(csv_content)
        
        data = parse_parts_table(csv_file)
        db_config = get_db_config('mssql')
        field = data['tables']['TestTable']['fields'][0]
        
        field_sql = generate_field_definition(field, data, db_config)
        
        # ntext should be mapped to nvarchar(max) for MSSQL
        assert 'nvarchar(max)' in field_sql
        assert 'ntext' not in field_sql


class TestGenerateForeignKeyConstraint:
    """Tests for foreign key constraint generation."""
    
    def test_generates_fk_constraint(self, sample_csv_file):
        data = parse_parts_table(sample_csv_file)
        db_config = get_db_config('mssql')
        field = next(f for f in data['tables']['TestTable']['fields']
                    if f['part_id'] == 'Parent_ID')

        fk_sql = generate_foreign_key_constraint('TestTable', field, db_config)

        assert 'ALTER TABLE [TestTable]' in fk_sql
        assert 'ADD CONSTRAINT' in fk_sql
        assert 'FOREIGN KEY ([Parent_ID])' in fk_sql
        assert 'REFERENCES [TestTable] ([TestTable_ID])' in fk_sql
    
    def test_returns_none_for_non_fk_field(self, sample_csv_file):
        data = parse_parts_table(sample_csv_file)
        db_config = get_db_config('mssql')
        field = data['tables']['TestTable']['fields'][0]  # ID field, no FK
        
        fk_sql = generate_foreign_key_constraint('TestTable', field, db_config)
        
        assert fk_sql is None


class TestCircularDependencyDetection:
    """Tests for circular FK validation."""
    
    def test_detects_simple_circular_dependency(self, tmp_path):
        csv_content = """Part_ID,Label,Description,Part_type,Value_set_part_ID,Member_of_set_part_ID,SQL_data_type,Is_required,Default_value,Sort_order,TableA_present,TableA_order,TableB_present,TableB_order
TableA,Table A,First table,table,,,,,,,,,
TableB,Table B,Second table,table,,,,,,,,,
TableA_ID,Table A ID,Identifier for TableA,key,,,int,True,,1,key,1,property,2
TableB_ID,Table B ID,Identifier for TableB,key,,,int,True,,1,property,2,key,1
"""
        csv_file = tmp_path / "circular.csv"
        csv_file.write_text(csv_content)

        data = parse_parts_table(csv_file)

        with pytest.raises(ValueError, match="Circular foreign key dependencies"):
            generate_sql_schema(data)
    
    def test_allows_self_referential_fks(self, tmp_path):
        csv_content = """Part_ID,Label,Description,Part_type,Value_set_part_ID,Member_of_set_part_ID,SQL_data_type,Is_required,Default_value,Sort_order,TableA_present,TableA_order
TableA,Table A,Hierarchical table,table,,,,,,,,
TableA_ID,Table A ID,Identifier for TableA,key,,,int,True,,1,key,1
TableA_Parent_ID,Parent ID,FK to parent TableA,property,,,int,False,,2,property,2
"""
        csv_file = tmp_path / "self_ref.csv"
        csv_file.write_text(csv_content)

        data = parse_parts_table(csv_file)

        # Should NOT raise - self-referential is OK
        sql = generate_sql_schema(data)
        assert 'CREATE TABLE' in sql

    def test_allows_chain_dependencies(self, tmp_path):
        csv_content = """Part_ID,Label,Description,Part_type,Value_set_part_ID,Member_of_set_part_ID,SQL_data_type,Is_required,Default_value,Sort_order,TableA_present,TableA_order,TableB_present,TableB_order,TableC_present,TableC_order
TableA,Table A,First,table,,,,,,,,,,,,
TableA_ID,Table A ID,PK,key,,,int,True,,1,key,1,,,,
TableB,Table B,Second,table,,,,,,,,,,,,
TableB_ID,Table B ID,PK,key,,,int,True,,1,,,key,1,,
TableA_ID,Table A ID,A ref,key,,,int,False,,2,,,property,2,,
TableC,Table C,Third,table,,,,,,,,,,,,
TableC_ID,Table C ID,PK,key,,,int,True,,1,,,,,key,1
TableB_ID,Table B ID,B ref,key,,,int,False,,2,,,,,property,2
"""
        csv_file = tmp_path / "chain.csv"
        csv_file.write_text(csv_content)
        
        data = parse_parts_table(csv_file)
        
        # Should NOT raise - A->B->C is fine
        sql = generate_sql_schema(data)
        assert 'CREATE TABLE' in sql
    
    def test_validation_function_directly(self, tmp_path):
        csv_content = """Part_ID,Label,Description,Part_type,Value_set_part_ID,Member_of_set_part_ID,SQL_data_type,Is_required,Default_value,Sort_order,TableA_present,TableA_order,TableB_present,TableB_order
TableA,Table A,First table,table,,,,,,,,,
TableB,Table B,Second table,table,,,,,,,,,
TableA_ID,Table A ID,Identifier for TableA,key,,,int,True,,1,key,1,property,2
TableB_ID,Table B ID,Identifier for TableB,key,,,int,True,,1,property,2,key,1
"""
        csv_file = tmp_path / "circular.csv"
        csv_file.write_text(csv_content)

        data = parse_parts_table(csv_file)

        with pytest.raises(ValueError) as exc_info:
            validate_no_circular_fks(data)

        error_msg = str(exc_info.value)
        assert 'TableA' in error_msg
        assert 'TableB' in error_msg
        assert '↔' in error_msg


class TestDatabaseTargeting:
    """Tests for multi-database support."""
    
    def test_uses_mssql_bracket_quoting(self, sample_csv_file):
        data = parse_parts_table(sample_csv_file)
        sql = generate_sql_schema(data, target_db='mssql')

        assert '[TestTable]' in sql
        assert '[TestTable_ID]' in sql
    
    def test_converts_ntext_to_nvarchar_max(self, tmp_path):
        csv_content = """Part_ID,Label,Description,Part_type,Value_set_part_ID,Member_of_set_part_ID,SQL_data_type,Is_required,Default_value,Sort_order,TableA_present,TableA_order
TableA,Table A,Test,table,,,,,,,,
TableA_ID,Table A ID,PK,key,,,int,True,,1,key,1
Notes,Notes,Long text,property,,,ntext,False,,2,property,2
"""
        csv_file = tmp_path / "ntext.csv"
        csv_file.write_text(csv_content)
        
        data = parse_parts_table(csv_file)
        sql = generate_sql_schema(data, target_db='mssql')
        
        # ntext should be converted to nvarchar(max)
        assert 'nvarchar(max)' in sql
        # Check that ntext doesn't appear in actual SQL (only in comments is OK)
        sql_lines = [line for line in sql.split('\n') if not line.strip().startswith('--')]
        sql_without_comments = '\n'.join(sql_lines)
        assert 'ntext' not in sql_without_comments.lower()
    
    def test_rejects_unsupported_database(self, sample_csv_file):
        data = parse_parts_table(sample_csv_file)
        
        with pytest.raises(ValueError, match="Unsupported database"):
            generate_sql_schema(data, target_db='oracle')
    
    def test_get_db_config_returns_correct_structure(self):
        config = get_db_config('mssql')
        
        assert 'quote_char' in config
        assert 'type_mappings' in config
        assert 'supports_check_constraints' in config
        assert callable(config['quote'])
    
    def test_db_config_quote_function(self):
        config = get_db_config('mssql')
        
        quoted = config['quote']('TableName')
        assert quoted == '[TableName]'


class TestExtractFieldName:
    """Tests for field name extraction helper - NEW FORMAT."""

    def test_extracts_field_from_part_id(self):
        # ID fields are kept as-is (these are the actual SQL field names)
        assert extract_field_name('TestTable_ID') == 'TestTable_ID'
        assert extract_field_name('Equipment_ID') == 'Equipment_ID'
        assert extract_field_name('Contact_ID') == 'Contact_ID'

        # Table-prefixed non-ID fields: remove lowercase table prefix
        assert extract_field_name('site_City') == 'City'
        assert extract_field_name('contact_City') == 'City'
        assert extract_field_name('purpose_Description') == 'Description'

    def test_handles_part_id_without_underscore(self):
        # Non-prefixed fields stay as-is
        assert extract_field_name('SimpleField') == 'SimpleField'
        assert extract_field_name('Forest') == 'Forest'

    def test_handles_multiple_underscores(self):
        # Mixed case fields with underscores (not table-prefixed)
        assert extract_field_name('Street_number') == 'Street_number'
        assert extract_field_name('Latitude_GPS') == 'Latitude_GPS'


class TestSQLIntegration:
    """Integration tests for complete SQL generation."""
    
    def test_generates_complete_valid_schema(self, sample_csv_file):
        data = parse_parts_table(sample_csv_file)
        sql = generate_sql_schema(data)
        
        # Should have all major components
        assert 'CREATE TABLE' in sql
        assert 'PRIMARY KEY' in sql
        assert 'ALTER TABLE' in sql
        assert 'FOREIGN KEY' in sql
        assert 'REFERENCES' in sql
    
    def test_table_order_is_deterministic(self, sample_csv_file):
        data = parse_parts_table(sample_csv_file)
        sql1 = generate_sql_schema(data, include_timestamp=False)
        sql2 = generate_sql_schema(data, include_timestamp=False)

        # Should generate identical SQL on repeated calls
        assert sql1 == sql2
    
    def test_handles_complex_schema(self, tmp_path):
        csv_content = """Part_ID,Label,Description,Part_type,Value_set_part_ID,Member_of_set_part_ID,SQL_data_type,Is_required,Default_value,Sort_order,Parent_present,Parent_order,Child_present,Child_order
Parent,Parent,Parent table,table,,,,,,,,
Parent_ID,Parent ID,Identifier for Parent,key,,,int,True,,1,key,1,,
Name,Name,Name,property,,,nvarchar(100),True,,2,property,2,,
Child,Child,Child table,table,,,,,,,,
Child_ID,Child ID,Identifier for Child,key,,,int,True,,1,,,key,1
Parent_ID,Parent ID,Identifier for Parent,key,,,int,True,,2,,,property,2
Status,Status,Status,property,StatusSet,,nvarchar(50),False,pending,3,,,property,3
StatusSet,Status Set,Valid statuses,valueSet,,,,,,,,,
pending,Pending,Pending status,valueSetMember,,StatusSet,nvarchar(50),,,1,,
active,Active,Active status,valueSetMember,,StatusSet,nvarchar(50),,,2,,
"""
        csv_file = tmp_path / "complex.csv"
        csv_file.write_text(csv_content)

        data = parse_parts_table(csv_file)
        sql = generate_sql_schema(data)

        # Parent table should be created
        assert 'CREATE TABLE [Parent]' in sql
        # Child table should be created
        assert 'CREATE TABLE [Child]' in sql
        # FK relationship should exist
        assert 'REFERENCES [Parent]' in sql
        # Default value should be present
        assert "DEFAULT 'pending'" in sql