"""Tests for PRD-3 S4 — save/reload named mapping config.

Verifies:
- Config dict serializes/deserializes correctly (pure logic, no Streamlit).
- Round-trip save → load produces identical role_map.
- _build_config produces the expected PRD-5-compatible shape.
- _list_configs returns saved files.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from unittest import mock

import pytest

# ---------------------------------------------------------------------------
# Module-level load (once per process) — avoids the "numpy loaded twice" error
# when multiple tests each call _load_mapper_module() independently.
# ---------------------------------------------------------------------------

_MAPPER_PATH = Path(__file__).resolve().parent.parent.parent / "app" / "pages" / "mapper.py"

_fake_st = mock.MagicMock()
_fake_st.file_uploader.return_value = None

with mock.patch.dict(sys.modules, {"streamlit": _fake_st}):
    _spec = importlib.util.spec_from_file_location("mapper_s4_cfg", str(_MAPPER_PATH))
    assert _spec is not None
    _mapper_mod = importlib.util.module_from_spec(_spec)
    assert _spec.loader is not None
    _spec.loader.exec_module(_mapper_mod)  # type: ignore[union-attr]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_build_config_shape():
    """_build_config returns a dict with the PRD-5-compatible keys."""
    role_map = {"sample_datetime": "sample_datetime", "COD (mg/L)": "parameter_value"}
    cfg = _mapper_mod._build_config(
        name="Test Config",
        header_row=0,
        data_start_row=1,
        role_map=role_map,
        sheet_name="Sheet1",
    )
    assert cfg["name"] == "Test Config"
    assert cfg["version"] == 1
    assert cfg["header_row"] == 0
    assert cfg["data_start_row"] == 1
    assert cfg["role_map"] == role_map
    assert cfg["sheet_name"] == "Sheet1"


def test_build_config_no_sheet():
    """_build_config omits sheet_name when None (CSV case)."""
    cfg = _mapper_mod._build_config(
        name="CSV Config",
        header_row=0,
        data_start_row=1,
        role_map={"dt": "sample_datetime"},
        sheet_name=None,
    )
    assert "sheet_name" not in cfg


def test_config_json_roundtrip():
    """Config dict survives JSON serialization/deserialization without loss."""
    role_map = {
        "sample_datetime": "sample_datetime",
        "Location": "sampling_location",
        "Replicate": "replicate",
        "COD (mg/L)": "parameter_value",
        "TSS (mg/L)": "parameter_value",
    }
    cfg = _mapper_mod._build_config(
        name="Lab Sheet v1",
        header_row=0,
        data_start_row=1,
        role_map=role_map,
        sheet_name="Data",
    )

    serialized = json.dumps(cfg)
    deserialized = json.loads(serialized)

    assert deserialized["name"] == cfg["name"]
    assert deserialized["version"] == cfg["version"]
    assert deserialized["header_row"] == cfg["header_row"]
    assert deserialized["data_start_row"] == cfg["data_start_row"]
    assert deserialized["role_map"] == cfg["role_map"]
    assert deserialized["sheet_name"] == cfg["sheet_name"]


def test_save_and_load_roundtrip(tmp_path, monkeypatch):
    """Round-trip save → load produces identical role_map."""
    monkeypatch.setattr(_mapper_mod, "_config_dir", lambda: tmp_path)

    role_map = {
        "sample_datetime": "sample_datetime",
        "Loc": "sampling_location",
        "COD (mg/L)": "parameter_value",
    }
    cfg = _mapper_mod._build_config(
        name="Roundtrip Test",
        header_row=2,
        data_start_row=3,
        role_map=role_map,
    )

    saved_path = _mapper_mod._save_config(cfg)
    assert saved_path.exists()

    loaded = _mapper_mod._load_config(saved_path)

    assert loaded["role_map"] == role_map
    assert loaded["header_row"] == 2
    assert loaded["data_start_row"] == 3
    assert loaded["name"] == "Roundtrip Test"
    assert loaded["version"] == 1


def test_list_configs(tmp_path, monkeypatch):
    """_list_configs returns all saved JSON files."""
    monkeypatch.setattr(_mapper_mod, "_config_dir", lambda: tmp_path)

    # Initially empty
    assert _mapper_mod._list_configs() == []

    # Save two configs
    cfg_a = _mapper_mod._build_config("Alpha", 0, 1, {"dt": "sample_datetime"})
    cfg_b = _mapper_mod._build_config("Beta", 0, 1, {"loc": "sampling_location"})
    _mapper_mod._save_config(cfg_a)
    _mapper_mod._save_config(cfg_b)

    configs = _mapper_mod._list_configs()
    assert len(configs) == 2
    stems = {p.stem for p in configs}
    assert "Alpha" in stems
    assert "Beta" in stems


def test_save_config_sanitizes_name(tmp_path, monkeypatch):
    """_save_config creates a valid filename even for names with special chars."""
    monkeypatch.setattr(_mapper_mod, "_config_dir", lambda: tmp_path)

    cfg = _mapper_mod._build_config(
        name="My Config: 2024/01 (v2)",
        header_row=0,
        data_start_row=1,
        role_map={},
    )
    saved_path = _mapper_mod._save_config(cfg)
    assert saved_path.exists()
    # Name should be a valid filename (no slashes or colons)
    assert "/" not in saved_path.name
    assert ":" not in saved_path.name
