"""Browser test — a lab AnalysisSeries annotation renders on the Explore chart.

Real Chromium drives the Data Explorer: add the lab series 6 ("TEST_ COD at Final
effluent"), snap the window to its data, and assert an annotation created against
the live API surfaces in the overlay summary table below the chart. This exercises
the read-back overlay (independent of the Recording *write* dialog).

Preconditions (see scripts/dev_stack.sh + verify-app-in-browser skill):
  - stack up at :8501 / :8000, APP_DEV_AUTO_LOGIN=1
  - the seed annotation is created idempotently below (authenticated with the
    dev service token).

Run:  uv run pytest tests/e2e/ -m browser
"""
from __future__ import annotations

import os
import re

import httpx
import pytest

playwright_sync = pytest.importorskip("playwright.sync_api")
Page = playwright_sync.Page
expect = playwright_sync.expect

API = "http://localhost:8000/api/v1"
SERIES_ID = 6
RANGE_TITLE = "BROWSER-TEST range"
# Same dev service token the app auto-logs-in with; the API accepts it as a bearer.
_TOKEN = os.getenv("API_SERVICE_TOKEN", "dev-service-token")
_AUTH = {"Authorization": f"Bearer {_TOKEN}"}


def _ensure_seed_annotation() -> None:
    """Idempotently ensure a range annotation exists on series 6 to assert on."""
    try:
        r = httpx.get(
            f"{API}/analysis-series/{SERIES_ID}/annotations",
            params={"from": "2024-01-01T00:00:00", "to": "2024-12-31T00:00:00"},
            headers=_AUTH,
            timeout=10,
        )
        r.raise_for_status()
        if any(a.get("title") == RANGE_TITLE for a in r.json().get("annotations", [])):
            return
        httpx.post(
            f"{API}/analysis-series/{SERIES_ID}/annotations",
            json={
                "annotation_type": "Anomaly",
                "start_time": "2024-02-04T16:00:00",
                "end_time": "2024-02-05T10:00:00",
                "title": RANGE_TITLE,
                "comment": "spans COD effluent samples",
            },
            headers=_AUTH,
            timeout=10,
        ).raise_for_status()
    except Exception as exc:  # pragma: no cover - diagnostic aid
        pytest.skip(f"API not ready to seed annotation: {exc}")


def _set_date(page: Page, idx: int, value: str) -> None:
    inp = page.locator("[data-testid='stDateInput'] input").nth(idx)
    inp.click()
    page.wait_for_timeout(200)
    page.keyboard.press("Control+A")
    page.keyboard.press("Backspace")
    page.keyboard.type(value, delay=35)
    page.keyboard.press("Enter")
    page.wait_for_timeout(1600)


@pytest.mark.browser
def test_lab_series_annotation_renders_on_explore(page: Page, app_url: str) -> None:
    _ensure_seed_annotation()

    # Auth lives in Home.py — land on the root, then navigate via st.navigation.
    page.set_viewport_size({"width": 1400, "height": 2200})
    page.goto(app_url, wait_until="networkidle")
    expect(page).to_have_title(re.compile("datEAUbase"), timeout=30_000)
    page.get_by_role("link", name="Visualize Data").first.click()
    expect(page.get_by_text("Data Explorer").first).to_be_visible(timeout=30_000)
    page.wait_for_timeout(1500)

    # The annotation is Feb 2024; widen the window so the series' data loads.
    _set_date(page, 0, "2024/01/01")
    _set_date(page, 1, "2024/12/31")

    # Unified picker: narrow to the COD effluent series, then add it.
    picker = page.locator("[data-testid='stExpander']").filter(has_text="Add streams")
    arrow = picker.locator("text=keyboard_arrow_right")
    if arrow.count():
        picker.first.click()
        page.wait_for_timeout(700)
    search = page.get_by_placeholder(
        "type location, parameter, equipment, or campaign…"
    )
    search.fill("Final effluent")
    search.press("Enter")
    page.wait_for_timeout(1500)

    # The "Matching streams" selectbox is the last one on the page (after the
    # campaign filter + 5 cascade filters). Open it and pick the COD series.
    page.locator("[data-testid='stSelectbox']").last.click()
    page.wait_for_timeout(600)
    # "COD concentration" uniquely picks series 6 (vs "COD filtered concentration").
    page.get_by_role("option").filter(has_text="COD concentration").first.click()
    page.wait_for_timeout(800)
    page.get_by_role("button", name="+ Add to plot").click()
    page.wait_for_timeout(2500)

    # Snap the window to the series' data so its annotations load onto the chart.
    page.get_by_role("button", name="All data").click()
    page.wait_for_timeout(3000)

    # The annotation surfaces in the overlay summary table below the chart. The
    # st.dataframe glide-grid mirrors cells into hidden a11y DOM nodes, so assert
    # attachment, not visibility.
    expect(page.get_by_text(RANGE_TITLE).first).to_be_attached(timeout=30_000)
    assert page.locator("[data-testid='stException']").count() == 0
