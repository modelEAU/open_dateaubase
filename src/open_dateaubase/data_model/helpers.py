"""
Helper functions for manipulating the dictionary.

Usage:
    from open_dateaubase.helpers import DictionaryManager

    mgr = DictionaryManager.load("src/open_dateaubase/dictionary.json")
    mgr.create_value_set("Status_set", "Valid status values")
    mgr.add_value_set_member("Status_set", "active", "Active status", order=1)
    mgr.save()
"""

from pathlib import Path
from typing import Optional, Literal
import json
from .models import (
    Dictionary,
    TablePart,
    KeyPart,
    PropertyPart,
    CompositeKeyFirstPart,
    CompositeKeySecondPart,
    ParentKeyPart,
    ValueSetPart,
    ValueSetMemberPart,
    TablePresence,
    Part,
)


class DictionaryManager:
    """Manages dictionary operations with validation."""

    def __init__(self, dictionary: Dictionary, path: Path):
        self.dictionary = dictionary
        self.path = path

    @classmethod
    def load(cls, path: str | Path | None = None) -> "DictionaryManager":
        """Load dictionary from JSON file with validation."""
        if path is None:
            # Default path when no path specified
            from importlib.resources import files
            path = files('open_dateaubase').joinpath('dictionary.json')
        
        path = Path(path) if isinstance(path, str) else path
        with open(path, "r", encoding="utf-8") as f:
            raw_data = json.load(f)
        dictionary = Dictionary.model_validate(raw_data)
        return cls(dictionary, path)

    def save(self, path: Optional[Path] = None) -> None:
        """Save dictionary to JSON file."""
        target = path or self.path
        # Export as dict, convert to JSON with PascalCase keys
        data = self.dictionary.model_dump(by_alias=True)
        with open(target, "w", encoding="utf-8") as f:
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

    def create_value_set(self, part_id: str, label: str, description: str) -> None:
        """Create a new value set."""
        if self._part_exists(part_id):
            raise ValueError(f"Part '{part_id}' already exists")

        value_set = ValueSetPart(
            Part_ID=part_id, Label=label, Description=description, Part_type="valueSet"
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
        order: int = 999,
    ) -> None:
        """Add a member to a value set."""
        if not self._part_exists(value_set_id):
            raise ValueError(f"Value set '{value_set_id}' does not exist")

        if self._part_exists(member_id):
            raise ValueError(f"Part '{member_id}' already exists")

        member = ValueSetMemberPart(
            Part_ID=member_id,
            Label=label,
            Description=description,
            Part_type="valueSetMember",
            Member_of_set_part_ID=value_set_id,
            Sort_order=order,
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

    def create_table(self, table_id: str, label: str, description: str) -> None:
        """Create a new table."""
        if self._part_exists(table_id):
            raise ValueError(f"Part '{table_id}' already exists")

        table = TablePart(
            Part_ID=table_id, Label=label, Description=description, Part_type="table"
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
        role: Literal[
            "key", "property", "compositeKeyFirst", "compositeKeySecond"
        ] = "property",
        sql_data_type: str = "nvarchar(255)",
        required: bool = False,
        order: int = 999,
        value_set_id: Optional[str] = None,
        default_value: Optional[str] = None,
    ) -> None:
        """Add a field to a table (or update existing field's table_presence)."""
        if not self._part_exists(table_id):
            raise ValueError(f"Table '{table_id}' does not exist")

        existing_part = self._find_part(field_id)

        if existing_part:
            # Field exists - update its table_presence
            if not hasattr(existing_part, "table_presence"):
                raise ValueError(f"Part '{field_id}' exists but is not a field type")

            # Add table presence
            existing_part.table_presence[table_id] = TablePresence(
                role=role, required=required, order=order
            )
            print(f"Added '{field_id}' to table '{table_id}' with role '{role}'")
        else:
            # Create new field
            presence = {
                table_id: TablePresence(role=role, required=required, order=order)
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

            field_kwargs = {
                "Part_ID": field_id,
                "Label": label,
                "Description": description,
                "Part_type": role if role != "property" else "property",
                "SQL_data_type": sql_data_type,
                "Is_required": required,
                "Default_value": default_value,
                "table_presence": presence,
            }

            if value_set_id:
                field_kwargs["Value_set_part_ID"] = value_set_id

            field = field_class(**field_kwargs)
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
        order: int = 999,
    ) -> None:
        """Add a hierarchical parent key to a table."""
        if not self._part_exists(table_id):
            raise ValueError(f"Table '{table_id}' does not exist")

        if not self._part_exists(ancestor_key_id):
            raise ValueError(f"Ancestor key '{ancestor_key_id}' does not exist")

        if self._part_exists(parent_key_id):
            raise ValueError(f"Part '{parent_key_id}' already exists")

        parent_key = ParentKeyPart(
            Part_ID=parent_key_id,
            Label=label,
            Description=description,
            Part_type="parentKey",
            Ancestor_part_ID=ancestor_key_id,
            SQL_data_type=sql_data_type,
            Is_required=required,
            table_presence={
                table_id: TablePresence(role="property", required=required, order=order)
            },
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
            part.part_id for part in self.dictionary.parts if part.part_type == "table"
        ]

    def list_value_sets(self) -> list[str]:
        """List all value set Part_IDs."""
        return [
            part.part_id
            for part in self.dictionary.parts
            if part.part_type == "valueSet"
        ]

    # ========================================================================
    # Query Operations (replacing old SQL queries)
    # ========================================================================

    def get_value_set_members(self, field_id: str) -> list[dict]:
        """Get all valid values for a field's value set constraint.

        Args:
            field_id: The Part_ID of the field to check

        Returns:
            List of dictionaries with Part_ID, Label, Description for each member
        """
        field = self._find_part(field_id)
        if not field:
            return []

        # Check if field has a value set constraint
        value_set_id = getattr(field, "value_set_part_id", None)
        if not value_set_id:
            return []

        # Find all members of this value set
        members = []
        for part in self.dictionary.parts:
            if (
                hasattr(part, "member_of_set_part_id")
                and part.member_of_set_part_id == value_set_id
            ):
                members.append(
                    {
                        "Part_ID": part.part_id,
                        "Label": part.label,
                        "Description": part.description,
                        "Sort_order": getattr(part, "sort_order", 999),
                    }
                )

        # Sort by sort_order
        members.sort(key=lambda x: x["Sort_order"])
        return members

    def get_table_columns(self, table_id: str) -> list[dict]:
        """Get all columns that appear in a specific table.

        Args:
            table_id: The Part_ID of the table

        Returns:
            List of dictionaries with column metadata
        """
        columns = []
        for part in self.dictionary.parts:
            # Only field parts have table_presence
            if hasattr(part, "table_presence") and part.table_presence:
                if table_id in part.table_presence:
                    presence = part.table_presence[table_id]
                    columns.append(
                        {
                            "Part_ID": part.part_id,
                            "Label": part.label,
                            "SQL_data_type": getattr(part, "sql_data_type", None),
                            "Is_required": presence.required,
                            "Role": presence.role,
                            "Order": presence.order,
                        }
                    )

        # Sort by order
        columns.sort(key=lambda x: x["Order"])
        return columns

    def get_field_tables(self, field_id: str) -> list[dict]:
        """Find all tables where a specific field appears.

        Args:
            field_id: The Part_ID of the field

        Returns:
            List of dictionaries with table and role information
        """
        field = self._find_part(field_id)
        if not field or not hasattr(field, "table_presence"):
            return []

        tables = []
        for table_id, presence in field.table_presence.items():
            tables.append(
                {
                    "Table_ID": table_id,
                    "Role": presence.role,
                    "Required": presence.required,
                    "Order": presence.order,
                }
            )

        return tables

    def get_primary_keys(self) -> list[dict]:
        """Find all primary keys in the database.

        Returns:
            List of dictionaries with primary key information
        """
        primary_keys = []
        for part in self.dictionary.parts:
            if part.part_type == "key":
                # Find which table this key belongs to
                tables = []
                if hasattr(part, "table_presence") and part.table_presence:
                    for table_id, presence in part.table_presence.items():
                        if presence.role == "key":
                            tables.append(table_id)

                primary_keys.append(
                    {
                        "Part_ID": part.part_id,
                        "Label": part.label,
                        "SQL_data_type": getattr(part, "sql_data_type", None),
                        "Primary_in_tables": tables,
                    }
                )

        return primary_keys

    def get_shared_fields(self) -> list[dict]:
        """Find fields that appear in multiple tables.

        Returns:
            List of dictionaries with shared field information
        """
        shared_fields = []
        for part in self.dictionary.parts:
            if (
                hasattr(part, "table_presence")
                and part.table_presence
                and len(part.table_presence) > 1
            ):
                tables = []
                for table_id, presence in part.table_presence.items():
                    tables.append({"Table_ID": table_id, "Role": presence.role})

                shared_fields.append(
                    {
                        "Part_ID": part.part_id,
                        "Label": part.label,
                        "Part_type": part.part_type,
                        "Table_count": len(part.table_presence),
                        "Tables": tables,
                    }
                )

        # Sort by table count (most shared first)
        shared_fields.sort(key=lambda x: x["Table_count"], reverse=True)
        return shared_fields
