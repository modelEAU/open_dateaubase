"""JSON-based test fixtures for open_dateaubase testing.

This module provides sample dictionary data in the current JSON format
used by Pydantic models, replacing the old CSV-based fixtures.
"""

from typing import Dict, Any


def sample_dictionary_data() -> Dict[str, Any]:
    """Sample dictionary with basic table, fields, and value set."""
    return {
        "parts": [
            # Table definition
            {
                "Part_ID": "test_table",
                "Label": "Test Table",
                "Description": "A test table for demonstration",
                "Part_type": "table",
            },
            # Primary key field
            {
                "Part_ID": "TestTable_ID",
                "Label": "Test Table ID",
                "Description": "Primary identifier for TestTable",
                "Part_type": "key",
                "SQL_data_type": "int",
                "Is_required": True,
                "table_presence": {
                    "test_table": {"role": "key", "required": True, "order": 1}
                },
            },
            # Regular field with value set constraint
            {
                "Part_ID": "Status",
                "Label": "Status",
                "Description": "Current status of record",
                "Part_type": "property",
                "SQL_data_type": "nvarchar(50)",
                "Is_required": False,
                "Value_set_part_ID": "StatusSet",
                "table_presence": {
                    "test_table": {"role": "property", "required": False, "order": 2}
                },
            },
            # Regular field without constraints
            {
                "Part_ID": "Description",
                "Label": "Description",
                "Description": "Detailed description",
                "Part_type": "property",
                "SQL_data_type": "nvarchar(255)",
                "Is_required": True,
                "table_presence": {
                    "test_table": {"role": "property", "required": True, "order": 3}
                },
            },
            # Parent key (hierarchical self-reference)
            {
                "Part_ID": "Parent_ID",
                "Label": "Parent ID",
                "Description": "Hierarchical reference to parent record",
                "Part_type": "parentKey",
                "Ancestor_part_ID": "TestTable_ID",
                "SQL_data_type": "int",
                "Is_required": False,
                "table_presence": {
                    "test_table": {"role": "property", "required": False, "order": 4}
                },
            },
            # Value set definition
            {
                "Part_ID": "StatusSet",
                "Label": "Status Set",
                "Description": "Valid status values for records",
                "Part_type": "valueSet",
            },
            # Value set members
            {
                "Part_ID": "active",
                "Label": "Active",
                "Description": "Record is currently active",
                "Part_type": "valueSetMember",
                "Member_of_set_part_ID": "StatusSet",
                "Sort_order": 1,
            },
            {
                "Part_ID": "inactive",
                "Label": "Inactive",
                "Description": "Record is currently inactive",
                "Part_type": "valueSetMember",
                "Member_of_set_part_ID": "StatusSet",
                "Sort_order": 2,
            },
            {
                "Part_ID": "pending",
                "Label": "Pending",
                "Description": "Record is pending review",
                "Part_type": "valueSetMember",
                "Member_of_set_part_ID": "StatusSet",
                "Sort_order": 3,
            },
        ]
    }


def complex_dictionary_data() -> Dict[str, Any]:
    """Complex dictionary with multiple tables, relationships, and edge cases."""
    return {
        "parts": [
            # First table
            {
                "Part_ID": "contact",
                "Label": "Contact",
                "Description": "Contact information table",
                "Part_type": "table",
            },
            {
                "Part_ID": "Contact_ID",
                "Label": "Contact ID",
                "Description": "Primary key for contact",
                "Part_type": "key",
                "SQL_data_type": "int",
                "Is_required": True,
                "table_presence": {
                    "contact": {"role": "key", "required": True, "order": 1}
                },
            },
            {
                "Part_ID": "contact_Name",
                "Label": "Name",
                "Description": "Full name of contact",
                "Part_type": "property",
                "SQL_data_type": "nvarchar(255)",
                "Is_required": True,
                "table_presence": {
                    "contact": {"role": "property", "required": True, "order": 2}
                },
            },
            # Second table with FK to first
            {
                "Part_ID": "project",
                "Label": "Project",
                "Description": "Project information",
                "Part_type": "table",
            },
            {
                "Part_ID": "Project_ID",
                "Label": "Project ID",
                "Description": "Primary key for project",
                "Part_type": "key",
                "SQL_data_type": "int",
                "Is_required": True,
                "table_presence": {
                    "project": {"role": "key", "required": True, "order": 1}
                },
            },
            {
                "Part_ID": "Project_Contact_ID",
                "Label": "Contact ID",
                "Description": "Foreign key to contact",
                "Part_type": "property",
                "SQL_data_type": "int",
                "Is_required": True,
                "table_presence": {
                    "project": {"role": "property", "required": True, "order": 2}
                },
            },
            # Junction table for many-to-many
            {
                "Part_ID": "project_has_contact",
                "Label": "Project Has Contact",
                "Description": "Junction table for project-contact relationships",
                "Part_type": "table",
            },
            {
                "Part_ID": "Junction_Project_ID",
                "Label": "Project ID",
                "Description": "Foreign key to project in junction",
                "Part_type": "compositeKeyFirst",
                "SQL_data_type": "int",
                "Is_required": True,
                "table_presence": {
                    "project_has_contact": {
                        "role": "compositeKeyFirst",
                        "required": True,
                        "order": 1,
                    }
                },
            },
            {
                "Part_ID": "Junction_Contact_ID",
                "Label": "Contact ID",
                "Description": "Foreign key to contact in junction",
                "Part_type": "compositeKeySecond",
                "SQL_data_type": "int",
                "Is_required": True,
                "table_presence": {
                    "project_has_contact": {
                        "role": "compositeKeySecond",
                        "required": True,
                        "order": 2,
                    }
                }
            },
        ]
    }


def edge_case_dictionary_data() -> Dict[str, Any]:
    """Dictionary with edge cases for testing error handling."""
    return {
        "parts": [
            # Table with special characters in name
            {
                "Part_ID": "special_table",
                "Label": "Special-Table!",
                "Description": "Table with special characters: @#$%",
                "Part_type": "table",
            },
            # Field with very long name
            {
                "Part_ID": "VeryLongFieldNameThatExceedsNormalDatabaseLimitsAndMightCauseIssues",
                "Label": "Very Long Field Name That Exceeds Normal Database Limits",
                "Description": "A field with an extremely long name for testing edge cases",
                "Part_type": "property",
                "SQL_data_type": "nvarchar(max)",
                "Is_required": False,
                "table_presence": {
                    "special_table": {"role": "property", "required": False, "order": 1}
                },
            },
            # Field with default value
            {
                "Part_ID": "Created_Date",
                "Label": "Created Date",
                "Description": "Date when record was created",
                "Part_type": "property",
                "SQL_data_type": "datetime",
                "Is_required": True,
                "Default_value": "GETDATE()",
                "table_presence": {
                    "special_table": {"role": "property", "required": True, "order": 2}
                },
            },
            # Boolean field
            {
                "Part_ID": "Is_Active",
                "Label": "Is Active",
                "Description": "Whether record is active",
                "Part_type": "property",
                "SQL_data_type": "bit",
                "Is_required": False,
                "Default_value": "True",
                "table_presence": {
                    "special_table": {"role": "property", "required": False, "order": 3}
                },
            },
        ]
    }


def invalid_dictionary_data() -> Dict[str, Any]:
    """Invalid dictionary data for testing validation errors."""
    return {
        "parts": [
            # Missing required fields
            {
                "Part_ID": "incomplete_table",
                # Missing Label and Description
                "Part_type": "table",
            },
            # Invalid part type
            {
                "Part_ID": "invalid_part",
                "Label": "Invalid Part",
                "Description": "This has an invalid part type",
                "Part_type": "invalid_type",
            },
            # Key without _ID suffix
            {
                "Part_ID": "InvalidKey",
                "Label": "Invalid Key",
                "Description": "This key doesn't end with _ID",
                "Part_type": "key",
                "SQL_data_type": "int",
                "Is_required": True,
                "table_presence": {
                    "incomplete_table": {"role": "key", "required": True, "order": 1}
                },
            },
            # Value set without proper suffix
            {
                "Part_ID": "InvalidValueSet",
                "Label": "Invalid Value Set",
                "Description": "This value set doesn't end with _set or Set",
                "Part_type": "valueSet",
            },
        ]
    }
