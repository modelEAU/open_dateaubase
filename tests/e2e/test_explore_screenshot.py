"""Playwright browser tests: Explore page with real sensor + lab data.

Run:  uv run pytest tests/e2e/ -m browser -s
Needs: docker compose up  (API:8000 + app:8501 + demo seed)
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from playwright.sync_api import Page

playwright_sync = pytest.importorskip("playwright.sync_api")
expect = playwright_sync.expect

SCREENSHOT_PATH = Path("/tmp/explore_sensor_and_lab.png")
SCREENSHOT_ANN_PATH = Path("/tmp/explore_all_annotations.png")


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _open_picker(page: "Page") -> None:
    """Ensure the 🔍 Add streams expander is open."""
    expander = page.locator("[data-testid='stExpander']").filter(has_text="Add streams")
    arrow = expander.locator("text=keyboard_arrow_right")
    if arrow.count():
        expander.first.click()
        page.wait_for_timeout(600)


def _add_selected_trace(page: "Page") -> None:
    """Click the '+ Add to plot' primary button and wait for Streamlit re-run."""
    page.get_by_role("button", name="+ Add to plot").click()
    page.wait_for_timeout(2_000)


def _setup_both_traces(page: "Page", app_url: str) -> None:
    """Navigate to /explore, add one sensor trace and one lab (COD at Influent) trace."""
    page.set_viewport_size({"width": 1280, "height": 1800})
    page.goto(f"{app_url}/explore", wait_until="networkidle")
    page.wait_for_selector("text=Add streams", timeout=30_000)
    page.wait_for_timeout(2_000)

    _open_picker(page)
    page.wait_for_timeout(2_000)
    expect(page.get_by_role("button", name="+ Add to plot")).to_be_visible(timeout=10_000)
    _add_selected_trace(page)  # sensor: TEST_Turb-001 / Turbidity

    # Filter to "Influent" — only lab series live there (sensor is at Aerobic zone outlet)
    _open_picker(page)
    search = page.get_by_placeholder("type location, parameter, equipment, or campaign…")
    search.fill("Influent")
    search.press("Enter")
    page.wait_for_timeout(2_000)
    _add_selected_trace(page)  # lab: COD at Influent

    page.wait_for_selector("[data-testid='stPlotlyChart']", timeout=20_000)
    page.wait_for_timeout(3_000)  # let chart fully render


def _find_marker_center(page: "Page", trace_idx: int, point_idx: int = 0) -> dict | None:
    """Return viewport-relative center {x, y} of a Plotly scatter marker, or None."""
    return page.evaluate(
        """([ti, pi]) => {
            const plot = document.querySelector(
                '[data-testid="stPlotlyChart"] .js-plotly-plot'
            );
            if (!plot) return null;
            const traces = Array.from(plot.querySelectorAll('svg .scatter.trace'));
            if (traces.length <= ti) return null;
            const pts = traces[ti].querySelectorAll('.points path');
            if (pts.length <= pi) return null;
            const r = pts[pi].getBoundingClientRect();
            if (r.width === 0 && r.height === 0) return null;
            return {x: (r.left + r.right) / 2, y: (r.top + r.bottom) / 2};
        }""",
        [trace_idx, point_idx],
    )


def _drag_select_marker(page: "Page", trace_idx: int) -> None:
    """Select a data point via a tiny box drag in Plotly's box-select mode.

    Streamlit 1.55 sets layout.dragmode="select" by default on plotly_chart with
    on_select="rerun", so plotly_selected fires on any drag — no modebar click
    needed.  A zero-movement page.mouse.click() fires only plotly_click, which
    Streamlit does NOT subscribe to in this mode; only a drag triggers the
    plotly_selected event that causes st.rerun() with updated selection state.

    Trace 0 (sensor, hourly, ~1.6 px/pt): a 5 px box captures 2–4 points →
    button says "Create Annotation" (range annotation from those timestamps).
    Trace 1 (lab diamonds, ~228 px apart): a 5 px box captures exactly 1 →
    button says "Create Lab Annotation (point)" with observation_id set.
    """
    chart = page.locator("[data-testid='stPlotlyChart']")
    chart.scroll_into_view_if_needed()
    page.wait_for_timeout(1_500)  # let scroll + lazy-render settle

    center = None
    for idx in range(100):
        center = _find_marker_center(page, trace_idx, idx)
        if center:
            break
    assert center is not None, f"No visible marker found in trace {trace_idx}"

    half = 5  # 10 px total drag — reliably above Plotly's MIN_DRAG threshold
    page.mouse.move(center["x"] - half, center["y"] - half)
    page.mouse.down()
    page.mouse.move(center["x"] + half, center["y"] + half, steps=5)
    page.mouse.up()
    page.wait_for_timeout(3_000)  # wait for Streamlit rerun triggered by plotly_selected


def _fill_annotation_dialog(page: "Page", title: str) -> None:
    """Wait for the annotation dialog, fill title, click Save, wait for rerun."""
    expect(
        page.get_by_role("button", name="Save Annotation")
    ).to_be_visible(timeout=10_000)
    page.get_by_label("Title (optional)").fill(title)
    page.get_by_role("button", name="Save Annotation").click()
    page.wait_for_timeout(2_500)  # save API call + st.rerun()


def _fill_equipment_event_dialog(page: "Page", notes: str) -> None:
    """Wait for the equipment event dialog, fill notes, click Save Event, wait for rerun."""
    expect(
        page.get_by_role("button", name="Save Event")
    ).to_be_visible(timeout=10_000)
    page.get_by_label("Notes (optional)").fill(notes)
    page.get_by_role("button", name="Save Event").click()
    page.wait_for_timeout(2_500)


# ---------------------------------------------------------------------------
# Test 1: basic screenshot (sensor line + lab diamonds, no annotation flow)
# ---------------------------------------------------------------------------

@pytest.mark.browser
def test_explore_screenshot_sensor_and_lab(page: "Page", app_url: str) -> None:
    """Add one sensor Deployment Trace and one lab AnalysisSeries, screenshot."""
    _setup_both_traces(page, app_url)

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


# ---------------------------------------------------------------------------
# Test 2: all five annotation paths
# ---------------------------------------------------------------------------

@pytest.mark.browser
def test_all_annotation_paths(page: "Page", app_url: str) -> None:
    """Exercise every annotation entry point after real sensor+lab data is on the chart.

    Covered paths:
      1. Range annotation on sensor channel  (always-visible view-range button)
      2. Range annotation on lab series      (always-visible view-range button)
      3. Point annotation on sensor          (click sensor marker → dialog)
      4. Equipment event on sensor           (click sensor marker → Tag Equipment Event)
      5. Point annotation on lab             (click lab diamond → dialog)
    """
    _setup_both_traces(page, app_url)

    # Scroll to bottom so annotation controls are in viewport.
    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    page.wait_for_timeout(1_000)

    # ------------------------------------------------------------------
    # 1. Sensor range annotation
    # ------------------------------------------------------------------
    btn_sr = page.get_by_role("button", name="Create Annotation (view range)")
    btn_sr.scroll_into_view_if_needed()
    btn_sr.click()
    _fill_annotation_dialog(page, title="E2E-sensor-range")

    # ------------------------------------------------------------------
    # 2. Lab range annotation
    # ------------------------------------------------------------------
    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    page.wait_for_timeout(500)
    btn_lr = page.get_by_role("button", name="Create Lab Annotation (view range)")
    btn_lr.scroll_into_view_if_needed()
    btn_lr.click()
    _fill_annotation_dialog(page, title="E2E-lab-range")

    # ------------------------------------------------------------------
    # 3. Point annotation on sensor
    #    Click a sensor marker → "Create Annotation (point)" button appears below chart.
    #    After save + st.rerun(), the plotly widget state (key="scalar_chart") persists
    #    the selection, so step 4 can reuse it immediately.
    # ------------------------------------------------------------------
    _drag_select_marker(page, trace_idx=0)
    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    page.wait_for_timeout(500)

    btn_sp = page.get_by_role(
        "button", name=re.compile(r"Create Annotation(\s\(point\))?$")
    ).first
    btn_sp.scroll_into_view_if_needed()
    btn_sp.click()
    _fill_annotation_dialog(page, title="E2E-sensor-selection")

    # ------------------------------------------------------------------
    # 4. Equipment event
    #    Selection from step 3 may be preserved across the st.rerun().
    #    If cleared, re-drag.
    # ------------------------------------------------------------------
    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    page.wait_for_timeout(500)

    btn_eq = page.get_by_role("button", name="Tag Equipment Event")
    if not btn_eq.is_visible():
        _drag_select_marker(page, trace_idx=0)
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        page.wait_for_timeout(500)

    btn_eq.scroll_into_view_if_needed()
    btn_eq.click()
    _fill_equipment_event_dialog(page, notes="E2E-test-event")

    # ------------------------------------------------------------------
    # 5. Lab point annotation
    #    Lab diamonds are ~228 px apart; 5 px drag captures exactly one →
    #    "Create Lab Annotation (point)" with observation_id set.
    # ------------------------------------------------------------------
    _drag_select_marker(page, trace_idx=1)
    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    page.wait_for_timeout(500)

    btn_lp = page.get_by_role(
        "button", name=re.compile(r"Create Lab Annotation \(point\)|Create Lab Annotation")
    ).first
    btn_lp.scroll_into_view_if_needed()
    btn_lp.click()
    _fill_annotation_dialog(page, title="E2E-lab-point")

    # ------------------------------------------------------------------
    # Final checks
    # ------------------------------------------------------------------
    assert page.locator("[data-testid='stException']").count() == 0, (
        "Streamlit raised an exception during annotation flow"
    )
    page.screenshot(path=str(SCREENSHOT_ANN_PATH), full_page=True)
    print(f"\n  Screenshot saved → {SCREENSHOT_ANN_PATH}")
    assert SCREENSHOT_ANN_PATH.stat().st_size > 10_000, "Annotation screenshot suspiciously small"
