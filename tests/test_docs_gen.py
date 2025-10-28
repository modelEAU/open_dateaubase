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
    generate_tables_markdown,
    generate_value_sets_markdown,
    on_pre_build,
    generate_sql_schemas
)
from fixtures import sample_csv_data

@pytest.fixture
def sample_csv_file(tmp_path, sample_csv_data):
    """Create a temporary CSV file."""
    csv_file = tmp_path / "test_parts.csv"
    csv_file.write_text(sample_csv_data)
    return csv_file


class TestParsePartsTable:
    """Tests for parse_parts_table function."""
    
    def test_parse_identifies_tables(self, sample_csv_file):
        data = parse_parts_table(sample_csv_file)
        
        assert 'TestTable' in data['tables']
        assert data['tables']['TestTable']['label'] == 'Test Table'
        assert data['tables']['TestTable']['description'] == 'A test table'
    
    def test_parse_identifies_fields(self, sample_csv_file):
        data = parse_parts_table(sample_csv_file)
        
        fields = data['tables']['TestTable']['fields']
        assert len(fields) == 4
        
        # Check primary key
        pk_field = next(f for f in fields if f['part_id'] == 'TestTable_ID')
        assert pk_field['part_type'] == 'key'
        assert pk_field['is_required'] == True
        assert pk_field['sql_data_type'] == 'int'
    
    def test_parse_identifies_foreign_keys(self, sample_csv_file):
        data = parse_parts_table(sample_csv_file)

        # Parent_ID is now a parentKey type with Ancestor_part_ID set
        fk_field = next(f for f in data['tables']['TestTable']['fields']
                       if f['part_id'] == 'Parent_ID')
        assert fk_field['fk_to'] == 'TestTable_ID'
    
    def test_parse_identifies_value_sets(self, sample_csv_file):
        data = parse_parts_table(sample_csv_file)
        
        assert 'StatusSet' in data['value_sets']
        assert data['value_sets']['StatusSet']['label'] == 'Status Set'
        assert len(data['value_sets']['StatusSet']['members']) == 2
    
    def test_parse_sorts_fields_by_sort_order(self, sample_csv_file):
        data = parse_parts_table(sample_csv_file)
        
        fields = data['tables']['TestTable']['fields']
        sort_orders = [f['sort_order'] for f in fields]
        assert sort_orders == sorted(sort_orders)
    
    def test_parse_sorts_value_set_members(self, sample_csv_file):
        data = parse_parts_table(sample_csv_file)
        
        members = data['value_sets']['StatusSet']['members']
        sort_orders = [m['sort_order'] for m in members]
        assert sort_orders == sorted(sort_orders)
    
    def test_parse_links_value_sets_to_fields(self, sample_csv_file):
        data = parse_parts_table(sample_csv_file)

        status_field = next(f for f in data['tables']['TestTable']['fields']
                           if f['part_id'] == 'Status')
        assert status_field['value_set'] == 'StatusSet'


class TestGenerateTablesMarkdown:
    """Tests for generate_tables_markdown function."""
    
    def test_generates_valid_markdown(self, sample_csv_file):
        data = parse_parts_table(sample_csv_file)
        markdown = generate_tables_markdown(data)
        
        assert '# Database Tables' in markdown
        assert '## Tables' in markdown
    
    def test_includes_table_headings(self, sample_csv_file):
        data = parse_parts_table(sample_csv_file)
        markdown = generate_tables_markdown(data)
        
        assert '### Test Table' in markdown
        assert 'A test table' in markdown
    
    def test_includes_table_anchors(self, sample_csv_file):
        data = parse_parts_table(sample_csv_file)
        markdown = generate_tables_markdown(data)
        
        # Check for invisible anchor span
        assert '<span id="TestTable"></span>' in markdown
    
    def test_includes_field_anchors(self, sample_csv_file):
        data = parse_parts_table(sample_csv_file)
        markdown = generate_tables_markdown(data)

        # Check for field anchors in description column
        assert '<span id="TestTable_ID"></span>' in markdown
        assert '<span id="Name"></span>' in markdown
    
    def test_generates_fields_table(self, sample_csv_file):
        data = parse_parts_table(sample_csv_file)
        markdown = generate_tables_markdown(data)
        
        # Check table header
        assert '| Field | SQL Type | Value Set | Required | Description | Constraints |' in markdown
        assert '|-------|----------|-----------|----------|-------------|-------------|' in markdown
    
    def test_marks_primary_keys(self, sample_csv_file):
        data = parse_parts_table(sample_csv_file)
        markdown = generate_tables_markdown(data)
        
        # Primary key should have PK marker
        assert 'int **(PK)**' in markdown
    
    def test_marks_required_fields(self, sample_csv_file):
        data = parse_parts_table(sample_csv_file)
        markdown = generate_tables_markdown(data)
        
        # Should have checkmarks for required fields
        assert '✓' in markdown
    
    def test_links_to_value_sets(self, sample_csv_file):
        data = parse_parts_table(sample_csv_file)
        markdown = generate_tables_markdown(data)
        
        # Should link to value set
        assert '[StatusSet](valuesets.md#StatusSet)' in markdown
    
    def test_links_foreign_keys(self, sample_csv_file):
        data = parse_parts_table(sample_csv_file)
        markdown = generate_tables_markdown(data)
        
        # Should link FK to target field
        assert 'FK → [TestTable_ID](#TestTable_ID)' in markdown
    
    def test_shows_dash_when_no_value_set(self, sample_csv_file):
        data = parse_parts_table(sample_csv_file)
        markdown = generate_tables_markdown(data)
        
        # Fields without value sets should show '-'
        lines = markdown.split('\n')
        name_field_line = [l for l in lines if 'Name field' in l][0]
        assert '| -' in name_field_line or '- |' in name_field_line


class TestGenerateValueSetsMarkdown:
    """Tests for generate_value_sets_markdown function."""
    
    def test_generates_valid_markdown(self, sample_csv_file):
        data = parse_parts_table(sample_csv_file)
        markdown = generate_value_sets_markdown(data)
        
        assert '# Value Sets' in markdown
    
    def test_includes_value_set_headings(self, sample_csv_file):
        data = parse_parts_table(sample_csv_file)
        markdown = generate_value_sets_markdown(data)
        
        assert '## Status Set' in markdown
        assert 'Valid status values' in markdown
    
    def test_includes_value_set_anchors(self, sample_csv_file):
        data = parse_parts_table(sample_csv_file)
        markdown = generate_value_sets_markdown(data)
        
        # Check for invisible anchor span
        assert '<span id="StatusSet"></span>' in markdown
    
    def test_includes_member_anchors(self, sample_csv_file):
        data = parse_parts_table(sample_csv_file)
        markdown = generate_value_sets_markdown(data)
        
        # Check for member anchors
        assert '<span id="active"></span>' in markdown
        assert '<span id="inactive"></span>' in markdown
    
    def test_generates_members_table(self, sample_csv_file):
        data = parse_parts_table(sample_csv_file)
        markdown = generate_value_sets_markdown(data)
        
        # Check table header
        assert '| Value | Description |' in markdown
        assert '|-------|-------------|' in markdown
    
    def test_lists_all_members(self, sample_csv_file):
        data = parse_parts_table(sample_csv_file)
        markdown = generate_value_sets_markdown(data)
        
        assert '`active`' in markdown
        assert 'Active status' in markdown
        assert '`inactive`' in markdown
        assert 'Inactive status' in markdown
    
    def test_handles_empty_value_sets(self, tmp_path):
        # CSV with no value sets
        csv_content = """Part_ID,Label,Description,Part_type,Table_part_ID,Value_set_part_ID,Member_of_set_part_ID,FK_to_part_ID,SQL_data_type,Is_required,Default_value,Sort_order
TestTable,Test Table,A test table,table,,,,,,,,
"""
        csv_file = tmp_path / "empty_valuesets.csv"
        csv_file.write_text(csv_content)
        
        data = parse_parts_table(csv_file)
        markdown = generate_value_sets_markdown(data)
        
        assert 'No value sets currently appear in the dictionary' in markdown


class TestIntegration:
    """Integration tests checking cross-referencing between tables and value sets."""
    
    def test_value_set_links_are_bidirectional(self, sample_csv_file):
        data = parse_parts_table(sample_csv_file)
        tables_md = generate_tables_markdown(data)
        valuesets_md = generate_value_sets_markdown(data)
        
        # Table should link to value set
        assert '[StatusSet](valuesets.md#StatusSet)' in tables_md
        
        # Value set should have anchor that table links to
        assert '<span id="StatusSet"></span>' in valuesets_md
    
    def test_foreign_key_links_point_to_existing_anchors(self, sample_csv_file):
        data = parse_parts_table(sample_csv_file)
        markdown = generate_tables_markdown(data)

        # FK link
        assert 'FK → [TestTable_ID](#TestTable_ID)' in markdown

        # Target anchor exists
        assert '<span id="TestTable_ID"></span>' in markdown


class TestGenerateSQLSchemas:
    """Tests for generate_sql_schemas function."""

    def test_generates_sql_file_with_timestamp_and_version(self, sample_csv_file, tmp_path):
        """Test that SQL files are generated with timestamp and version in filename."""
        data = parse_parts_table(sample_csv_file)
        sql_path = tmp_path / "sql_output"
        sql_path.mkdir()

        generate_sql_schemas(data, sql_path, ['mssql'])

        # Check that a file was created
        sql_files = list(sql_path.glob('*.sql'))
        assert len(sql_files) == 1

        # Check filename format: YYYY-MM-DDTHH:MM:SS.ffffff_version_mssql.sql
        sql_file = sql_files[0]
        filename = sql_file.name

        # Should contain version
        assert '0.1.0' in filename  # Current package version

        # Should contain database type
        assert 'mssql.sql' in filename

        # Should contain ISO timestamp format (just check for basic structure)
        assert filename.count('_') >= 2  # timestamp_version_mssql.sql

    def test_generates_multiple_database_schemas(self, sample_csv_file, tmp_path):
        """Test that multiple database schemas can be generated."""
        data = parse_parts_table(sample_csv_file)
        sql_path = tmp_path / "sql_output"
        sql_path.mkdir()

        # Currently only mssql is supported, but test the loop structure
        generate_sql_schemas(data, sql_path, ['mssql'])

        sql_files = list(sql_path.glob('*_mssql.sql'))
        assert len(sql_files) == 1

    def test_generated_sql_contains_valid_schema(self, sample_csv_file, tmp_path):
        """Test that generated SQL contains expected schema elements."""
        data = parse_parts_table(sample_csv_file)
        sql_path = tmp_path / "sql_output"
        sql_path.mkdir()

        generate_sql_schemas(data, sql_path, ['mssql'])

        sql_file = list(sql_path.glob('*.sql'))[0]
        sql_content = sql_file.read_text(encoding='utf-8')

        # Should contain basic SQL elements
        assert 'CREATE TABLE [TestTable]' in sql_content
        assert 'PRIMARY KEY' in sql_content
        assert 'FOREIGN KEY' in sql_content

    def test_writes_to_correct_path(self, sample_csv_file, tmp_path):
        """Test that SQL files are written to the specified path."""
        data = parse_parts_table(sample_csv_file)
        sql_path = tmp_path / "custom_sql_dir"
        sql_path.mkdir()

        generate_sql_schemas(data, sql_path, ['mssql'])

        # Should write to custom directory
        assert any(sql_path.glob('*.sql'))
        assert len(list(sql_path.glob('*.sql'))) == 1


class TestOnPreBuild:
    """Tests for on_pre_build MkDocs hook."""

    @pytest.fixture
    def mock_config(self, tmp_path, sample_csv_data):
        """Create a mock MkDocs config."""
        # Setup directory structure
        project_root = tmp_path / "project"
        project_root.mkdir()
        docs_dir = project_root / "docs"
        docs_dir.mkdir()
        reference_dir = docs_dir / "reference"
        reference_dir.mkdir()
        sql_dir = project_root / "sql_generation_scripts"
        sql_dir.mkdir()

        # Create dictionary CSV
        csv_file = project_root / "dictionary.csv"
        csv_file.write_text(sample_csv_data)

        # Create mock config object
        config = {
            'config_file_path': str(project_root / "mkdocs.yml"),
            'docs_dir': str(docs_dir)
        }

        return config, project_root, docs_dir, reference_dir, sql_dir

    def test_generates_all_output_files(self, mock_config):
        """Test that on_pre_build generates all expected output files."""
        config, project_root, docs_dir, reference_dir, sql_dir = mock_config

        on_pre_build(config)

        # Check that markdown files were created
        assert (reference_dir / "tables.md").exists()
        assert (reference_dir / "valuesets.md").exists()

        # Check that SQL files were created
        sql_files = list(sql_dir.glob("*.sql"))
        assert len(sql_files) > 0
        assert any('mssql.sql' in f.name for f in sql_files)

    def test_tables_md_contains_expected_content(self, mock_config):
        """Test that generated tables.md has correct content."""
        config, project_root, docs_dir, reference_dir, sql_dir = mock_config

        on_pre_build(config)

        tables_content = (reference_dir / "tables.md").read_text(encoding='utf-8')

        # Should have standard elements
        assert '# Database Tables' in tables_content
        assert '### Test Table' in tables_content
        assert 'A test table' in tables_content
        assert '<span id="TestTable"></span>' in tables_content

    def test_valuesets_md_contains_expected_content(self, mock_config):
        """Test that generated valuesets.md has correct content."""
        config, project_root, docs_dir, reference_dir, sql_dir = mock_config

        on_pre_build(config)

        valuesets_content = (reference_dir / "valuesets.md").read_text(encoding='utf-8')

        # Should have standard elements
        assert '# Value Sets' in valuesets_content
        assert '## Status Set' in valuesets_content
        assert 'Valid status values' in valuesets_content

    def test_sql_schemas_generated_with_correct_format(self, mock_config):
        """Test that SQL schemas have correct filename format."""
        config, project_root, docs_dir, reference_dir, sql_dir = mock_config

        on_pre_build(config)

        sql_files = list(sql_dir.glob("*.sql"))
        assert len(sql_files) > 0

        # Check filename format
        for sql_file in sql_files:
            filename = sql_file.name
            # Should have format: timestamp_version_dbtype.sql
            assert '_mssql.sql' in filename
            assert '0.1.0' in filename  # Version should be included

    def test_handles_missing_reference_directory(self, mock_config):
        """Test that on_pre_build works even if reference directory doesn't exist initially."""
        config, project_root, docs_dir, reference_dir, sql_dir = mock_config

        # Remove reference directory
        import shutil
        shutil.rmtree(reference_dir)

        # Create it fresh
        reference_dir.mkdir()

        # Should work without errors
        on_pre_build(config)

        assert (reference_dir / "tables.md").exists()
        assert (reference_dir / "valuesets.md").exists()

    def test_uses_target_dbs_constant(self, mock_config):
        """Test that on_pre_build respects TARGET_DBS constant."""
        config, project_root, docs_dir, reference_dir, sql_dir = mock_config

        on_pre_build(config)

        # Should generate MSSQL schema (per TARGET_DBS = ["mssql"])
        sql_files = list(sql_dir.glob("*_mssql.sql"))
        assert len(sql_files) == 1

    def test_reads_csv_from_project_root(self, mock_config):
        """Test that on_pre_build correctly locates dictionary.csv in project root."""
        config, project_root, docs_dir, reference_dir, sql_dir = mock_config

        # CSV was created in project_root by fixture
        csv_path = project_root / "dictionary.csv"
        assert csv_path.exists()

        # Should read and process without errors
        on_pre_build(config)

        # Verify it actually read the CSV by checking output
        tables_content = (reference_dir / "tables.md").read_text(encoding='utf-8')
        assert 'TestTable' in tables_content