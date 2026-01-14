"""Tests for SQL schema generation from dictionary."""

import pytest
import json
from pathlib import Path
import sys

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "tests"))
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from generate_sql import (
    parse_parts_json,
    generate_sql_schema,
    generate_field_definition,
    generate_foreign_key_constraint,
    validate_no_circular_fks,
    get_db_config,
    extract_field_name,
    generate_sql_schemas,
)
from fixtures.sample_dictionary import sample_dictionary_data


@pytest.fixture
def sample_json_file(tmp_path):
    """Create a temporary JSON file with sample dictionary data."""
    json_file = tmp_path / "test_dictionary.json"
    json_file.write_text(json.dumps(sample_dictionary_data(), indent=2))
    return json_file


class TestParsePartsJson:
    """Tests for JSON parsing function."""

    def test_parse_identifies_tables(self, sample_json_file):
        data = parse_parts_json(sample_json_file)
        assert "test_table" in data["tables"]
        assert data["tables"]["test_table"]["label"] == "Test Table"

    def test_parse_identifies_fields(self, sample_json_file):
        data = parse_parts_json(sample_json_file)
        fields = data["tables"]["test_table"]["fields"]

        # Should have: ID, Status, Description, Parent_ID
        assert len(fields) >= 3

        # Check primary key field exists
        pk_field = next((f for f in fields if f["part_id"] == "TestTable_ID"), None)
        assert pk_field is not None
        assert pk_field["part_type"] == "key"
        assert pk_field["is_required"] is True

    def test_parse_identifies_value_sets(self, sample_json_file):
        data = parse_parts_json(sample_json_file)
        assert "StatusSet" in data["value_sets"]
        assert len(data["value_sets"]["StatusSet"]["members"]) == 3


class TestGenerateSQLSchema:
    """Tests for SQL schema generation."""

    def test_generates_create_table_statement(self, sample_json_file):
        data = parse_parts_json(sample_json_file)
        sql = generate_sql_schema(data)
        assert "CREATE TABLE [test_table]" in sql

    def test_includes_all_fields(self, sample_json_file):
        data = parse_parts_json(sample_json_file)
        sql = generate_sql_schema(data)

        assert "[TestTable_ID]" in sql
        assert "[Status]" in sql
        assert "[Description]" in sql

    def test_generates_primary_key_constraint(self, sample_json_file):
        data = parse_parts_json(sample_json_file)
        sql = generate_sql_schema(data)

        assert "CONSTRAINT [PK_test_table] PRIMARY KEY" in sql
        assert "[TestTable_ID]" in sql

    def test_marks_required_fields_not_null(self, sample_json_file):
        data = parse_parts_json(sample_json_file)
        sql = generate_sql_schema(data)

        lines = sql.split("\n")
        testtable_id_line = next((l for l in lines if "[TestTable_ID]" in l and "PRIMARY KEY" not in l), None)
        assert testtable_id_line is not None
        assert "NOT NULL" in testtable_id_line

    def test_generates_foreign_key_constraints(self, sample_json_file):
        data = parse_parts_json(sample_json_file)
        sql = generate_sql_schema(data)

        assert "ALTER TABLE [test_table]" in sql
        assert "FOREIGN KEY ([Parent_ID])" in sql
        assert "REFERENCES [TestTable] ([TestTable_ID])" in sql


class TestExtractFieldName:
    """Tests for field name extraction helper."""

    def test_extracts_field_from_part_id(self):
        # ID fields are kept as-is
        assert extract_field_name("TestTable_ID") == "TestTable_ID"
        assert extract_field_name("Equipment_ID") == "Equipment_ID"

        # Table-prefixed non-ID fields: remove lowercase table prefix
        assert extract_field_name("site_City") == "City"
        assert extract_field_name("contact_City") == "City"

    def test_handles_part_id_without_underscore(self):
        assert extract_field_name("SimpleField") == "SimpleField"

    def test_handles_multiple_underscores(self):
        assert extract_field_name("Street_number") == "Street_number"


class TestDatabaseTargeting:
    """Tests for multi-database support."""

    def test_uses_mssql_bracket_quoting(self, sample_json_file):
        data = parse_parts_json(sample_json_file)
        sql = generate_sql_schema(data, target_db="mssql")

        assert "[test_table]" in sql
        assert "[TestTable_ID]" in sql

    def test_rejects_unsupported_database(self, sample_json_file):
        data = parse_parts_json(sample_json_file)

        with pytest.raises(ValueError, match="Unsupported database"):
            generate_sql_schema(data, target_db="oracle")

    def test_get_db_config_returns_correct_structure(self):
        config = get_db_config("mssql")

        assert "quote_char" in config
        assert "type_mappings" in config
        assert "supports_check_constraints" in config
        assert callable(config["quote"])


class TestEdgeCases:
    """Test edge cases and error handling for SQL generation."""

    def test_deprecated_ntext_type_mapping(self, tmp_path):
        """Test that deprecated ntext type is mapped to nvarchar(max)."""
        json_data = {
            "parts": [
                {"Part_ID": "test_table", "Label": "Test", "Description": "Test", "Part_type": "table"},
                {
                    "Part_ID": "Notes",
                    "Label": "Notes",
                    "Description": "Long text",
                    "Part_type": "property",
                    "SQL_data_type": "ntext",
                    "Is_required": False,
                    "table_presence": {"test_table": {"role": "property", "required": False, "order": 1}},
                },
            ]
        }
        json_file = tmp_path / "ntext.json"
        json_file.write_text(json.dumps(json_data))

        data = parse_parts_json(json_file)
        sql = generate_sql_schema(data)

        # ntext should be converted to nvarchar(max)
        assert "nvarchar(max)" in sql
        # ntext should not appear in actual SQL (only in comments is OK)
        sql_lines = [line for line in sql.split("\n") if not line.strip().startswith("--")]
        sql_without_comments = "\n".join(sql_lines)
        assert "ntext" not in sql_without_comments.lower()

    def test_boolean_default_value_conversion(self, tmp_path):
        """Test that boolean default values are converted to 0/1."""
        json_data = {
            "parts": [
                {"Part_ID": "test_table", "Label": "Test", "Description": "Test", "Part_type": "table"},
                {
                    "Part_ID": "IsActive",
                    "Label": "Is Active",
                    "Description": "Boolean field",
                    "Part_type": "property",
                    "SQL_data_type": "bit",
                    "Default_value": "True",
                    "Is_required": False,
                    "table_presence": {"test_table": {"role": "property", "required": False, "order": 1}},
                },
            ]
        }
        json_file = tmp_path / "bool.json"
        json_file.write_text(json.dumps(json_data))

        data = parse_parts_json(json_file)
        sql = generate_sql_schema(data)

        # Boolean default should be converted to 1
        assert "DEFAULT 1" in sql

    def test_very_long_field_names(self):
        """Test that very long field names are handled correctly."""
        long_name = "VeryLongFieldNameThatExceedsNormalDatabaseLimitsAndMightCauseIssues"
        assert extract_field_name(long_name) == long_name

    def test_field_names_with_numbers(self):
        """Test field names containing numbers."""
        assert extract_field_name("Field_1") == "Field_1"
        assert extract_field_name("table_Field123") == "Field123"
        assert extract_field_name("Field123_ID") == "Field123_ID"

    def test_empty_string_field_name(self):
        """Test handling of empty string field name."""
        assert extract_field_name("") == ""

    def test_single_character_field_names(self):
        """Test single character field names."""
        assert extract_field_name("A") == "A"
        assert extract_field_name("X") == "X"

    def test_empty_tables_list(self, tmp_path):
        """Test handling of dictionary with no tables."""
        json_data = {"parts": []}
        json_file = tmp_path / "empty.json"
        json_file.write_text(json.dumps(json_data))

        data = parse_parts_json(json_file)
        sql = generate_sql_schema(data)

        # Should generate valid SQL header even with no tables
        assert "Auto-generated SQL schema" in sql

    def test_missing_json_file_raises_error(self, tmp_path):
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

    def test_self_referential_fk_allowed(self, tmp_path):
        """Test that self-referential FKs (hierarchical) are allowed."""
        json_data = {
            "parts": [
                {"Part_ID": "category", "Label": "Category", "Description": "Hierarchical", "Part_type": "table"},
                {
                    "Part_ID": "Category_ID",
                    "Label": "Category ID",
                    "Description": "PK",
                    "Part_type": "key",
                    "SQL_data_type": "int",
                    "Is_required": True,
                    "table_presence": {"category": {"role": "key", "required": True, "order": 1}},
                },
                {
                    "Part_ID": "Parent_Category_ID",
                    "Label": "Parent Category ID",
                    "Description": "Parent",
                    "Part_type": "parentKey",
                    "Ancestor_part_ID": "Category_ID",
                    "SQL_data_type": "int",
                    "Is_required": False,
                    "table_presence": {"category": {"role": "property", "required": False, "order": 2}},
                },
            ]
        }
        json_file = tmp_path / "self_ref.json"
        json_file.write_text(json.dumps(json_data))

        data = parse_parts_json(json_file)

        # Should NOT raise - self-referential FKs are allowed
        sql = generate_sql_schema(data)
        assert "CREATE TABLE" in sql

    def test_table_with_many_fields(self, tmp_path):
        """Test handling of tables with many fields."""
        parts = [
            {"Part_ID": "big_table", "Label": "Big Table", "Description": "Table with many fields", "Part_type": "table"},
            # Add primary key
            {
                "Part_ID": "BigTable_ID",
                "Label": "Big Table ID",
                "Description": "Primary key",
                "Part_type": "key",
                "SQL_data_type": "int",
                "Is_required": True,
                "table_presence": {"big_table": {"role": "key", "required": True, "order": 1}},
            }
        ]

        # Add 50 fields
        for i in range(50):
            parts.append({
                "Part_ID": f"Field_{i}",
                "Label": f"Field {i}",
                "Description": f"Field number {i}",
                "Part_type": "property",
                "SQL_data_type": "int",
                "Is_required": False,
                "table_presence": {"big_table": {"role": "property", "required": False, "order": i + 2}},
            })

        json_data = {"parts": parts}
        json_file = tmp_path / "big_table.json"
        json_file.write_text(json.dumps(json_data))

        data = parse_parts_json(json_file)
        sql = generate_sql_schema(data)

        # Should generate SQL without errors
        assert "CREATE TABLE [big_table]" in sql
        assert "[Field_0]" in sql
        assert "[Field_49]" in sql
