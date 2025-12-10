"""Tests for Pydantic models."""

import pytest
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from open_dateaubase.models import (
    Dictionary, TablePart, KeyPart, PropertyPart,
    TablePresence, ValueSetPart, ValueSetMemberPart,
    ParentKeyPart
)


class TestTablePresence:
    def test_valid_table_presence(self):
        presence = TablePresence(role="key", required=True, order=1)
        assert presence.role == "key"
        assert presence.required is True
        assert presence.order == 1


class TestTablePart:
    def test_valid_table(self):
        table = TablePart(
            part_id="test_table",
            label="Test Table",
            description="A test table",
            part_type="table"
        )
        assert table.part_id == "test_table"


class TestKeyPart:
    def test_valid_key(self):
        key = KeyPart(
            part_id="Test_ID",
            label="Test ID",
            description="Test identifier",
            part_type="key",
            table_presence={
                "test_table": TablePresence(role="key", required=True, order=1)
            }
        )
        assert key.part_id == "Test_ID"

    def test_key_without_id_suffix(self):
        with pytest.raises(ValueError, match="should end with '_ID'"):
            KeyPart(
                part_id="TestKey",
                label="Test",
                description="Test",
                part_type="key",
                table_presence={
                    "test": TablePresence(role="key", required=True, order=1)
                }
            )


class TestParentKeyPart:
    def test_valid_parent_key(self):
        parent = ParentKeyPart(
            part_id="Parent_ID",
            label="Parent",
            description="Hierarchical parent",
            part_type="parentKey",
            ancestor_part_id="Test_ID",
            table_presence={
                "test": TablePresence(role="property", required=False, order=2)
            }
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
                    "Part_type": "table"
                },
                {
                    "Part_ID": "Test_ID",
                    "Label": "Test ID",
                    "Description": "Test key",
                    "Part_type": "key",
                    "table_presence": {
                        "test_table": {
                            "role": "key",
                            "required": True,
                            "order": 1
                        }
                    }
                }
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
                    "Part_type": "table"
                },
                {
                    "Part_ID": "duplicate",
                    "Label": "Dup 2",
                    "Description": "Second",
                    "Part_type": "table"
                }
            ]
        }
        with pytest.raises(ValueError, match="Duplicate Part_IDs"):
            Dictionary.model_validate(data)
