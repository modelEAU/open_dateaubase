"""Browse Tables — read-only introspection of raw database contents.

Distinct from the curated CRUD pages: those edit a safe subset of fields through
the API's business logic; this shows *every* column of any table as stored,
read-only. Structure comes from the YAML schema dictionary; data from the
generic /admin/tables endpoint.
"""

from __future__ import annotations

import sys
from pathlib import Path

_project_root = str(Path(__file__).resolve().parent.parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

import pandas as pd
import streamlit as st

from app.api_client import APIError, list_db_tables, read_db_table
from app.components.schema_registry import load_table

st.title("Browse Tables")
st.caption(
    "Read-only view of raw database contents — including columns the edit forms "
    "deliberately hide. For editing, use the dedicated admin pages."
)

try:
    tables = list_db_tables()
except APIError as e:
    st.error(f"Cannot load table list: {e.message}")
    st.stop()

names = [t["name"] for t in tables]
if not names:
    st.info("No browsable tables found.")
    st.stop()

selected = st.selectbox(
    "Table", names, help="Which table of the data model to inspect."
)
limit = st.slider(
    "Max rows",
    min_value=50,
    max_value=1000,
    value=200,
    step=50,
    help="How many rows to fetch. Raise it to see more of a large table.",
)

# Structure (from the YAML schema dictionary, when the table has an entry).
try:
    meta = load_table(selected)
    with st.expander("Columns (schema)"):
        st.dataframe(
            pd.DataFrame(
                [
                    {
                        "column": c.name,
                        "type": c.logical_type,
                        "nullable": c.nullable,
                        "pk": c.is_pk,
                        "fk": c.fk_table or "",
                        "description": c.description,
                    }
                    for c in meta.columns
                ]
            ),
            use_container_width=True,
            hide_index=True,
        )
except Exception:
    st.caption("No YAML schema entry for this table; showing data only.")

# Data (live, from the DB).
try:
    data = read_db_table(selected, limit=limit)
except APIError as e:
    st.error(f"Cannot load rows: {e.message}")
    st.stop()

suffix = " (truncated)" if data["truncated"] else ""
st.caption(f"{data['row_count']} rows{suffix}")
st.dataframe(
    pd.DataFrame(data["rows"], columns=data["columns"]),
    use_container_width=True,
    hide_index=True,
)
