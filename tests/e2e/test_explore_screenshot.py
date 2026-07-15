"""Playwright browser tests: the Data Explorer Recording gesture on real data.

Run:   uv run pytest tests/e2e/ -m browser -s
Needs: the full stack (scripts/dev_stack.sh up) — MSSQL + demo seed + API + app.

Two things make this test what it is (both learned the hard way, keep them):

1. **Auth via Home, not direct /explore.** The app authenticates in Home.py
   (dev auto-login), which only runs when you land on the app root and navigate
   through `st.navigation`. A direct `goto(".../explore")` is served by
   Streamlit's filesystem page discovery, bypasses Home, and every API call 401s.

2. **The chart is an ECharts canvas, not Plotly SVG.** Point identity lives on a
   scatter *marker* layer that the toolbox brush selects; a plain canvas click
   rarely lands on a marker. So we activate the brush tool (a canvas-drawn icon
   near the top-right) and drag a tall box — that reliably captures points.
"""
from __future__ import annotations

from pathlib import Path

import pytest

playwright_sync = pytest.importorskip("playwright.sync_api")
expect = playwright_sync.expect

SHOT_RENDER = Path("/tmp/explore_echarts_render.png")
SHOT_RECORD = Path("/tmp/explore_recording_dialog.png")

# The demo turbidity deployment (TEST_Turb-001) lives here; the default 30-day
# window sits after the seed data ends (2026-06-09), so widen it before picking.
_WINDOW_FROM = "2026/04/01"
_WINDOW_TO = "2026/06/10"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _open_explore(page, app_url: str) -> None:
    """Land on the app root (runs Home.py auth), then open Visualize Data."""
    page.set_viewport_size({"width": 1400, "height": 2200})
    page.goto(f"{app_url}/", wait_until="networkidle")
    page.wait_for_timeout(3500)  # dev auto-login + st.navigation render
    page.get_by_role("link", name="Visualize Data").first.click()
    page.wait_for_selector("text=Add streams", timeout=20_000)
    page.wait_for_timeout(1500)


def _set_date(page, idx: int, value: str) -> None:
    inp = page.locator("[data-testid='stDateInput'] input").nth(idx)
    inp.click()
    page.wait_for_timeout(200)
    page.keyboard.press("Control+A")
    page.keyboard.press("Backspace")
    page.keyboard.type(value, delay=35)
    page.keyboard.press("Enter")  # NOT Escape — Escape reverts the typed value
    page.wait_for_timeout(1600)


def _add_first_trace(page) -> None:
    """Widen the window so the picker lists the demo trace, then add it."""
    _set_date(page, 0, _WINDOW_FROM)
    _set_date(page, 1, _WINDOW_TO)
    picker = page.locator("[data-testid='stExpander']").filter(has_text="Add streams")
    arrow = picker.locator("text=keyboard_arrow_right")
    if arrow.count():
        picker.first.click()
        page.wait_for_timeout(700)
    add = page.get_by_role("button", name="+ Add to plot")
    expect(add).to_be_enabled(timeout=10_000)
    add.click()
    page.wait_for_timeout(2500)
    # Frame the stream's real data range so the chart actually has points in view.
    page.get_by_role("button", name="All data").click()
    page.wait_for_timeout(3000)


def _brush_select_points(page) -> None:
    """Activate the ECharts toolbox brush and drag a tall box to select points.

    The brush icons are canvas-drawn, anchored to the top-right; an offset from
    the right edge hits the same icon regardless of canvas width. Try a couple of
    offsets and stop as soon as the selection reveals the Record button."""
    canvas = page.frame_locator("iframe").first.locator("canvas").first
    canvas.scroll_into_view_if_needed()
    page.wait_for_timeout(1500)
    box = canvas.bounding_box()
    assert box, "ECharts canvas not found"
    x, y, w, h = box["x"], box["y"], box["width"], box["height"]

    record = page.get_by_role("button", name="Record what happened")
    for right_offset in (66, 88, 44):
        page.mouse.click(x + w - right_offset, y + 20)  # a brush toolbox icon
        page.wait_for_timeout(400)
        page.mouse.move(x + w * 0.35, y + h * 0.15)
        page.mouse.down()
        page.mouse.move(x + w * 0.60, y + h * 0.85, steps=12)
        page.mouse.up()
        page.wait_for_timeout(2000)
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        page.wait_for_timeout(1200)
        if record.count():
            return
    raise AssertionError("brush selection did not reveal the Record button")


# ---------------------------------------------------------------------------
# Test 1: the ECharts chart renders on real data, authenticated
# ---------------------------------------------------------------------------

@pytest.mark.browser
def test_explore_renders_echarts_chart(page, app_url: str) -> None:
    _open_explore(page, app_url)
    _add_first_trace(page)

    canvas = page.frame_locator("iframe").first.locator("canvas").first
    expect(canvas).to_be_visible(timeout=15_000)
    page.screenshot(path=str(SHOT_RENDER), full_page=True)

    assert page.locator("[data-testid='stException']").count() == 0, (
        "Streamlit exception visible on the Explore page"
    )
    assert SHOT_RENDER.stat().st_size > 10_000, "render screenshot suspiciously small"


# ---------------------------------------------------------------------------
# Test 2: the Recording gesture — brush → dialog → write one Event
# ---------------------------------------------------------------------------

@pytest.mark.browser
def test_recording_gesture_writes_an_event(page, app_url: str) -> None:
    """Standing on a plotted series, brush points, open the Recording dialog on
    the equipment rung (a cause), pick a kind and record. The rung routes the
    write to a single Event — no Event/Annotation choice ever shown."""
    _open_explore(page, app_url)
    _add_first_trace(page)
    _brush_select_points(page)

    page.get_by_role("button", name="Record what happened").first.click()
    page.wait_for_timeout(1500)

    dialog = page.get_by_role("dialog")
    expect(dialog).to_be_visible(timeout=10_000)
    # The dialog leads with the target rung, defaulting to the equipment ("the
    # probe") — a cause target, never the Event/Annotation split.
    assert "What did this happen to" in dialog.inner_text()

    # Pick a kind (index 0 is the "— none —" sentinel), then record.
    kind = dialog.locator("[data-testid='stSelectbox']").nth(1)
    kind.click()
    page.wait_for_timeout(600)
    options = page.get_by_role("option")
    assert options.count() > 1, "no event kinds offered on the equipment rung"
    options.nth(1).click()
    page.wait_for_timeout(700)

    dialog.get_by_role("button", name="Record").click()
    page.wait_for_timeout(2500)  # create_event + st.rerun (closes the dialog)

    page.screenshot(path=str(SHOT_RECORD), full_page=True)
    assert page.locator("[data-testid='stException']").count() == 0, (
        "Streamlit raised an exception during the Recording flow"
    )
    # The write succeeded and the dialog closed itself on rerun.
    assert page.get_by_role("dialog").count() == 0, "Recording dialog did not close"
