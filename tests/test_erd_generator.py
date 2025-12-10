"""
Tests for ERD generator module.
"""

import pytest
from pathlib import Path
import json
import sys

# Add src to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / 'src'))
sys.path.insert(0, str(project_root / 'docs' / 'hooks'))

from erd_generator import (
    generate_erd_data,
    generate_erd_html,
    ERDTable,
    ERDField,
    ERDRelationship
)


@pytest.fixture
def sample_parts_data():
    """Sample parsed parts data for testing."""
    return {
        'tables': {
            'contact': {
                'label': 'Contact',
                'description': 'Stores contact information',
                'fields': [
                    {
                        'part_id': 'Contact_ID',
                        'label': 'Contact ID',
                        'description': 'Primary key',
                        'part_type': 'key',
                        'sql_data_type': 'int',
                        'is_required': True,
                        'default_value': '',
                        'fk_to': '',
                        'value_set': '',
                        'sort_order': 1
                    },
                    {
                        'part_id': 'First_name',
                        'label': 'First Name',
                        'description': 'Contact first name',
                        'part_type': 'property',
                        'sql_data_type': 'nvarchar(255)',
                        'is_required': False,
                        'default_value': '',
                        'fk_to': '',
                        'value_set': '',
                        'sort_order': 2
                    }
                ]
            },
            'metadata': {
                'label': 'Metadata',
                'description': 'Stores metadata',
                'fields': [
                    {
                        'part_id': 'Metadata_ID',
                        'label': 'Metadata ID',
                        'description': 'Primary key',
                        'part_type': 'key',
                        'sql_data_type': 'int',
                        'is_required': True,
                        'default_value': '',
                        'fk_to': '',
                        'value_set': '',
                        'sort_order': 1
                    },
                    {
                        'part_id': 'Contact_ID',
                        'label': 'Contact ID',
                        'description': 'Foreign key to contact',
                        'part_type': 'property',
                        'sql_data_type': 'int',
                        'is_required': False,
                        'default_value': '',
                        'fk_to': 'Contact_ID',
                        'value_set': '',
                        'sort_order': 2
                    }
                ]
            }
        },
        'value_sets': {},
        'metadata': {},
        'id_field_locations': {}
    }


def test_generate_erd_data(sample_parts_data):
    """Test ERD data generation from parts data."""
    erd_data = generate_erd_data(sample_parts_data)
    
    # Check structure
    assert 'tables' in erd_data
    assert 'relationships' in erd_data
    
    # Check tables
    assert len(erd_data['tables']) == 2
    table_ids = [t['id'] for t in erd_data['tables']]
    assert 'contact' in table_ids
    assert 'metadata' in table_ids
    
    # Check relationships
    assert len(erd_data['relationships']) == 1
    rel = erd_data['relationships'][0]
    assert rel['from_table'] == 'metadata'
    assert rel['to_table'] == 'contact'
    assert rel['from_field'] == 'Contact ID'


def test_erd_field_detection(sample_parts_data):
    """Test that primary and foreign keys are correctly identified."""
    erd_data = generate_erd_data(sample_parts_data)
    
    # Find contact table
    contact_table = next(t for t in erd_data['tables'] if t['id'] == 'contact')
    
    # Check PK field
    pk_field = next(f for f in contact_table['fields'] if f['name'] == 'Contact ID')
    assert pk_field['is_pk'] is True
    assert pk_field['is_fk'] is False
    
    # Find metadata table
    metadata_table = next(t for t in erd_data['tables'] if t['id'] == 'metadata')
    
    # Check FK field
    fk_field = next(f for f in metadata_table['fields'] if f['name'] == 'Contact ID')
    assert fk_field['is_fk'] is True
    assert fk_field['fk_target'] == 'contact.Contact_ID'


def test_generate_jointjs_html(sample_parts_data, tmp_path):
    """Test JointJS HTML generation."""
    erd_data = generate_erd_data(sample_parts_data)
    output_path = tmp_path / 'erd_test.html'
    
    generate_erd_html(erd_data, output_path, library='jointjs')
    
    # Check file was created
    assert output_path.exists()
    
    # Check content
    content = output_path.read_text()
    assert 'JointJS' in content or 'jointjs' in content
    assert 'Contact' in content
    assert 'Metadata' in content
    assert 'const erdData' in content
    assert 'dagre' in content  # Ensure layout engine is included


def test_invalid_library(sample_parts_data, tmp_path):
    """Test that invalid library raises error."""
    erd_data = generate_erd_data(sample_parts_data)
    output_path = tmp_path / 'erd_invalid.html'
    
    with pytest.raises(ValueError, match="Unsupported library"):
        generate_erd_html(erd_data, output_path, library='invalid')


def test_empty_tables():
    """Test ERD generation with no tables."""
    empty_data = {
        'tables': {},
        'value_sets': {},
        'metadata': {},
        'id_field_locations': {}
    }
    
    erd_data = generate_erd_data(empty_data)
    
    assert erd_data['tables'] == []
    assert erd_data['relationships'] == []


def test_self_referential_relationship():
    """Test handling of self-referential foreign keys (parent keys)."""
    data = {
        'tables': {
            'category': {
                'label': 'Category',
                'description': 'Hierarchical categories',
                'fields': [
                    {
                        'part_id': 'Category_ID',
                        'label': 'Category ID',
                        'description': 'Primary key',
                        'part_type': 'key',
                        'sql_data_type': 'int',
                        'is_required': True,
                        'default_value': '',
                        'fk_to': '',
                        'value_set': '',
                        'sort_order': 1
                    },
                    {
                        'part_id': 'Parent_Category_ID',
                        'label': 'Parent Category ID',
                        'description': 'Parent category',
                        'part_type': 'property',
                        'sql_data_type': 'int',
                        'is_required': False,
                        'default_value': '',
                        'fk_to': 'Category_ID',
                        'value_set': '',
                        'sort_order': 2
                    }
                ]
            }
        },
        'value_sets': {},
        'metadata': {},
        'id_field_locations': {}
    }
    
    erd_data = generate_erd_data(data)
    
    # Should have one self-referential relationship
    assert len(erd_data['relationships']) == 1
    rel = erd_data['relationships'][0]
    assert rel['from_table'] == 'category'
    assert rel['to_table'] == 'category'
