"""AppTest coverage for the AnalysisSeries picker."""
from __future__ import annotations

from contextlib import ExitStack, contextmanager
from pathlib import Path
from unittest.mock import patch

import pytest
from streamlit.testing.v1 import AppTest

HARNESS = str(Path(__file__).parent / "series_picker_harness.py")
MOD = "app.api_client"


@contextmanager
def _offline(**extra):
    """Cut every API call the picker makes; `extra` overrides a return value."""
    with ExitStack() as stack:
        stack.enter_context(
            patch(f"{MOD}.list_sampling_points_lookup", return_value=[])
        )
        stack.enter_context(
            patch("app.components.param_unit.list_parameter_units_lookup",
                  return_value=[])
        )
        for name, value in extra.items():
            stack.enter_context(patch(f"{MOD}.{name}", return_value=value))
        yield


def _step(at: AppTest, **extra) -> AppTest:
    with _offline(**extra):
        at.run()
    return at


def _run() -> AppTest:
    return _step(AppTest.from_file(HARNESS, default_timeout=30))


def _widget(at: AppTest, kind: str, key: str):
    return next(w for w in getattr(at, kind) if w.key == key)


def _open_create_form(at: AppTest) -> AppTest:
    _widget(at, "button", "spkr_series_toggle_create").click()
    return _step(at)


def test_filter_row_is_labelled_as_search():
    """#75 — the filter row must not read as a second create form."""
    at = _run()
    assert any("Search existing series" in c.value for c in at.caption)


def test_create_form_inherits_filter_selection():
    """#74 — filters chosen while searching seed the create form."""
    at = _run()
    _widget(at, "selectbox", "spkr_series_camp_sel").set_value("Alpha")
    _widget(at, "selectbox", "spkr_series_param_sel").set_value("TSS")
    _step(at)

    _open_create_form(at)

    assert _widget(at, "selectbox", "spkr_series_nc_camp").value == "Alpha"
    assert _widget(at, "selectbox", "spkr_series_nc_param").value == "TSS"


def test_value_kind_is_derived_from_parameter():
    """#76 — value kind follows Parameter.ValueKind_ID and is not editable."""
    at = _open_create_form(_run())
    _widget(at, "selectbox", "spkr_series_nc_param").set_value("Thermal image")
    _step(at)

    vk = next(w for w in at.text_input if w.label == "Value kind")
    assert vk.value == "Image"
    assert vk.disabled


def test_created_series_is_visible_immediately():
    """#77 — a freshly created series must show up without a page reload."""
    at = _open_create_form(_run())
    _widget(at, "selectbox", "spkr_series_nc_param").set_value("TSS")
    _widget(at, "selectbox", "spkr_series_nc_sp").set_value("Outlet")
    _step(at)
    _widget(at, "selectbox", "spkr_series_nc_unit").set_value("mg/L")
    _step(at)

    _widget(at, "button", "spkr_series_create_btn").click()
    _step(at, create_analysis_series={"analysis_series_id": 99})

    # Chip resolves to the real name, not the "Series 99" fallback.
    assert any(
        b.key == "spkr_series_rm_99" and "TSS at Outlet" in b.label for b in at.button
    )

    # ...and it stays resolvable until the caller's own fetch catches up.
    carried = at.session_state["spkr_series_created"]
    assert [s["analysis_series_id"] for s in carried] == [99]
    assert carried[0]["value_kind_id"] == 1


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__]))
