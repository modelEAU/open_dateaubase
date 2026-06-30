from unittest.mock import patch
from streamlit.testing.v1 import AppTest

APP = "app/Home.py"

_FAKE_USER = {"full_name": "Test User", "user_id": 1}


def _run(mock_sps, *, sites=None, persons=None, channels=None, analysis_series=None):
    ch_resp = {"items": channels or [], "total": len(channels or [])}
    with patch("app.api_client.list_sampling_points_lookup", return_value=mock_sps), \
         patch("app.api_client.list_sites_lookup", return_value=sites or []), \
         patch("app.api_client.list_persons_lookup", return_value=persons or []), \
         patch("app.api_client.list_channels", return_value=ch_resp), \
         patch("app.api_client.list_analysis_series_lookup", return_value=analysis_series or []), \
         patch("app.api_client.get_health", return_value={"api_version": "test", "db": "ok"}), \
         patch("app.auth.get_current_user", return_value=_FAKE_USER):
        at = AppTest.from_file(APP)
        at.run()
    return at


def _collect_text(at) -> str:
    """Join all visible text (markdown, info, success, warning, error, subheader, title)."""
    parts = []
    for el in at.get("markdown") + at.get("text") + at.get("info"):
        parts.append(el.value)
    return " ".join(parts)


def test_panel_shown_when_no_sampling_points():
    at = _run([])
    text = _collect_text(at)
    assert "Get started" in text or "sampling location" in text.lower()


def test_panel_shown_when_sps_exist_but_no_streams():
    """S2: sampling points alone no longer hide the panel; streams are required."""
    at = _run([{"sampling_point_id": 1, "name": "SP-1"}])
    text = _collect_text(at)
    assert "Get started" in text


def test_panel_hidden_when_stream_exists():
    """Auto-hides when at least one ingestable Stream (Channel) exists."""
    at = _run([], channels=[{"stream_id": 1}])
    text = _collect_text(at)
    assert "Get started" not in text


def test_panel_hidden_when_analysis_series_exists():
    """Auto-hides when at least one AnalysisSeries exists."""
    at = _run([], analysis_series=[{"analysis_series_id": 1}])
    text = _collect_text(at)
    assert "Get started" not in text


def test_ticks_appear_for_completed_steps():
    """Steps show ✓ when the list is non-empty."""
    at = _run([], sites=[{"site_id": 1}])
    text = _collect_text(at)
    assert "✓" in text
    assert "Get started" in text
