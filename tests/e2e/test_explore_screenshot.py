"""Playwright browser test: Explore page with one sensor trace + one lab trace.

Navigates to the Data Explorer, adds one Deployment Trace (sensor) and one
AnalysisSeries (lab) via the unified picker, waits for the chart, and saves
a screenshot to /tmp/explore_sensor_and_lab.png.

Run:  uv run pytest tests/e2e/test_explore_screenshot.py -m browser -s
Needs:  scripts/dev_stack.sh up  (API:8000 + app:8501 + demo seed with ELH rows)
"""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from playwright.sync_api import Page

playwright_sync = pytest.importorskip("playwright.sync_api")
expect = playwright_sync.expect

SCREENSHOT_PATH = Path("/tmp/explore_sensor_and_lab.png")


def _open_picker(page: "Page") -> None:
    """Ensure the 🔍 Add traces expander is open."""
    expander = page.locator("[data-testid='stExpander']").filter(has_text="Add traces")
    arrow = expander.locator("text=keyboard_arrow_right")
    if arrow.count():
        expander.first.click()
        page.wait_for_timeout(600)


def _add_selected_trace(page: "Page") -> None:
    """Click the '+ Add to plot' primary button and wait for Streamlit re-run."""
    page.get_by_role("button", name="+ Add to plot").click()
    # Wait for the page to re-run and settle.
    page.wait_for_timeout(2_000)



@pytest.mark.browser
def test_explore_screenshot_sensor_and_lab(page: "Page", app_url: str) -> None:
    """Add one sensor Deployment Trace and one lab AnalysisSeries, screenshot."""
    page.set_viewport_size({"width": 1280, "height": 1800})
    page.goto(f"{app_url}/explore", wait_until="networkidle")
    page.wait_for_selector("text=Add traces", timeout=30_000)
    page.wait_for_timeout(2_000)  # let Streamlit finish initial run

    _open_picker(page)
    page.wait_for_timeout(2_000)  # wait for deployment traces to load from API

    # Step 1: add the first (sensor) trace — default selection in the selectbox.
    expect(
        page.get_by_role("button", name="+ Add to plot")
    ).to_be_visible(timeout=10_000)
    _add_selected_trace(page)

    # Step 2: filter to "Influent" — only lab series exist there (no equipment
    # is deployed at the Influent sampling point in the demo seed).
    # This makes the selectbox show only lab entries without needing dropdown navigation.
    _open_picker(page)
    search_box = page.get_by_placeholder("type location, parameter, equipment, or campaign…")
    search_box.fill("Influent")
    search_box.press("Enter")  # trigger Streamlit re-run with the filter applied
    page.wait_for_timeout(2_000)  # let Streamlit re-run and filter options
    _add_selected_trace(page)

    # Wait for Plotly chart to render.
    page.wait_for_timeout(4_000)

    # Scroll down to bring the chart into view; Streamlit renders lazily.
    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    page.wait_for_timeout(2_000)
    page.evaluate("window.scrollTo(0, 0)")
    page.wait_for_timeout(1_000)

    page.screenshot(path=str(SCREENSHOT_PATH), full_page=True)
    print(f"\n  Screenshot saved → {SCREENSHOT_PATH}")

    assert page.locator("[data-testid='stException']").count() == 0, (
        "Streamlit exception visible on page"
    )
    assert SCREENSHOT_PATH.exists(), "Screenshot was not written"
    assert SCREENSHOT_PATH.stat().st_size > 10_000, "Screenshot suspiciously small"
