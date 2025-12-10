"""
Pydantic models for the open_dateaubase dictionary.

This module defines the type-safe schema for the dictionary using discriminated
unions to enforce Part_type-specific validation rules.
"""

from typing import Literal, Union, Dict, Optional, List, Any, Annotated
from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict


# ============================================================================
# Table Presence Metadata
# ============================================================================


class TablePresence(BaseModel):
    """Metadata about how a field appears in a specific table."""

    model_config = ConfigDict(frozen=True)  # Immutable for safety

    role: Literal["key", "property", "compositeKeyFirst", "compositeKeySecond"]
    required: bool = False
    order: int = Field(ge=1, description="Display order in table (1-indexed)")

    # Foreign key relationship metadata
    relationship_type: Optional[
        Literal["one-to-one", "one-to-many", "many-to-many"]
    ] = Field(
        None,
        description="Type of relationship this FK represents. Set when this field is a foreign key.",
    )

    @model_validator(mode="after")
    def validate_fk_consistency(self):
        """Ensure FK metadata is consistent."""
        has_relationship = self.relationship_type is not None

        # Validate relationship types match expected roles
        if has_relationship:
            # one-to-one: FK should typically be a key (though property is also valid)
            # one-to-many: FK should be a property (regular column in child table)
            # many-to-many: FK should be part of composite key in junction table

            if self.relationship_type == "one-to-one" and self.role not in [
                "key",
                "property",
            ]:
                raise ValueError(
                    f"one-to-one relationships require role='key' or 'property', got '{self.role}'"
                )

            if self.relationship_type == "one-to-many" and self.role not in [
                "property",
                "compositeKeyFirst",
                "compositeKeySecond",
            ]:
                raise ValueError(
                    f"one-to-many relationships typically require role='property', got '{self.role}'"
                )

            if self.relationship_type == "many-to-many" and self.role not in [
                "compositeKeyFirst",
                "compositeKeySecond",
            ]:
                raise ValueError(
                    f"many-to-many relationships require composite key roles, got '{self.role}'"
                )

        return self


# ============================================================================
# Base Part Model
# ============================================================================


class PartBase(BaseModel):
    """Base model for all dictionary parts."""

    model_config = ConfigDict(
        populate_by_name=True
    )  # Allow both snake_case and PascalCase

    part_id: str = Field(..., alias="Part_ID", min_length=1)
    label: str = Field(..., alias="Label", min_length=1)
    description: str = Field(..., alias="Description", min_length=1)
    sort_order: Optional[int] = Field(None, alias="Sort_order", ge=1)


# ============================================================================
# Table Part
# ============================================================================


class TablePart(PartBase):
    """Represents a database table definition."""

    part_type: Literal["table"] = Field(alias="Part_type")

    @field_validator("part_id")
    @classmethod
    def validate_table_name(cls, v: str) -> str:
        """Table names should be lowercase with underscores."""
        if " " in v:
            raise ValueError(f"Table name '{v}' should not contain spaces")
        return v


# ============================================================================
# Field Parts (key, property, compositeKey*)
# ============================================================================


class FieldPartBase(PartBase):
    """Base for parts that represent table columns."""

    sql_data_type: Optional[str] = Field(None, alias="SQL_data_type")
    is_required: bool = Field(default=False, alias="Is_required")
    default_value: Optional[str] = Field(None, alias="Default_value")
    value_set_part_id: Optional[str] = Field(None, alias="Value_set_part_ID")
    table_presence: Dict[str, TablePresence] = Field(
        default_factory=dict, description="Maps table_name -> TablePresence metadata"
    )

    @model_validator(mode="after")
    def validate_table_presence_not_empty(self):
        """Field parts must appear in at least one table."""
        if not self.table_presence:
            raise ValueError(
                f"Field '{self.part_id}' must appear in at least one table"
            )
        return self


class KeyPart(FieldPartBase):
    """Primary key field."""

    part_type: Literal["key"] = Field(alias="Part_type")

    @field_validator("part_id")
    @classmethod
    def validate_key_naming(cls, v: str) -> str:
        """Primary keys should end with '_ID'."""
        if not v.endswith("_ID"):
            raise ValueError(f"Key '{v}' should end with '_ID'")
        return v

    @model_validator(mode="after")
    def validate_key_in_tables(self):
        """A key must be 'key' in at least one table."""
        has_key_role = any(
            presence.role == "key" for presence in self.table_presence.values()
        )
        if not has_key_role:
            raise ValueError(
                f"Key '{self.part_id}' must have role='key' in at least one table"
            )
        return self


class PropertyPart(FieldPartBase):
    """Regular column/field."""

    part_type: Literal["property"] = Field(alias="Part_type")


class CompositeKeyFirstPart(FieldPartBase):
    """First component of composite primary key."""

    part_type: Literal["compositeKeyFirst"] = Field(alias="Part_type")

    @field_validator("part_id")
    @classmethod
    def validate_composite_key_naming(cls, v: str) -> str:
        """Composite keys should end with '_ID'."""
        if not v.endswith("_ID"):
            raise ValueError(f"Composite key '{v}' should end with '_ID'")
        return v


class CompositeKeySecondPart(FieldPartBase):
    """Second component of composite primary key."""

    part_type: Literal["compositeKeySecond"] = Field(alias="Part_type")

    @field_validator("part_id")
    @classmethod
    def validate_composite_key_naming(cls, v: str) -> str:
        """Composite keys should end with '_ID'."""
        if not v.endswith("_ID"):
            raise ValueError(f"Composite key '{v}' should end with '_ID'")
        return v


class ParentKeyPart(FieldPartBase):
    """Hierarchical self-reference within same table."""

    part_type: Literal["parentKey"] = Field(alias="Part_type")
    ancestor_part_id: str = Field(..., alias="Ancestor_part_ID", min_length=1)

    @field_validator("ancestor_part_id")
    @classmethod
    def validate_ancestor_is_key(cls, v: str) -> str:
        """Ancestor should be a key field (end with _ID)."""
        if not v.endswith("_ID"):
            raise ValueError(f"Ancestor '{v}' should be a key field ending with '_ID'")
        return v


# ============================================================================
# Value Set Parts
# ============================================================================


class ValueSetPart(PartBase):
    """Enumeration/controlled vocabulary definition."""

    part_type: Literal["valueSet"] = Field(alias="Part_type")

    @field_validator("part_id")
    @classmethod
    def validate_value_set_naming(cls, v: str) -> str:
        """Value sets should end with '_set' by convention."""
        if not v.endswith("_set") and not v.endswith("Set"):
            raise ValueError(f"Value set '{v}' should end with '_set' or 'Set'")
        return v


class ValueSetMemberPart(PartBase):
    """Individual value within a value set."""

    part_type: Literal["valueSetMember"] = Field(alias="Part_type")
    member_of_set_part_id: str = Field(..., alias="Member_of_set_part_ID", min_length=1)

    @field_validator("member_of_set_part_id")
    @classmethod
    def validate_member_of_set(cls, v: str) -> str:
        """Should reference a value set."""
        if not v.endswith("_set") and not v.endswith("Set"):
            raise ValueError(
                f"Member should belong to a value set ending with '_set' or 'Set', got '{v}'"
            )
        return v


# ============================================================================
# Discriminated Union
# ============================================================================

Part = Annotated[
    Union[
        TablePart,
        KeyPart,
        PropertyPart,
        CompositeKeyFirstPart,
        CompositeKeySecondPart,
        ParentKeyPart,
        ValueSetPart,
        ValueSetMemberPart,
    ],
    Field(discriminator="part_type"),
]


# ============================================================================
# Dictionary Root
# ============================================================================


class Dictionary(BaseModel):
    """Root dictionary model."""

    parts: List[Part]

    @field_validator("parts")
    @classmethod
    def validate_unique_part_ids(cls, v: List[Part]) -> List[Part]:
        """Ensure all Part_IDs are unique."""
        part_ids = [part.part_id for part in v]
        duplicates = [pid for pid in set(part_ids) if part_ids.count(pid) > 1]
        if duplicates:
            raise ValueError(f"Duplicate Part_IDs found: {duplicates}")
        return v

    @model_validator(mode="after")
    def validate_cross_references(self):
        """Validate that all cross-references point to existing parts."""
        part_ids = {part.part_id for part in self.parts}

        # Validate value_set_part_id references
        for part in self.parts:
            if isinstance(part, FieldPartBase) and part.value_set_part_id:
                if part.value_set_part_id not in part_ids:
                    raise ValueError(
                        f"Field '{part.part_id}' references non-existent "
                        f"value set '{part.value_set_part_id}'"
                    )

        # Validate member_of_set_part_id references
        for part in self.parts:
            if isinstance(part, ValueSetMemberPart):
                if part.member_of_set_part_id not in part_ids:
                    raise ValueError(
                        f"Value set member '{part.part_id}' references "
                        f"non-existent set '{part.member_of_set_part_id}'"
                    )

        # Validate ancestor_part_id references
        for part in self.parts:
            if isinstance(part, ParentKeyPart):
                if part.ancestor_part_id not in part_ids:
                    raise ValueError(
                        f"Parent key '{part.part_id}' references non-existent "
                        f"ancestor '{part.ancestor_part_id}'"
                    )

        # Validate table_presence references
        table_names = {
            part.part_id for part in self.parts if isinstance(part, TablePart)
        }
        for part in self.parts:
            if isinstance(part, FieldPartBase):
                for table_name in part.table_presence.keys():
                    if table_name not in table_names:
                        raise ValueError(
                            f"Field '{part.part_id}' references non-existent "
                            f"table '{table_name}' in table_presence"
                        )

        # Validate foreign key relationships by inferring targets from field names
        for part in self.parts:
            if isinstance(part, FieldPartBase):
                for table_name, presence in part.table_presence.items():
                    if presence.relationship_type:
                        # Infer FK target from field name (field name ending in _ID references same-named primary key)
                        if part.part_id.endswith("_ID"):
                            # Validate that the inferred target exists and is a key field
                            target_part = next(
                                (p for p in self.parts if p.part_id == part.part_id),
                                None,
                            )
                            if target_part and not isinstance(
                                target_part,
                                (
                                    KeyPart,
                                    CompositeKeyFirstPart,
                                    CompositeKeySecondPart,
                                ),
                            ):
                                raise ValueError(
                                    f"Field '{part.part_id}' appears to be a foreign key but is not defined as a key field"
                                )

        return self
