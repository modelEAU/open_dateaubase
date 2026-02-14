"""Tests for dictionary reference documentation generation."""

import pytest
import json
from pathlib import Path
import sys

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "tests"))
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from generate_dictionary_reference import (
    parse_parts_json,
    generate_tables_markdown,
    generate_value_sets_markdown,
)
from fixtures.sample_dictionary import sample_dictionary_data


@pytest.fixture
def sample_json_file(tmp_path):
    """Create a temporary JSON file with sample dictionary data."""
    json_file = tmp_path / "test_dictionary.json"
    json_file.write_text(json.dumps(sample_dictionary_data(), indent=2))
    return json_file


class TestParsePartsJson:
    """Tests for JSON parsing."""

    def test_parse_identifies_tables(self, sample_json_file):
        data = parse_parts_json(sample_json_file)
        
        assert "test_table" in data["tables"]
        assert data["tables"]["test_table"]["label"] == "Test Table"
        assert data["tables"]["test_table"]["description"] == "A test table for demonstration"

    def test_parse_identifies_fields(self, sample_json_file):
        data = parse_parts_json(sample_json_file)
        
        fields = data["tables"]["test_table"]["fields"]
        assert len(fields) >= 3

        # Check primary key
        pk_field = next(f for f in fields if f["part_id"] == "TestTable_ID")
        assert pk_field["part_type"] == "key"
        assert pk_field["is_required"] is True
        assert pk_field["sql_data_type"] == "int"

    def test_parse_identifies_value_sets(self, sample_json_file):
        data = parse_parts_json(sample_json_file)
        
        assert "StatusSet" in data["value_sets"]
        assert data["value_sets"]["StatusSet"]["label"] == "Status Set"
        assert len(data["value_sets"]["StatusSet"]["members"]) == 3

    def test_parse_sorts_fields_by_sort_order(self, sample_json_file):
        data = parse_parts_json(sample_json_file)
        
        fields = data["tables"]["test_table"]["fields"]
        sort_orders = [f["sort_order"] for f in fields]
        assert sort_orders == sorted(sort_orders)

    def test_parse_sorts_value_set_members(self, sample_json_file):
        data = parse_parts_json(sample_json_file)
        
        members = data["value_sets"]["StatusSet"]["members"]
        sort_orders = [m["sort_order"] for m in members]
        assert sort_orders == sorted(sort_orders)


class TestGenerateTablesMarkdown:
    """Tests for tables markdown generation."""

    def test_generates_valid_markdown(self, sample_json_file):
        data = parse_parts_json(sample_json_file)
        markdown = generate_tables_markdown(data)
        
        assert "# Database Tables" in markdown
        assert "## Tables" in markdown

    def test_includes_table_headings(self, sample_json_file):
        data = parse_parts_json(sample_json_file)
        markdown = generate_tables_markdown(data)
        
        assert "### Test Table" in markdown
        assert "A test table for demonstration" in markdown

    def test_includes_table_anchors(self, sample_json_file):
        data = parse_parts_json(sample_json_file)
        markdown = generate_tables_markdown(data)
        
        # Check for invisible anchor span
        assert '<span id="test_table"></span>' in markdown

    def test_includes_field_anchors(self, sample_json_file):
        data = parse_parts_json(sample_json_file)
        markdown = generate_tables_markdown(data)
        
        # Check for field anchors in description column
        assert '<span id="TestTable_ID"></span>' in markdown
        assert '<span id="Status"></span>' in markdown

    def test_generates_fields_table(self, sample_json_file):
        data = parse_parts_json(sample_json_file)
        markdown = generate_tables_markdown(data)
        
        # Check table header
        assert "| Field | SQL Type | Value Set | Required | Description | Constraints |" in markdown
        assert "|-------|----------|-----------|----------|-------------|-------------|" in markdown

    def test_marks_primary_keys(self, sample_json_file):
        data = parse_parts_json(sample_json_file)
        markdown = generate_tables_markdown(data)
        
        # Primary key should have PK marker
        assert "int **(PK)**" in markdown

    def test_marks_required_fields(self, sample_json_file):
        data = parse_parts_json(sample_json_file)
        markdown = generate_tables_markdown(data)
        
        # Should have checkmarks for required fields
        assert "✓" in markdown

    def test_links_to_value_sets(self, sample_json_file):
        data = parse_parts_json(sample_json_file)
        markdown = generate_tables_markdown(data)
        
        # Should link to value set
        assert "[StatusSet](valuesets.md#StatusSet)" in markdown


class TestGenerateValueSetsMarkdown:
    """Tests for value sets markdown generation."""

    def test_generates_valid_markdown(self, sample_json_file):
        data = parse_parts_json(sample_json_file)
        markdown = generate_value_sets_markdown(data)
        
        assert "# Value Sets" in markdown

    def test_includes_value_set_headings(self, sample_json_file):
        data = parse_parts_json(sample_json_file)
        markdown = generate_value_sets_markdown(data)
        
        assert "## Status Set" in markdown
        assert "Valid status values for records" in markdown

    def test_includes_value_set_anchors(self, sample_json_file):
        data = parse_parts_json(sample_json_file)
        markdown = generate_value_sets_markdown(data)
        
        # Check for invisible anchor span
        assert '<span id="StatusSet"></span>' in markdown

    def test_includes_member_anchors(self, sample_json_file):
        data = parse_parts_json(sample_json_file)
        markdown = generate_value_sets_markdown(data)
        
        # Check for member anchors
        assert '<span id="active"></span>' in markdown
        assert '<span id="inactive"></span>' in markdown

    def test_generates_members_table(self, sample_json_file):
        data = parse_parts_json(sample_json_file)
        markdown = generate_value_sets_markdown(data)
        
        # Check table header
        assert "| Value | Description |" in markdown
        assert "|-------|-------------|" in markdown

    def test_lists_all_members(self, sample_json_file):
        data = parse_parts_json(sample_json_file)
        markdown = generate_value_sets_markdown(data)
        
        assert "`active`" in markdown
        assert "Record is currently active" in markdown
        assert "`inactive`" in markdown
        assert "Record is currently inactive" in markdown

    def test_handles_empty_value_sets(self, tmp_path):
        # JSON with no value sets
        json_content = {
            "parts": [
                {
                    "Part_ID": "test_table",
                    "Label": "Test Table",
                    "Description": "A test table",
                    "Part_type": "table",
                }
            ]
        }
        json_file = tmp_path / "empty_valuesets.json"
        json_file.write_text(json.dumps(json_content))

        data = parse_parts_json(json_file)
        markdown = generate_value_sets_markdown(data)

        assert "No value sets currently appear in dictionary" in markdown


class TestIntegration:
    """Integration tests checking cross-referencing."""

    def test_value_set_links_are_bidirectional(self, sample_json_file):
        data = parse_parts_json(sample_json_file)
        tables_md = generate_tables_markdown(data)
        valuesets_md = generate_value_sets_markdown(data)

        # Table should link to value set
        assert "[StatusSet](valuesets.md#StatusSet)" in tables_md

        # Value set should have anchor that table links to
        assert '<span id="StatusSet"></span>' in valuesets_md


class TestEdgeCases:
    """Test edge cases and error handling for dictionary reference generation."""

    def test_empty_description_handling(self, tmp_path):
        """Test handling of empty descriptions."""
        json_data = {
            "parts": [
                {"Part_ID": "test_table", "Label": "Test Table", "Description": "", "Part_type": "table"}
            ]
        }
        json_file = tmp_path / "empty_desc.json"
        json_file.write_text(json.dumps(json_data))

        # Empty descriptions should not be allowed by validation
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            data = parse_parts_json(json_file)

    def test_table_with_no_fields(self, tmp_path):
        """Test handling of table with no fields."""
        json_data = {
            "parts": [
                {"Part_ID": "empty_table", "Label": "Empty Table", "Description": "No fields", "Part_type": "table"}
            ]
        }
        json_file = tmp_path / "no_fields.json"
        json_file.write_text(json.dumps(json_data))

        data = parse_parts_json(json_file)
        markdown = generate_tables_markdown(data)

        # Should handle tables with no fields
        assert "### Empty Table" in markdown
        assert "No fields" in markdown

    def test_value_set_with_no_members(self, tmp_path):
        """Test handling of value set with no members."""
        json_data = {
            "parts": [
                {"Part_ID": "EmptySet", "Label": "Empty Set", "Description": "No members", "Part_type": "valueSet"}
            ]
        }
        json_file = tmp_path / "empty_set.json"
        json_file.write_text(json.dumps(json_data))

        data = parse_parts_json(json_file)
        markdown = generate_value_sets_markdown(data)

        # Should handle empty value sets
        assert "## Empty Set" in markdown
        assert "No members" in markdown

    def test_special_characters_in_descriptions(self, tmp_path):
        """Test that special characters in descriptions are handled properly."""
        json_data = {
            "parts": [
                {
                    "Part_ID": "test_table",
                    "Label": "Test Table",
                    "Description": "Table with special chars: < > & \" '",
                    "Part_type": "table",
                }
            ]
        }
        json_file = tmp_path / "special_chars.json"
        json_file.write_text(json.dumps(json_data))

        data = parse_parts_json(json_file)
        markdown = generate_tables_markdown(data)

        # Should include the description with special characters
        assert "special chars" in markdown

    def test_very_long_table_names(self, tmp_path):
        """Test handling of very long table names."""
        long_name = "VeryLongTableNameThatExceedsNormalConventionsButIsStillValid"
        json_data = {
            "parts": [
                {
                    "Part_ID": long_name,
                    "Label": "Very Long Table Name",
                    "Description": "Test long names",
                    "Part_type": "table",
                }
            ]
        }
        json_file = tmp_path / "long_name.json"
        json_file.write_text(json.dumps(json_data))

        data = parse_parts_json(json_file)
        markdown = generate_tables_markdown(data)

        # Should handle long table names
        assert "Very Long Table Name" in markdown
        assert f'<span id="{long_name}"></span>' in markdown

    def test_missing_file_raises_error(self, tmp_path):
        """Test that missing JSON file raises appropriate error."""
        non_existent = tmp_path / "nonexistent.json"

        with pytest.raises(FileNotFoundError):
            parse_parts_json(non_existent)

    def test_malformed_json_raises_error(self, tmp_path):
        """Test that malformed JSON raises appropriate error."""
        json_file = tmp_path / "malformed.json"
        json_file.write_text("{ this is not valid json }")

        with pytest.raises(json.JSONDecodeError):
            parse_parts_json(json_file)

    def test_foreign_key_display(self, sample_json_file):
        """Test that foreign keys are properly displayed in markdown."""
        data = parse_parts_json(sample_json_file)
        markdown = generate_tables_markdown(data)

        # Parent_ID FK should be displayed with link
        assert "FK →" in markdown
        assert "[TestTable_ID]" in markdown
