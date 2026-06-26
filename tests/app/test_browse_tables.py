"""Smoke test: the read-only Browse Tables page renders with mocked data."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

PAGE = str(Path(__file__).resolve().parents[2] / "app" / "pages" / "browse_tables.py")

_TABLES = [{"name": "Equipment"}, {"name": "Site"}]
_DATA = {
    "table": "Equipment",
    "columns": ["equipment_id", "identifier"],
    "rows": [{"equipment_id": 1, "identifier": "probe-1"}],
    "row_count": 1,
    "truncated": False,
}


def test_browse_tables_renders():
    with patch("app.api_client.list_db_tables", return_value=_TABLES), patch(
        "app.api_client.read_db_table", return_value=_DATA
    ):
        at = AppTest.from_file(PAGE).run()
    assert not at.exception
    # table picker + at least one rendered dataframe (the data grid)
    assert any(sb.label == "Table" for sb in at.selectbox)
    assert len(at.dataframe) >= 1
