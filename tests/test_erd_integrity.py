"""
Tests for ERD (Entity-Relationship Diagram) integrity.

These tests verify that:
1. All FK relationships are captured in the ERD
2. All relationships point to valid tables
3. The generated HTML contains all expected elements
"""

import sys
from pathlib import Path
import pytest
import json

# Add project paths
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / 'src'))
sys.path.insert(0, str(project_root / 'docs/hooks'))

from erd_generator import generate_erd_data, generate_erd_html
import generate_docs


@pytest.fixture
def parts_data():
    """Load and parse the dictionary.json file."""
    json_path = project_root / 'src/dictionary.json'
    return generate_docs.parse_parts_json(json_path)


@pytest.fixture
def erd_data(parts_data):
    """Generate ERD data from parts data."""
    return generate_erd_data(parts_data)


def test_all_fk_relationships_captured(parts_data, erd_data):
    """Test that all FK fields result in relationships in the ERD."""
    # Count total FK fields in dictionary
    total_fks = 0
    fk_details = []

    for table_id, table_info in parts_data['tables'].items():
        for field in table_info['fields']:
            if field.get('fk_to'):
                total_fks += 1
                fk_details.append({
                    'table': table_id,
                    'field': field['label'],
                    'fk_to': field['fk_to']
                })

    # Count relationships in ERD
    num_relationships = len(erd_data['relationships'])

    # Assert they match
    assert num_relationships == total_fks, (
        f"Expected {total_fks} relationships but got {num_relationships}. "
        f"FK fields: {fk_details}"
    )


def test_all_relationships_have_valid_tables(parts_data, erd_data):
    """Test that all relationships point to existing tables."""
    table_ids = set(parts_data['tables'].keys())

    for rel in erd_data['relationships']:
        assert rel['from_table'] in table_ids, (
            f"Relationship from_table '{rel['from_table']}' does not exist"
        )
        assert rel['to_table'] in table_ids, (
            f"Relationship to_table '{rel['to_table']}' does not exist"
        )


def test_all_tables_included_in_erd(parts_data, erd_data):
    """Test that all tables from dictionary are included in ERD."""
    dict_tables = set(parts_data['tables'].keys())
    erd_tables = {table['id'] for table in erd_data['tables']}

    assert dict_tables == erd_tables, (
        f"Table mismatch. Missing from ERD: {dict_tables - erd_tables}, "
        f"Extra in ERD: {erd_tables - dict_tables}"
    )


def test_relationship_field_names_exist(parts_data, erd_data):
    """Test that relationship field names exist in their respective tables."""
    for rel in erd_data['relationships']:
        # Check from_field exists in from_table
        from_table = parts_data['tables'][rel['from_table']]
        from_field_names = [f['label'] for f in from_table['fields']]
        assert rel['from_field'] in from_field_names, (
            f"Field '{rel['from_field']}' not found in table '{rel['from_table']}'"
        )

        # Check to_field exists in to_table
        to_table = parts_data['tables'][rel['to_table']]
        to_field_names = [f['label'] for f in to_table['fields']]
        assert rel['to_field'] in to_field_names, (
            f"Field '{rel['to_field']}' not found in table '{rel['to_table']}'"
        )


def test_junction_tables_not_preferred_as_targets(erd_data):
    """
    Test that relationships prefer non-junction tables as targets when possible.

    Junction tables (with '_has_' in name) should generally not be the target
    of FK relationships unless they are the only table with that PK.
    """
    # Count how many relationships point to junction tables
    junction_target_count = sum(
        1 for rel in erd_data['relationships']
        if '_has_' in rel['to_table']
    )

    # We expect very few or no relationships to point to junction tables
    # This is informational - junction tables are typically intermediate tables
    total_relationships = len(erd_data['relationships'])

    # Allow up to 10% of relationships to point to junction tables
    # (in case there are legitimate cases)
    assert junction_target_count / total_relationships < 0.1, (
        f"Too many relationships ({junction_target_count}/{total_relationships}) "
        f"point to junction tables. This may indicate incorrect FK resolution."
    )


def test_html_contains_clickable_arrows(erd_data, tmp_path):
    """Test that generated HTML contains link click handlers for clickable arrows."""
    output_path = tmp_path / 'test_erd.html'
    generate_erd_html(erd_data, output_path, library='jointjs')

    html_content = output_path.read_text()

    # Check for link click handler
    assert 'link:pointerdown' in html_content, (
        "Generated HTML missing link click handler (link:pointerdown)"
    )

    # Check for relationship data storage
    assert 'relationshipData' in html_content, (
        "Generated HTML missing relationshipData attribute for storing FK info"
    )


def test_html_contains_drag_functionality(erd_data, tmp_path):
    """Test that generated HTML contains table dragging functionality."""
    output_path = tmp_path / 'test_erd.html'
    generate_erd_html(erd_data, output_path, library='jointjs')

    html_content = output_path.read_text()

    # Check for drag handler
    assert 'startDrag' in html_content, (
        "Generated HTML missing startDrag function for table dragging"
    )

    # Check that drag is attached to header
    assert 'onmousedown' in html_content, (
        "Generated HTML missing onmousedown event for initiating drag"
    )


def test_html_has_all_tables(erd_data, tmp_path):
    """Test that generated HTML will render all tables."""
    output_path = tmp_path / 'test_erd.html'
    generate_erd_html(erd_data, output_path, library='jointjs')

    html_content = output_path.read_text()

    # The ERD data should be embedded as JSON in the HTML
    # Check that it contains table data
    assert 'erdData.tables' in html_content, (
        "Generated HTML missing erdData.tables reference"
    )


def test_relationship_count_matches_fk_count(parts_data, erd_data):
    """
    Test that the number of relationships equals the number of FK fields.
    This is the main integrity check - every FK should have exactly one relationship.
    """
    # Count FK fields
    fk_count = sum(
        1 for table in parts_data['tables'].values()
        for field in table['fields']
        if field.get('fk_to')
    )

    # Count relationships
    rel_count = len(erd_data['relationships'])

    assert rel_count == fk_count, (
        f"Relationship count ({rel_count}) does not match FK count ({fk_count}). "
        f"Every FK field should generate exactly one relationship."
    )


def test_no_duplicate_relationships(erd_data):
    """Test that there are no duplicate relationships in the ERD."""
    # Create a set of relationship signatures (from_table, to_table, from_field)
    relationship_signatures = [
        (rel['from_table'], rel['to_table'], rel['from_field'])
        for rel in erd_data['relationships']
    ]

    # Check for duplicates
    unique_signatures = set(relationship_signatures)

    assert len(relationship_signatures) == len(unique_signatures), (
        f"Found duplicate relationships. Total: {len(relationship_signatures)}, "
        f"Unique: {len(unique_signatures)}"
    )


def test_relationships_have_required_fields(erd_data):
    """Test that all relationships have the required fields."""
    required_fields = ['from_table', 'to_table', 'from_field', 'to_field', 'relationship_type']

    for i, rel in enumerate(erd_data['relationships']):
        for field in required_fields:
            assert field in rel, (
                f"Relationship {i} missing required field '{field}': {rel}"
            )
            assert rel[field], (
                f"Relationship {i} has empty value for required field '{field}': {rel}"
            )


if __name__ == '__main__':
    # Run tests with pytest
    pytest.main([__file__, '-v'])
