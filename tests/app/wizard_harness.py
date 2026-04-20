"""Minimal Streamlit harness for campaign wizard AppTest.

Not a test file — executed by AppTest.from_file() to provide a Streamlit
context in which render_wizard() can run with session state pre-seeded by
each test.
"""
from __future__ import annotations

import sys
from pathlib import Path

_root = str(Path(__file__).parent.parent.parent)
if _root not in sys.path:
    sys.path.insert(0, _root)

import streamlit as st

from app.components.campaign_wizard import render_wizard

st.set_page_config(page_title="Wizard Test Harness")
render_wizard()
