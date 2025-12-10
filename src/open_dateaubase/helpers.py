"""
Helper functions for manipulating the dictionary.

Usage:
    from open_dateaubase.helpers import DictionaryManager

    mgr = DictionaryManager.load("src/dictionary.json")
    mgr.create_value_set("Status_set", "Valid status values")
    mgr.add_value_set_member("Status_set", "active", "Active status", order=1)
    mgr.save()
"""

from pathlib import Path
from typing import Optional, Literal
import json
from .models import (
    Dictionary, TablePart, KeyPart, PropertyPart,
    CompositeKeyFirstPart, CompositeKeySecondPart,
    ParentKeyPart, ValueSetPart, ValueSetMemberPart,
    TablePresence, Part
)


class DictionaryManager:
    """Manages dictionary operations with validation."""

    def __init__(self, dictionary: Dictionary, path: Path):
        self.dictionary = dictionary
        self.path = path

    @classmethod
    def load(cls, path: str | Path) -> "DictionaryManager":
        """Load dictionary from JSON file with validation."""
        path = Path(path)
        with open(path, 'r', encoding='utf-8') as f:
            raw_data = json.load(f)
        dictionary = Dictionary.model_validate(raw_data)
        return cls(dictionary, path)

    def save(self, path: Optional[Path] = None) -> None:
        """Save dictionary to JSON file."""
        target = path or self.path
        # Export as dict, convert to JSON with PascalCase keys
        data = self.dictionary.model_dump(by_alias=True)
        with open(target, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"Dictionary saved to {target}")

    def _find_part(self, part_id: str) -> Optional[Part]:
        """Find a part by Part_ID."""
        for part in self.dictionary.parts:
            if part.part_id == part_id:
                return part
        return None

    def _part_exists(self, part_id: str) -> bool:
        """Check if a part exists."""
        return self._find_part(part_id) is not None

    # ========================================================================
    # Value Set Operations
    # ========================================================================

    def create_value_set(
        self,
        part_id: str,
        label: str,
        description: str
    ) -> None:
        """Create a new value set."""
        if self._part_exists(part_id):
            raise ValueError(f"Part '{part_id}' already exists")

        value_set = ValueSetPart(
            part_id=part_id,
            label=label,
            description=description,
            part_type="valueSet"
        )
        self.dictionary.parts.append(value_set)
        # Re-validate entire dictionary
        self.dictionary = Dictionary.model_validate(
            self.dictionary.model_dump(by_alias=True)
        )
        print(f"Created value set '{part_id}'")

    def add_value_set_member(
        self,
        value_set_id: str,
        member_id: str,
        label: str,
        description: str,
        order: int = 999
    ) -> None:
        """Add a member to a value set."""
        if not self._part_exists(value_set_id):
            raise ValueError(f"Value set '{value_set_id}' does not exist")

        if self._part_exists(member_id):
            raise ValueError(f"Part '{member_id}' already exists")

        member = ValueSetMemberPart(
            part_id=member_id,
            label=label,
            description=description,
            part_type="valueSetMember",
            member_of_set_part_id=value_set_id,
            sort_order=order
        )
        self.dictionary.parts.append(member)
        # Re-validate
        self.dictionary = Dictionary.model_validate(
            self.dictionary.model_dump(by_alias=True)
        )
        print(f"Added member '{member_id}' to value set '{value_set_id}'")

    # ========================================================================
    # Table Operations
    # ========================================================================

    def create_table(
        self,
        table_id: str,
        label: str,
        description: str
    ) -> None:
        """Create a new table."""
        if self._part_exists(table_id):
            raise ValueError(f"Part '{table_id}' already exists")

        table = TablePart(
            part_id=table_id,
            label=label,
            description=description,
            part_type="table"
        )
        self.dictionary.parts.append(table)
        # Re-validate
        self.dictionary = Dictionary.model_validate(
            self.dictionary.model_dump(by_alias=True)
        )
        print(f"Created table '{table_id}'")

    def add_field_to_table(
        self,
        table_id: str,
        field_id: str,
        label: str,
        description: str,
        role: Literal["key", "property", "compositeKeyFirst", "compositeKeySecond"] = "property",
        sql_data_type: str = "nvarchar(255)",
        required: bool = False,
        order: int = 999,
        value_set_id: Optional[str] = None,
        default_value: Optional[str] = None
    ) -> None:
        """Add a field to a table (or update existing field's table_presence)."""
        if not self._part_exists(table_id):
            raise ValueError(f"Table '{table_id}' does not exist")

        existing_part = self._find_part(field_id)

        if existing_part:
            # Field exists - update its table_presence
            if not hasattr(existing_part, 'table_presence'):
                raise ValueError(
                    f"Part '{field_id}' exists but is not a field type"
                )

            # Add table presence
            existing_part.table_presence[table_id] = TablePresence(
                role=role,
                required=required,
                order=order
            )
            print(f"Added '{field_id}' to table '{table_id}' with role '{role}'")
        else:
            # Create new field
            presence = {
                table_id: TablePresence(
                    role=role,
                    required=required,
                    order=order
                )
            }

            # Determine field class based on role
            if role == "key":
                field_class = KeyPart
            elif role == "compositeKeyFirst":
                field_class = CompositeKeyFirstPart
            elif role == "compositeKeySecond":
                field_class = CompositeKeySecondPart
            else:
                field_class = PropertyPart

            field = field_class(
                part_id=field_id,
                label=label,
                description=description,
                part_type=role if role != "property" else "property",
                sql_data_type=sql_data_type,
                is_required=required,
                default_value=default_value,
                value_set_part_id=value_set_id,
                table_presence=presence
            )
            self.dictionary.parts.append(field)
            print(f"Created field '{field_id}' in table '{table_id}'")

        # Re-validate entire dictionary
        self.dictionary = Dictionary.model_validate(
            self.dictionary.model_dump(by_alias=True)
        )

    def add_parent_key(
        self,
        table_id: str,
        parent_key_id: str,
        ancestor_key_id: str,
        label: str,
        description: str,
        sql_data_type: str = "int",
        required: bool = False,
        order: int = 999
    ) -> None:
        """Add a hierarchical parent key to a table."""
        if not self._part_exists(table_id):
            raise ValueError(f"Table '{table_id}' does not exist")

        if not self._part_exists(ancestor_key_id):
            raise ValueError(f"Ancestor key '{ancestor_key_id}' does not exist")

        if self._part_exists(parent_key_id):
            raise ValueError(f"Part '{parent_key_id}' already exists")

        parent_key = ParentKeyPart(
            part_id=parent_key_id,
            label=label,
            description=description,
            part_type="parentKey",
            ancestor_part_id=ancestor_key_id,
            sql_data_type=sql_data_type,
            is_required=required,
            table_presence={
                table_id: TablePresence(
                    role="property",
                    required=required,
                    order=order
                )
            }
        )
        self.dictionary.parts.append(parent_key)
        # Re-validate
        self.dictionary = Dictionary.model_validate(
            self.dictionary.model_dump(by_alias=True)
        )
        print(f"Added parent key '{parent_key_id}' to table '{table_id}'")

    # ========================================================================
    # Validation & Integrity
    # ========================================================================

    def validate(self) -> None:
        """Explicitly validate the dictionary."""
        try:
            Dictionary.model_validate(self.dictionary.model_dump(by_alias=True))
            print("Dictionary is valid!")
        except Exception as e:
            print(f"Validation failed: {e}")
            raise

    def list_tables(self) -> list[str]:
        """List all table Part_IDs."""
        return [
            part.part_id
            for part in self.dictionary.parts
            if part.part_type == "table"
        ]

    def list_value_sets(self) -> list[str]:
        """List all value set Part_IDs."""
        return [
            part.part_id
            for part in self.dictionary.parts
            if part.part_type == "valueSet"
        ]
