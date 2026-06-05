"""Fixtures for browser (Playwright) tests.

These tests need the full stack running (MSSQL + demo seed + API + Streamlit app,
see scripts/dev_stack.sh). They are opt-in via `-m browser` and AUTO-SKIP — never
fail — when the app is unreachable, so the default unit run and CI stay green.

The skip is applied in `pytest_collection_modifyitems` (at collection time) rather
than via a fixture, so it fires before pytest-playwright's `page` fixture tries to
launch a browser.
"""
from __future__ import annotations

import socket

import pytest

APP_HOST = "localhost"
APP_PORT = 8501


def _reachable(host: str, port: int, timeout: float = 1.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def pytest_collection_modifyitems(items) -> None:
    """Skip browser tests when the app isn't reachable."""
    if _reachable(APP_HOST, APP_PORT):
        return
    skip = pytest.mark.skip(
        reason=f"app not reachable at {APP_HOST}:{APP_PORT} — run `scripts/dev_stack.sh up`",
    )
    for item in items:
        if "browser" in item.keywords:
            item.add_marker(skip)


@pytest.fixture(scope="session")
def app_url() -> str:
    return f"http://{APP_HOST}:{APP_PORT}"
