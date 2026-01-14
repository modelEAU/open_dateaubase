"""Shared pytest configuration and fixtures for open_dateaubase tests."""

import pytest
import json
import sys
from pathlib import Path

# Add project paths to sys.path so imports work consistently
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))
sys.path.insert(0, str(project_root / "scripts"))
sys.path.insert(0, str(project_root / "tests"))


# Import fixtures
from fixtures.sample_dictionary import (
    sample_dictionary_data,
    complex_dictionary_data,
    edge_case_dictionary_data,
)


@pytest.fixture
def sample_json_dict():
    """Return sample dictionary data as Python dict."""
    return sample_dictionary_data()


@pytest.fixture
def complex_json_dict():
    """Return complex dictionary data as Python dict."""
    return complex_dictionary_data()


@pytest.fixture
def edge_case_json_dict():
    """Return edge case dictionary data as Python dict."""
    return edge_case_dictionary_data()


@pytest.fixture
def sample_json_file(tmp_path):
    """Create temporary JSON file with sample dictionary data."""
    json_file = tmp_path / "sample_dictionary.json"
    json_file.write_text(json.dumps(sample_dictionary_data(), indent=2))
    return json_file


@pytest.fixture
def complex_json_file(tmp_path):
    """Create temporary JSON file with complex dictionary data."""
    json_file = tmp_path / "complex_dictionary.json"
    json_file.write_text(json.dumps(complex_dictionary_data(), indent=2))
    return json_file


@pytest.fixture
def edge_case_json_file(tmp_path):
    """Create temporary JSON file with edge case dictionary data."""
    json_file = tmp_path / "edge_case_dictionary.json"
    json_file.write_text(json.dumps(edge_case_dictionary_data(), indent=2))
    return json_file


@pytest.fixture
def output_dirs(tmp_path):
    """Create standard output directory structure for tests."""
    dirs = {
        "docs": tmp_path / "docs" / "reference",
        "sql": tmp_path / "sql_generation_scripts",
        "assets": tmp_path / "docs" / "assets",
        "root": tmp_path,
    }
    
    for dir_path in dirs.values():
        if isinstance(dir_path, Path):
            dir_path.mkdir(parents=True, exist_ok=True)
    
    return dirs


# Configure pytest
def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "integration: mark test as integration test (slower, uses multiple modules)"
    )
    config.addinivalue_line(
        "markers", "unit: mark test as unit test (fast, isolated)"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )
