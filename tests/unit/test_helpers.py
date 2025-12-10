"""Tests for DictionaryManager class in helpers.py."""

import pytest
import json
import tempfile
from pathlib import Path
import sys

# Add src and fixtures to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent / "fixtures"))

from open_dateaubase.data_model.helpers import DictionaryManager
from open_dateaubase.data_model.models import Dictionary
from sample_dictionary import (
    sample_dictionary_data,
    complex_dictionary_data,
    edge_case_dictionary_data,
    invalid_dictionary_data,
)


class TestDictionaryManager:
    """Test basic DictionaryManager functionality."""

    def test_load_valid_dictionary(self, tmp_path):
        """Test loading a valid dictionary JSON file."""
        dict_data = sample_dictionary_data()
        dict_file = tmp_path / "test_dict.json"
        dict_file.write_text(json.dumps(dict_data, indent=2))

        manager = DictionaryManager.load(dict_file)

        assert manager.dictionary is not None
        assert (
            len(manager.dictionary.parts) == 9
        )  # Count parts in sample data (including value set members)
        assert manager.path == dict_file

    def test_load_invalid_json(self, tmp_path):
        """Test loading invalid JSON raises error."""
        dict_file = tmp_path / "invalid.json"
        dict_file.write_text("{ invalid json }")

        with pytest.raises(json.JSONDecodeError):
            DictionaryManager.load(dict_file)

    def test_save_dictionary(self, tmp_path):
        """Test saving dictionary to JSON file."""
        dict_data = sample_dictionary_data()
        dict_file = tmp_path / "test_dict.json"
        dict_file.write_text(json.dumps(dict_data, indent=2))

        manager = DictionaryManager.load(dict_file)

        # Modify and save
        save_file = tmp_path / "saved_dict.json"
        manager.save(save_file)

        assert save_file.exists()
        saved_data = json.loads(save_file.read_text())

        # Should have PascalCase keys
        assert "Part_ID" in saved_data["parts"][0]
        assert "Part_type" in saved_data["parts"][0]

    def test_save_to_original_path(self, tmp_path):
        """Test saving dictionary to original path when no path specified."""
        dict_data = sample_dictionary_data()
        dict_file = tmp_path / "test_dict.json"
        dict_file.write_text(json.dumps(dict_data, indent=2))

        manager = DictionaryManager.load(dict_file)
        manager.save()  # Save to original path

        # File should be updated
        modified_time = dict_file.stat().st_mtime
        assert modified_time > 0


class TestValueSetOperations:
    """Test value set creation and management."""

    def test_create_value_set(self, tmp_path):
        """Test creating a new value set."""
        dict_data = sample_dictionary_data()
        dict_file = tmp_path / "test_dict.json"
        dict_file.write_text(json.dumps(dict_data, indent=2))

        manager = DictionaryManager.load(dict_file)
        manager.create_value_set("NewStatusSet", "New Status Values", "Test status set")

        # Check value set was created
        new_vs = manager._find_part("NewStatusSet")
        assert new_vs is not None
        assert new_vs.part_id == "NewStatusSet"
        assert new_vs.label == "New Status Values"
        assert hasattr(new_vs, "part_type") and new_vs.part_type == "valueSet"

    def test_create_duplicate_value_set_fails(self, tmp_path):
        """Test creating duplicate value set raises error."""
        dict_data = sample_dictionary_data()
        dict_file = tmp_path / "test_dict.json"
        dict_file.write_text(json.dumps(dict_data, indent=2))

        manager = DictionaryManager.load(dict_file)

        with pytest.raises(ValueError, match="Part 'StatusSet' already exists"):
            manager.create_value_set("StatusSet", "Duplicate", "Should fail")

    def test_add_value_set_member(self, tmp_path):
        """Test adding a member to existing value set."""
        dict_data = sample_dictionary_data()
        dict_file = tmp_path / "test_dict.json"
        dict_file.write_text(json.dumps(dict_data, indent=2))

        manager = DictionaryManager.load(dict_file)
        manager.add_value_set_member(
            "StatusSet", "suspended", "Suspended", "Suspended status", order=4
        )

        # Check member was added
        new_member = manager._find_part("suspended")
        assert new_member is not None
        assert new_member.part_id == "suspended"
        assert new_member.label == "Suspended"
        assert (
            hasattr(new_member, "member_of_set_part_id")
            and new_member.member_of_set_part_id == "StatusSet"
        )
        assert new_member.sort_order == 4

    def test_add_member_to_nonexistent_value_set_fails(self, tmp_path):
        """Test adding member to non-existent value set raises error."""
        dict_data = sample_dictionary_data()
        dict_file = tmp_path / "test_dict.json"
        dict_file.write_text(json.dumps(dict_data, indent=2))

        manager = DictionaryManager.load(dict_file)

        with pytest.raises(
            ValueError, match="Value set 'NonExistentSet' does not exist"
        ):
            manager.add_value_set_member(
                "NonExistentSet", "test", "Test", "Test member"
            )

    def test_add_duplicate_member_fails(self, tmp_path):
        """Test adding duplicate member raises error."""
        dict_data = sample_dictionary_data()
        dict_file = tmp_path / "test_dict.json"
        dict_file.write_text(json.dumps(dict_data, indent=2))

        manager = DictionaryManager.load(dict_file)

        with pytest.raises(ValueError, match="Part 'active' already exists"):
            manager.add_value_set_member(
                "StatusSet", "active", "Duplicate Active", "Should fail"
            )


class TestTableOperations:
    """Test table creation and field management."""

    def test_create_table(self, tmp_path):
        """Test creating a new table."""
        dict_data = sample_dictionary_data()
        dict_file = tmp_path / "test_dict.json"
        dict_file.write_text(json.dumps(dict_data, indent=2))

        manager = DictionaryManager.load(dict_file)
        manager.create_table("new_table", "New Table", "A new test table")

        # Check table was created
        new_table = manager._find_part("new_table")
        assert new_table is not None
        assert new_table.part_id == "new_table"
        assert new_table.label == "New Table"
        assert hasattr(new_table, "part_type") and new_table.part_type == "table"

    def test_create_duplicate_table_fails(self, tmp_path):
        """Test creating duplicate table raises error."""
        dict_data = sample_dictionary_data()
        dict_file = tmp_path / "test_dict.json"
        dict_file.write_text(json.dumps(dict_data, indent=2))

        manager = DictionaryManager.load(dict_file)

        with pytest.raises(ValueError, match="Part 'test_table' already exists"):
            manager.create_table("test_table", "Duplicate", "Should fail")

    def test_add_field_to_table(self, tmp_path):
        """Test adding a new field to existing table."""
        dict_data = sample_dictionary_data()
        dict_file = tmp_path / "test_dict.json"
        dict_file.write_text(json.dumps(dict_data, indent=2))

        manager = DictionaryManager.load(dict_file)
        manager.add_field_to_table(
            table_id="test_table",
            field_id="NewField",
            label="New Field",
            description="A new test field",
            role="property",
            sql_data_type="nvarchar(100)",
            required=True,
            order=5,
        )

        # Check field was created
        new_field = manager._find_part("NewField")
        assert new_field is not None
        assert new_field.part_id == "NewField"
        assert new_field.label == "New Field"
        assert hasattr(new_field, "part_type") and new_field.part_type == "property"
        assert (
            hasattr(new_field, "table_presence")
            and "test_table" in new_field.table_presence
        )

    def test_add_field_to_nonexistent_table_fails(self, tmp_path):
        """Test adding field to non-existent table raises error."""
        dict_data = sample_dictionary_data()
        dict_file = tmp_path / "test_dict.json"
        dict_file.write_text(json.dumps(dict_data, indent=2))

        manager = DictionaryManager.load(dict_file)

        with pytest.raises(ValueError, match="Table 'NonExistentTable' does not exist"):
            manager.add_field_to_table(
                "NonExistentTable", "TestField", "Test Field", "Test description"
            )

    def test_add_key_field(self, tmp_path):
        """Test adding a primary key field."""
        dict_data = sample_dictionary_data()
        dict_file = tmp_path / "test_dict.json"
        dict_file.write_text(json.dumps(dict_data, indent=2))

        manager = DictionaryManager.load(dict_file)
        manager.add_field_to_table(
            table_id="test_table",
            field_id="NewTable_ID",
            label="New Table ID",
            description="Primary key for new table",
            role="key",
            sql_data_type="int",
            required=True,
            order=6,
        )

        # Check key field was created
        new_key = manager._find_part("NewTable_ID")
        assert new_key is not None
        assert new_key.part_id == "NewTable_ID"
        assert hasattr(new_key, "part_type") and new_key.part_type == "key"
        assert (
            hasattr(new_key, "table_presence")
            and "test_table" in new_key.table_presence
        )

    def test_add_parent_key(self, tmp_path):
        """Test adding a parent key for hierarchical relationships."""
        dict_data = sample_dictionary_data()
        dict_file = tmp_path / "test_dict.json"
        dict_file.write_text(json.dumps(dict_data, indent=2))

        manager = DictionaryManager.load(dict_file)
        manager.add_parent_key(
            table_id="test_table",
            parent_key_id="Parent_TestTable_ID",
            ancestor_key_id="TestTable_ID",
            label="Parent TestTable ID",
            description="Parent reference",
            sql_data_type="int",
            required=False,
            order=5,
        )

        # Check parent key was created
        parent_key = manager._find_part("Parent_TestTable_ID")
        assert parent_key is not None
        assert parent_key.part_id == "Parent_TestTable_ID"
        assert hasattr(parent_key, "part_type") and parent_key.part_type == "parentKey"
        assert (
            hasattr(parent_key, "ancestor_part_id")
            and parent_key.ancestor_part_id == "TestTable_ID"
        )


class TestQueryOperations:
    """Test query methods for retrieving dictionary information."""

    def test_get_value_set_members(self, tmp_path):
        """Test retrieving members of a value set."""
        dict_data = sample_dictionary_data()
        dict_file = tmp_path / "test_dict.json"
        dict_file.write_text(json.dumps(dict_data, indent=2))

        manager = DictionaryManager.load(dict_file)
        members = manager.get_value_set_members("Status")

        assert len(members) == 3
        member_ids = [m["Part_ID"] for m in members]
        assert "active" in member_ids
        assert "inactive" in member_ids
        assert "pending" in member_ids

        # Check sorting by sort_order
        sort_orders = [m["Sort_order"] for m in members]
        assert sort_orders == sorted(sort_orders)

    def test_get_value_set_members_nonexistent_field(self, tmp_path):
        """Test getting members for non-existent field returns empty list."""
        dict_data = sample_dictionary_data()
        dict_file = tmp_path / "test_dict.json"
        dict_file.write_text(json.dumps(dict_data, indent=2))

        manager = DictionaryManager.load(dict_file)
        members = manager.get_value_set_members("NonExistentField")

        assert members == []

    def test_get_value_set_members_field_without_value_set(self, tmp_path):
        """Test getting members for field without value set returns empty list."""
        dict_data = sample_dictionary_data()
        dict_file = tmp_path / "test_dict.json"
        dict_file.write_text(json.dumps(dict_data, indent=2))

        manager = DictionaryManager.load(dict_file)
        members = manager.get_value_set_members(
            "Description"
        )  # This field has no value set

        assert members == []

    def test_get_table_columns(self, tmp_path):
        """Test retrieving all columns for a table."""
        dict_data = sample_dictionary_data()
        dict_file = tmp_path / "test_dict.json"
        dict_file.write_text(json.dumps(dict_data, indent=2))

        manager = DictionaryManager.load(dict_file)
        columns = manager.get_table_columns("test_table")

        assert len(columns) == 4  # TestTable_ID, Status, Description, Parent_ID
        column_ids = [c["Part_ID"] for c in columns]
        assert "TestTable_ID" in column_ids
        assert "Status" in column_ids
        assert "Description" in column_ids
        assert "Parent_ID" in column_ids

        # Check sorting by order
        orders = [c["Order"] for c in columns]
        assert orders == sorted(orders)

    def test_get_table_columns_nonexistent_table(self, tmp_path):
        """Test getting columns for non-existent table returns empty list."""
        dict_data = sample_dictionary_data()
        dict_file = tmp_path / "test_dict.json"
        dict_file.write_text(json.dumps(dict_data, indent=2))

        manager = DictionaryManager.load(dict_file)
        columns = manager.get_table_columns("NonExistentTable")

        assert columns == []

    def test_get_primary_keys(self, tmp_path):
        """Test retrieving all primary keys in dictionary."""
        dict_data = complex_dictionary_data()
        dict_file = tmp_path / "test_dict.json"
        dict_file.write_text(json.dumps(dict_data, indent=2))

        manager = DictionaryManager.load(dict_file)
        primary_keys = manager.get_primary_keys()

        assert len(primary_keys) == 2  # Contact_ID, Project_ID
        key_ids = [k["Part_ID"] for k in primary_keys]
        assert "Contact_ID" in key_ids
        assert "Project_ID" in key_ids

    def test_list_tables(self, tmp_path):
        """Test listing all tables in dictionary."""
        dict_data = complex_dictionary_data()
        dict_file = tmp_path / "test_dict.json"
        dict_file.write_text(json.dumps(dict_data, indent=2))

        manager = DictionaryManager.load(dict_file)
        tables = manager.list_tables()

        assert len(tables) == 3  # contact, project, project_has_contact
        assert "contact" in tables
        assert "project" in tables
        assert "project_has_contact" in tables

    def test_list_value_sets(self, tmp_path):
        """Test listing all value sets in dictionary."""
        dict_data = sample_dictionary_data()
        dict_file = tmp_path / "test_dict.json"
        dict_file.write_text(json.dumps(dict_data, indent=2))

        manager = DictionaryManager.load(dict_file)
        value_sets = manager.list_value_sets()

        assert len(value_sets) == 1
        assert "StatusSet" in value_sets


class TestEdgeCasesAndErrorHandling:
    """Test edge cases and error handling in DictionaryManager."""

    def test_handle_very_long_field_names(self, tmp_path):
        """Test handling of fields with very long names."""
        dict_data = edge_case_dictionary_data()
        dict_file = tmp_path / "test_dict.json"
        dict_file.write_text(json.dumps(dict_data, indent=2))

        manager = DictionaryManager.load(dict_file)

        # Should be able to load and work with long field names
        long_field = manager._find_part(
            "VeryLongFieldNameThatExceedsNormalDatabaseLimitsAndMightCauseIssues"
        )
        assert long_field is not None
        assert len(long_field.part_id) > 50

    def test_handle_special_characters_in_names(self, tmp_path):
        """Test handling of special characters in table/field names."""
        dict_data = edge_case_dictionary_data()
        dict_file = tmp_path / "test_dict.json"
        dict_file.write_text(json.dumps(dict_data, indent=2))

        manager = DictionaryManager.load(dict_file)

        # Should handle special characters in labels but not in part IDs
        special_table = manager._find_part("special_table")
        assert special_table is not None
        assert "Special-Table!" in special_table.label
        assert "@" in special_table.description

    def test_validate_method(self, tmp_path):
        """Test explicit validation method."""
        dict_data = sample_dictionary_data()
        dict_file = tmp_path / "test_dict.json"
        dict_file.write_text(json.dumps(dict_data, indent=2))

        manager = DictionaryManager.load(dict_file)

        # Should not raise for valid data
        manager.validate()

        # Corrupt the data in a way that will fail validation
        original_part_id = manager.dictionary.parts[0].part_id
        manager.dictionary.parts[0].part_id = ""  # Invalid empty ID
        with pytest.raises(ValueError):
            manager.validate()

        # Restore for cleanup
        manager.dictionary.parts[0].part_id = original_part_id

    def test_build_complete_dictionary_workflow(self, tmp_path):
        """Test building a complete dictionary from scratch."""
        # Start with empty dictionary
        empty_data = {"parts": []}
        dict_file = tmp_path / "empty_dict.json"
        dict_file.write_text(json.dumps(empty_data, indent=2))

        manager = DictionaryManager.load(dict_file)

        # Create value set
        manager.create_value_set(
            "PrioritySet", "Priority Levels", "Task priority levels"
        )
        manager.add_value_set_member(
            "PrioritySet", "high", "High", "High priority", order=1
        )
        manager.add_value_set_member(
            "PrioritySet", "medium", "Medium", "Medium priority", order=2
        )
        manager.add_value_set_member(
            "PrioritySet", "low", "Low", "Low priority", order=3
        )

        # Create table
        manager.create_table("task", "Task", "Task management table")

        # Add fields to table
        manager.add_field_to_table(
            "task",
            "Task_ID",
            "Task ID",
            "Primary key",
            role="key",
            sql_data_type="int",
            required=True,
            order=1,
        )
        manager.add_field_to_table(
            "task",
            "Title",
            "Title",
            "Task title",
            role="property",
            sql_data_type="nvarchar(255)",
            required=True,
            order=2,
        )
        manager.add_field_to_table(
            "task",
            "Priority",
            "Priority",
            "Task priority",
            role="property",
            sql_data_type="nvarchar(20)",
            required=False,
            value_set_id="PrioritySet",
            order=3,
        )
        manager.add_field_to_table(
            "task",
            "Created_Date",
            "Created Date",
            "Creation timestamp",
            role="property",
            sql_data_type="datetime",
            required=True,
            default_value="GETDATE()",
            order=4,
        )

        # Verify the complete structure
        tables = manager.list_tables()
        value_sets = manager.list_value_sets()
        task_columns = manager.get_table_columns("task")
        priority_members = manager.get_value_set_members("Priority")

        assert len(tables) == 1
        assert len(value_sets) == 1
        assert len(task_columns) == 4  # Task_ID, Title, Priority, Created_Date
        assert len(priority_members) == 3

        # Verify specific relationships
        priority_field = manager._find_part("Priority")
        assert (
            hasattr(priority_field, "value_set_part_id")
            and priority_field.value_set_part_id == "PrioritySet"
        )
