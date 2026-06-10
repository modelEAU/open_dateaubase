"""Browser test — lab AnalysisSeries annotation renders on the explore page.

Real Chromium drives the Data Explorer: add a lab Trace (series 6, seeded as
"TEST_ COD at Final effluent"), snap the date window to its data via "Plot all",
and assert a lab annotation created against the live API surfaces in the overlay
summary table below the chart.

Preconditions (see scripts/dev_stack.sh + verify-app-in-browser skill):
  - stack up at :8501 / :8000, APP_DEV_AUTO_LOGIN=1
  - a range annotation titled "BROWSER-TEST range" on series 6 (this test seeds
    it idempotently if missing).

Run:  uv run pytest tests/e2e/ -m browser
"""
from __future__ import annotations

import re

import httpx
import pytest

playwright_sync = pytest.importorskip("playwright.sync_api")
Page = playwright_sync.Page
expect = playwright_sync.expect

API = "http://localhost:8000/api/v1"
SERIES_ID = 6
RANGE_TITLE = "BROWSER-TEST range"


def _ensure_seed_annotation() -> None:
    """Idempotently ensure a range annotation exists on series 6 to assert on."""
    try:
        r = httpx.get(
            f"{API}/analysis-series/{SERIES_ID}/annotations",
            params={"from": "2024-01-01T00:00:00", "to": "2024-12-31T00:00:00"},
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
            timeout=10,
        ).raise_for_status()
    except Exception as exc:  # pragma: no cover - diagnostic aid
        pytest.skip(f"API not ready to seed annotation: {exc}")


@pytest.mark.browser
def test_lab_series_annotation_renders_on_explore(page: Page, app_url: str) -> None:
    _ensure_seed_annotation()

    page.goto(app_url)
    expect(page).to_have_title(re.compile("datEAUbase"), timeout=30_000)

    # Navigate to the Data Explorer via the sidebar nav link.
    page.get_by_role("link", name="Visualize Data").click()
    expect(page.get_by_text("Data Explorer").first).to_be_visible(timeout=30_000)

    # Open the lab series picker and scope all further actions to its group
    # (a sensor picker with identical control labels sits alongside it).
    page.get_by_text("🧪 Lab / analysis series").click()
    lab = page.get_by_role("group").filter(has_text="🧪 Lab /")

    # Choose series 6 in the "Matching series" selectbox (a baseweb select
    # whose current value text starts with "LAB-").
    sel = lab.locator('[data-baseweb="select"]').filter(has_text="LAB-").last
    sel.scroll_into_view_if_needed()
    sel.click()
    page.get_by_role("option", name=re.compile(r"LAB-6\b")).first.click()

    lab.get_by_role("button", name="+ Add to plot").click()

    # Snap the date window to the series' data (2024-02) so its annotations load.
    plot_all = page.get_by_role("button", name="Plot all").first
    expect(plot_all).to_be_visible(timeout=30_000)
    plot_all.click()

    # The annotation surfaces in the overlay summary table below the chart.
    # st.dataframe renders a canvas-based glide-grid whose cells are mirrored
    # into hidden accessibility DOM nodes, so assert attachment, not visibility.
    expect(page.get_by_text(RANGE_TITLE).first).to_be_attached(timeout=30_000)
