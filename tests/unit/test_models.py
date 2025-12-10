"""Tests for Pydantic models."""

import pytest
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from open_dateaubase.data_model.models import (
    Dictionary,
    TablePart,
    KeyPart,
    PropertyPart,
    TablePresence,
    ValueSetPart,
    ValueSetMemberPart,
    ParentKeyPart,
)


class TestTablePresence:
    def test_valid_table_presence(self):
        presence = TablePresence(
            role="key", required=True, order=1, relationship_type=None
        )
        assert presence.role == "key"
        assert presence.required is True
        assert presence.order == 1


class TestTablePart:
    def test_valid_table(self):
        table = TablePart(
            Part_ID="test_table",
            Label="Test Table",
            Description="A test table",
            Part_type="table",
            Sort_order=None,
        )
        assert table.part_id == "test_table"


class TestKeyPart:
    def test_valid_key(self):
        key = KeyPart(
            Part_ID="Test_ID",
            Label="Test ID",
            Description="Test identifier",
            Part_type="key",
            SQL_data_type=None,
            Is_required=False,
            Default_value=None,
            Value_set_part_ID=None,
            table_presence={
                "test_table": TablePresence(
                    role="key", required=True, order=1, relationship_type=None
                )
            },
        )
        assert key.part_id == "Test_ID"

    def test_key_without_id_suffix(self):
        with pytest.raises(ValueError, match="should end with '_ID'"):
            KeyPart(
                Part_ID="TestKey",
                Label="Test",
                Description="Test",
                Part_type="key",
                SQL_data_type=None,
                Is_required=False,
                Default_value=None,
                Value_set_part_ID=None,
                table_presence={
                    "test": TablePresence(
                        role="key", required=True, order=1, relationship_type=None
                    )
                },
            )


class TestParentKeyPart:
    def test_valid_parent_key(self):
        parent = ParentKeyPart(
            Part_ID="Parent_ID",
            Label="Parent",
            Description="Hierarchical parent",
            Part_type="parentKey",
            Ancestor_part_ID="Test_ID",
            SQL_data_type=None,
            Is_required=False,
            Default_value=None,
            Value_set_part_ID=None,
            table_presence={
                "test": TablePresence(
                    role="property", required=False, order=2, relationship_type=None
                )
            },
        )
        assert parent.ancestor_part_id == "Test_ID"


class TestDictionary:
    def test_valid_dictionary(self):
        data = {
            "parts": [
                {
                    "Part_ID": "test_table",
                    "Label": "Test",
                    "Description": "Test table",
                    "Part_type": "table",
                },
                {
                    "Part_ID": "Test_ID",
                    "Label": "Test ID",
                    "Description": "Test key",
                    "Part_type": "key",
                    "table_presence": {
                        "test_table": {"role": "key", "required": True, "order": 1}
                    },
                },
            ]
        }
        dictionary = Dictionary.model_validate(data)
        assert len(dictionary.parts) == 2

    def test_duplicate_part_ids(self):
        data = {
            "parts": [
                {
                    "Part_ID": "duplicate",
                    "Label": "Dup 1",
                    "Description": "First",
                    "Part_type": "table",
                },
                {
                    "Part_ID": "duplicate",
                    "Label": "Dup 2",
                    "Description": "Second",
                    "Part_type": "table",
                },
            ]
        }
        with pytest.raises(ValueError, match="Duplicate Part_IDs"):
            Dictionary.model_validate(data)
