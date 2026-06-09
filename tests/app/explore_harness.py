"""Minimal Streamlit harness for the Data Explorer AppTest.

Not a test file — executed by AppTest.from_file() to provide a Streamlit
context. The page's auto-run main() is guarded, so we call it explicitly here
(under whatever patches the test has installed on app.pages.explore).
"""
from __future__ import annotations

import sys
from pathlib import Path

_root = str(Path(__file__).parent.parent.parent)
if _root not in sys.path:
    sys.path.insert(0, _root)

from app.pages import explore

explore.main()
