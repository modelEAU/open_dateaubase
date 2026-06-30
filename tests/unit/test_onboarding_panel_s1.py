from unittest.mock import patch
from streamlit.testing.v1 import AppTest

APP = "app/Home.py"

_FAKE_USER = {"full_name": "Test User", "user_id": 1}


def _run(mock_sps):
    with patch("app.api_client.list_sampling_points_lookup", return_value=mock_sps), \
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


def test_panel_hidden_when_sampling_points_exist():
    at = _run([{"sampling_point_id": 1, "name": "SP-1"}])
    text = _collect_text(at)
    assert "Get started" not in text
