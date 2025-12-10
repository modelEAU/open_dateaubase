"""Integration tests for documentation orchestration workflow."""

import pytest
import json
from pathlib import Path
import sys

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "tests"))
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))

from orchestrate_docs import main as orchestrate_main
from generate_dictionary_reference import parse_parts_json, generate_tables_markdown, generate_value_sets_markdown
from generate_erd import parse_erd_json, generate_erd_files
from generate_sql import generate_sql_schemas
from fixtures.sample_dictionary import sample_dictionary_data


@pytest.fixture
def sample_json_file(tmp_path):
    """Create a temporary JSON file with sample dictionary data."""
    json_file = tmp_path / "dictionary.json"
    json_file.write_text(json.dumps(sample_dictionary_data(), indent=2))
    return json_file


@pytest.fixture
def output_dirs(tmp_path):
    """Create temporary output directories."""
    docs_dir = tmp_path / "docs" / "reference"
    sql_dir = tmp_path / "sql_generation_scripts"
    assets_dir = tmp_path / "docs" / "assets"
    
    docs_dir.mkdir(parents=True, exist_ok=True)
    sql_dir.mkdir(parents=True, exist_ok=True)
    assets_dir.mkdir(parents=True, exist_ok=True)
    
    return {
        "docs": docs_dir,
        "sql": sql_dir,
        "assets": assets_dir,
        "root": tmp_path,
    }


class TestOrchestrationWorkflow:
    """Test the complete documentation generation workflow."""

    def test_generates_all_documentation_components(self, sample_json_file, output_dirs):
        """Test that all documentation components are generated."""
        parts_data = parse_parts_json(sample_json_file)
        
        # Generate all components
        tables = generate_tables_markdown(parts_data)
        value_sets = generate_value_sets_markdown(parts_data)
        
        # Write documentation
        (output_dirs["docs"] / "tables.md").write_text(tables, encoding="utf-8")
        (output_dirs["docs"] / "valuesets.md").write_text(value_sets, encoding="utf-8")
        
        # Generate ERD
        erd_parts_data = parse_erd_json(sample_json_file)
        generate_erd_files(erd_parts_data, output_dirs["assets"], output_dirs["docs"])
        
        # Generate SQL
        generate_sql_schemas(parts_data, output_dirs["sql"], ["mssql"])
        
        # Verify all files were created
        assert (output_dirs["docs"] / "tables.md").exists()
        assert (output_dirs["docs"] / "valuesets.md").exists()
        assert (output_dirs["docs"] / "erd.md").exists()
        assert (output_dirs["assets"] / "erd_interactive.html").exists()
        assert len(list(output_dirs["sql"].glob("*.sql"))) == 1

    def test_tables_markdown_contains_expected_content(self, sample_json_file, output_dirs):
        """Test that generated tables.md has correct content."""
        parts_data = parse_parts_json(sample_json_file)
        tables = generate_tables_markdown(parts_data)
        (output_dirs["docs"] / "tables.md").write_text(tables, encoding="utf-8")
        
        content = (output_dirs["docs"] / "tables.md").read_text(encoding="utf-8")
        
        assert "# Database Tables" in content
        assert "### Test Table" in content
        assert '<span id="test_table"></span>' in content
        assert '<span id="TestTable_ID"></span>' in content

    def test_valuesets_markdown_contains_expected_content(self, sample_json_file, output_dirs):
        """Test that generated valuesets.md has correct content."""
        parts_data = parse_parts_json(sample_json_file)
        value_sets = generate_value_sets_markdown(parts_data)
        (output_dirs["docs"] / "valuesets.md").write_text(value_sets, encoding="utf-8")
        
        content = (output_dirs["docs"] / "valuesets.md").read_text(encoding="utf-8")
        
        assert "# Value Sets" in content
        assert "## Status Set" in content
        assert '<span id="StatusSet"></span>' in content

    def test_erd_generation_creates_html(self, sample_json_file, output_dirs):
        """Test that ERD generation creates the interactive HTML."""
        erd_parts_data = parse_erd_json(sample_json_file)
        generate_erd_files(erd_parts_data, output_dirs["assets"], output_dirs["docs"])
        
        # Check interactive HTML exists
        interactive_html = output_dirs["assets"] / "erd_interactive.html"
        assert interactive_html.exists()
        
        # Check content
        content = interactive_html.read_text()
        assert "JointJS" in content or "jointjs" in content
        assert "Test Table" in content

    def test_sql_generation_creates_schema_file(self, sample_json_file, output_dirs):
        """Test that SQL generation creates schema files."""
        parts_data = parse_parts_json(sample_json_file)
        generate_sql_schemas(parts_data, output_dirs["sql"], ["mssql"])
        
        sql_files = list(output_dirs["sql"].glob("*.sql"))
        assert len(sql_files) == 1
        
        # Check filename format
        sql_file = sql_files[0]
        assert "_as-designed_mssql.sql" in sql_file.name
        
        # Check content
        content = sql_file.read_text(encoding="utf-8")
        assert "CREATE TABLE [test_table]" in content
        assert "PRIMARY KEY" in content

    def test_multiple_database_targets(self, sample_json_file, output_dirs):
        """Test that multiple database schemas can be generated."""
        parts_data = parse_parts_json(sample_json_file)
        
        # Currently only mssql is supported, but test the structure
        generate_sql_schemas(parts_data, output_dirs["sql"], ["mssql"])
        
        sql_files = list(output_dirs["sql"].glob("*_mssql.sql"))
        assert len(sql_files) == 1

    def test_workflow_handles_empty_value_sets(self, tmp_path, output_dirs):
        """Test that workflow handles dictionaries with no value sets."""
        json_data = {
            "parts": [
                {
                    "Part_ID": "test_table",
                    "Label": "Test Table",
                    "Description": "A test table",
                    "Part_type": "table",
                }
            ]
        }
        json_file = tmp_path / "no_valuesets.json"
        json_file.write_text(json.dumps(json_data))
        
        parts_data = parse_parts_json(json_file)
        value_sets = generate_value_sets_markdown(parts_data)
        (output_dirs["docs"] / "valuesets.md").write_text(value_sets, encoding="utf-8")
        
        content = (output_dirs["docs"] / "valuesets.md").read_text(encoding="utf-8")
        assert "No value sets currently appear in dictionary" in content

    def test_cross_references_between_components(self, sample_json_file, output_dirs):
        """Test that cross-references between components work correctly."""
        parts_data = parse_parts_json(sample_json_file)
        
        tables = generate_tables_markdown(parts_data)
        value_sets = generate_value_sets_markdown(parts_data)
        
        # Tables should link to value sets
        assert "[StatusSet](valuesets.md#StatusSet)" in tables
        
        # Value sets should have anchors that tables link to
        assert '<span id="StatusSet"></span>' in value_sets
