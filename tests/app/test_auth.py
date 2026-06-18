"""Tests for app.auth."""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch

from app import auth


@pytest.fixture
def fake_st(monkeypatch):
    """Provide a mocked streamlit module with a plain dict session_state."""
    state: dict = {}
    mock_st = MagicMock()
    mock_st.session_state = state
    mock_st.rerun.side_effect = RuntimeError("st.rerun")
    mock_st.stop.side_effect = RuntimeError("st.stop")
    monkeypatch.setattr(auth, "st", mock_st)
    yield mock_st


class TestEnsureAuthState:
    def test_dev_auto_login_with_service_token(self, fake_st, monkeypatch):
        monkeypatch.setenv("APP_DEV_AUTO_LOGIN", "1")
        monkeypatch.setenv("API_SERVICE_TOKEN", "dev-service-token")

        auth._ensure_auth_state()

        assert fake_st.session_state["authenticated"] is True
        assert fake_st.session_state["access_token"] == "dev-service-token"
        assert fake_st.session_state["user"]["email"] == "dev@localhost"
        assert fake_st.session_state["_dev_auto_login_attempted"] is True
        assert fake_st.session_state["_dev_auto_login_disabled"] is False

    def test_dev_auto_login_without_service_token_is_disabled(self, fake_st, monkeypatch):
        monkeypatch.setenv("APP_DEV_AUTO_LOGIN", "1")
        monkeypatch.delenv("API_SERVICE_TOKEN", raising=False)

        auth._ensure_auth_state()

        assert fake_st.session_state["authenticated"] is False
        assert fake_st.session_state["access_token"] is None
        assert fake_st.session_state["user"] is None
        assert fake_st.session_state["_dev_auto_login_attempted"] is True
        assert fake_st.session_state["_dev_auto_login_disabled"] is True

    def test_dev_auto_login_does_not_re_login_after_logout(self, fake_st, monkeypatch):
        monkeypatch.setenv("APP_DEV_AUTO_LOGIN", "1")
        monkeypatch.setenv("API_SERVICE_TOKEN", "dev-service-token")

        auth._ensure_auth_state()
        assert fake_st.session_state["authenticated"] is True

        with pytest.raises(RuntimeError, match="st.rerun"):
            auth.logout()

        assert fake_st.session_state["authenticated"] is False
        assert fake_st.session_state["access_token"] is None
        assert fake_st.session_state["user"] is None
        assert fake_st.session_state["_dev_auto_login_disabled"] is True

        # A fresh auth check must not re-enable the dev session automatically.
        auth._ensure_auth_state()
        assert fake_st.session_state["authenticated"] is False


class TestIsAuthenticated:
    def test_requires_user_record(self, fake_st):
        fake_st.session_state.update({"authenticated": True, "user": None})
        assert auth.is_authenticated() is False

    def test_true_when_authenticated_and_user_present(self, fake_st):
        fake_st.session_state.update(
            {"authenticated": True, "user": {"user_id": 1}}
        )
        assert auth.is_authenticated() is True


class TestCompleteAuth:
    def test_clears_disabled_flag(self, fake_st):
        fake_st.session_state.update({"_dev_auto_login_disabled": True})

        auth._complete_auth(
            {
                "access_token": "user-jwt",
                "user": {"user_id": 1, "email": "a@b.com"},
            }
        )

        assert fake_st.session_state["authenticated"] is True
        assert fake_st.session_state["access_token"] == "user-jwt"
        assert fake_st.session_state["user"]["email"] == "a@b.com"
        assert fake_st.session_state["_dev_auto_login_disabled"] is False
        assert fake_st.session_state["_dev_auto_login_attempted"] is True


class TestRequireAuth:
    def test_stops_when_not_authenticated(self, fake_st):
        fake_st.session_state.update({"authenticated": False, "user": None})
        with pytest.raises(RuntimeError, match="st.stop"):
            auth.require_auth()

    def test_returns_when_authenticated(self, fake_st):
        fake_st.session_state.update(
            {"authenticated": True, "user": {"user_id": 1}}
        )
        # st.stop should not be called; require_auth returns normally.
        auth.require_auth()
        fake_st.stop.assert_not_called()


class TestRefreshCurrentUser:
    def test_logs_out_on_api_error(self, fake_st, monkeypatch):
        fake_st.session_state.update(
            {
                "authenticated": True,
                "access_token": "tok",
                "user": {"user_id": 1},
            }
        )
        monkeypatch.setattr(
            auth, "get_me", MagicMock(side_effect=auth.APIError(401, "nope"))
        )

        with pytest.raises(RuntimeError, match="st.rerun"):
            auth.refresh_current_user()

        assert fake_st.session_state["authenticated"] is False
        assert fake_st.session_state["access_token"] is None
        assert fake_st.session_state["user"] is None
        assert fake_st.session_state["_dev_auto_login_disabled"] is True
