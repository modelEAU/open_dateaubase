"""Tests for PRD-3 S1 — mapper engine shell.

Goals:
- Fail immediately if app/pages/mapper.py is missing.
- Verify the LAB_ROLES constant is defined and contains required role names.
- Verify _read_dataframe helper parses a minimal CSV correctly.

We intentionally avoid AppTest here because the page calls mapper_page() at
module level (Streamlit pattern) and AppTest would require a running Streamlit
context; the module-level side-effects make import-time execution unreliable
without a harness. The import + constant tests are sufficient for S1.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
import io

import pandas as pd
import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_MAPPER_PATH = Path(__file__).resolve().parent.parent.parent / "app" / "pages" / "mapper.py"


def _load_mapper_module():
    """Load mapper.py without executing the top-level mapper_page() call.

    We monkey-patch streamlit so the module-level `mapper_page()` call is a
    no-op during import.
    """
    import unittest.mock as mock

    # Provide a fake streamlit module so the import doesn't fail or open a UI.
    fake_st = mock.MagicMock()
    # make file_uploader return None (no upload) so the page exits early
    fake_st.file_uploader.return_value = None

    with mock.patch.dict(sys.modules, {"streamlit": fake_st}):
        spec = importlib.util.spec_from_file_location("mapper_s1", str(_MAPPER_PATH))
        assert spec is not None
        mod = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(mod)  # type: ignore[union-attr]

    return mod


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_mapper_file_exists():
    """Fails if app/pages/mapper.py is missing."""
    assert _MAPPER_PATH.exists(), f"mapper.py not found at {_MAPPER_PATH}"


def test_lab_roles_defined():
    """LAB_ROLES constant must exist and contain required role names."""
    mod = _load_mapper_module()
    roles = mod.LAB_ROLES
    assert isinstance(roles, list), "LAB_ROLES must be a list"
    assert "(ignore)" in roles
    assert "sample_datetime" in roles
    assert "sampling_location" in roles
    assert "replicate" in roles
    assert "parameter_value" in roles


def test_read_dataframe_csv():
    """_read_dataframe parses a minimal CSV correctly."""
    mod = _load_mapper_module()
    csv_bytes = b"col_a,col_b\n1,x\n2,y\n"
    df = mod._read_dataframe(csv_bytes, "test.csv", header_row=0)
    assert list(df.columns) == ["col_a", "col_b"]
    assert len(df) == 2


@pytest.mark.skipif(
    not importlib.util.find_spec("openpyxl"),
    reason="openpyxl not installed — skip XLSX parsing test",
)
def test_read_dataframe_xlsx():
    """_read_dataframe parses a minimal XLSX correctly (requires openpyxl)."""
    mod = _load_mapper_module()

    # Build a minimal xlsx in memory
    buf = io.BytesIO()
    pd.DataFrame({"alpha": [1, 2], "beta": ["x", "y"]}).to_excel(buf, index=False)
    xlsx_bytes = buf.getvalue()

    df = mod._read_dataframe(xlsx_bytes, "test.xlsx", sheet_name=0, header_row=0)
    assert "alpha" in df.columns
    assert "beta" in df.columns
    assert len(df) == 2
