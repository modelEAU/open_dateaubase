"""Browser smoke test — confirms the Streamlit app actually renders.

This is a thin tracer: a real Chromium loads the app and we assert a known element
appears. Deeper flow coverage (lab ingest, series_picker) belongs in additional
browser tests; exhaustive logic coverage belongs in headless AppTest (tests/app/).

Run:  uv run pytest tests/e2e/ -m browser   (needs `scripts/dev_stack.sh up`)
"""
from __future__ import annotations

import re

import pytest

# Skip this module cleanly if the `test` extra (pytest-playwright) isn't installed.
playwright_sync = pytest.importorskip("playwright.sync_api")
Page = playwright_sync.Page
expect = playwright_sync.expect


@pytest.mark.browser
def test_app_renders(page: Page, app_url: str) -> None:
    """The Streamlit app loads in a real browser and renders past the splash.

    Robust to auth state: a fresh instance shows the "Sign in" tab, while one
    started with APP_DEV_AUTO_LOGIN=1 lands on the dashboard (brand header).
    """
    page.goto(app_url)
    # Document title is set globally via st.set_page_config before navigation.
    expect(page).to_have_title(re.compile("datEAUbase"), timeout=30_000)
    # And at least one known view has rendered (logged-out OR logged-in).
    signed_out = page.get_by_text("Sign in")
    dashboard = page.get_by_role("heading", name="open_datEAUbase")
    expect(signed_out.or_(dashboard).first).to_be_visible(timeout=30_000)
