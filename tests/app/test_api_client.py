"""Unit tests for app.api_client."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.api_client import APIError, get_health, login, signup, get_me, get_audit_logs


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mock_response(status_code: int, json_data: dict | None = None, text: str = "") -> MagicMock:
    resp = MagicMock()
    resp.status_code = status_code
    resp.is_success = 200 <= status_code < 300
    resp.text = text
    resp.json.return_value = json_data or {}
    return resp


class _FakeClient:
    """Context manager that returns itself and records calls."""

    def __init__(self, response: MagicMock):
        self._response = response
        self.last_method = None
        self.last_url = None
        self.last_kwargs: dict = {}

    def __enter__(self):
        return self

    def __exit__(self, *_):
        pass

    def get(self, url, **kwargs):
        self.last_method, self.last_url, self.last_kwargs = "GET", url, kwargs
        return self._response

    def post(self, url, **kwargs):
        self.last_method, self.last_url, self.last_kwargs = "POST", url, kwargs
        return self._response

    def delete(self, url, **kwargs):
        self.last_method, self.last_url, self.last_kwargs = "DELETE", url, kwargs
        return self._response

    def patch(self, url, **kwargs):
        self.last_method, self.last_url, self.last_kwargs = "PATCH", url, kwargs
        return self._response

    def put(self, url, **kwargs):
        self.last_method, self.last_url, self.last_kwargs = "PUT", url, kwargs
        return self._response


# ---------------------------------------------------------------------------
# APIError
# ---------------------------------------------------------------------------

class TestAPIError:
    def test_attributes(self):
        err = APIError(404, "not found")
        assert err.status_code == 404
        assert err.message == "not found"
        assert "404" in str(err)


# ---------------------------------------------------------------------------
# get_health
# ---------------------------------------------------------------------------

class TestGetHealth:
    def test_success(self):
        response = _mock_response(200, {"status": "ok", "db": "connected"})
        with patch("app.api_client._get_client", return_value=_FakeClient(response)):
            result = get_health()
        assert result["status"] == "ok"

    def test_connection_error_raises_api_error(self):
        import httpx

        with patch("app.api_client._get_client") as mock_client:
            instance = MagicMock()
            instance.__enter__ = MagicMock(side_effect=httpx.ConnectError("refused"))
            instance.__exit__ = MagicMock(return_value=False)
            mock_client.return_value = instance
            with pytest.raises(APIError) as exc_info:
                get_health()
        assert exc_info.value.status_code == 503

    def test_non_2xx_raises_api_error(self):
        response = _mock_response(503, {"detail": "DB down"})
        with patch("app.api_client._get_client", return_value=_FakeClient(response)):
            with pytest.raises(APIError) as exc_info:
                get_health()
        assert exc_info.value.status_code == 503


# ---------------------------------------------------------------------------
# signup
# ---------------------------------------------------------------------------

class TestSignup:
    def test_success(self):
        payload = {
            "access_token": "tok",
            "token_type": "bearer",
            "user": {"user_id": 1, "email": "a@b.com"},
        }
        response = _mock_response(200, payload)
        client = _FakeClient(response)
        with patch("app.api_client._get_client", return_value=client):
            result = signup("a@b.com", "Alice", "password1")
        assert result["access_token"] == "tok"
        assert client.last_method == "POST"
        assert client.last_url == "/auth/signup"

    def test_duplicate_email_raises(self):
        response = _mock_response(400, {"detail": "An account with this email already exists."})
        with patch("app.api_client._get_client", return_value=_FakeClient(response)):
            with pytest.raises(APIError) as exc_info:
                signup("dup@example.com", "Dup", "pass1234")
        assert exc_info.value.status_code == 400


# ---------------------------------------------------------------------------
# login
# ---------------------------------------------------------------------------

class TestLogin:
    def test_success(self):
        payload = {
            "access_token": "tok",
            "token_type": "bearer",
            "user": {"user_id": 1, "email": "a@b.com"},
        }
        response = _mock_response(200, payload)
        client = _FakeClient(response)
        with patch("app.api_client._get_client", return_value=client):
            result = login("a@b.com", "password1")
        assert result["access_token"] == "tok"
        assert client.last_method == "POST"
        assert client.last_url == "/auth/login"

    def test_wrong_credentials_raises(self):
        response = _mock_response(401, {"detail": "Invalid email or password."})
        with patch("app.api_client._get_client", return_value=_FakeClient(response)):
            with pytest.raises(APIError) as exc_info:
                login("a@b.com", "wrongpass")
        assert exc_info.value.status_code == 401


# ---------------------------------------------------------------------------
# get_me
# ---------------------------------------------------------------------------

class TestGetMe:
    def test_success(self):
        user = {"user_id": 1, "email": "a@b.com", "full_name": "Alice"}
        response = _mock_response(200, user)
        client = _FakeClient(response)
        with patch("app.api_client._get_client", return_value=client):
            result = get_me()
        assert result["email"] == "a@b.com"
        assert client.last_method == "GET"
        assert client.last_url == "/auth/me"

    def test_unauthorized_raises(self):
        response = _mock_response(401, {"detail": "Missing Authorization header."})
        fake_st = MagicMock()
        fake_st.session_state = {"access_token": None}
        with (
            patch("app.api_client.st", fake_st),
            patch("app.api_client._get_client", return_value=_FakeClient(response)),
        ):
            with pytest.raises(APIError) as exc_info:
                get_me()
        assert exc_info.value.status_code == 401


# ---------------------------------------------------------------------------
# get_audit_logs
# ---------------------------------------------------------------------------

class TestGetAuditLogs:
    def test_success(self):
        payload = {"items": [], "total": 0}
        response = _mock_response(200, payload)
        client = _FakeClient(response)
        with patch("app.api_client._get_client", return_value=client):
            result = get_audit_logs()
        assert "items" in result
        assert client.last_method == "GET"
        assert client.last_url == "/audit/logs"

    def test_with_filters(self):
        payload = {"items": [], "total": 0}
        response = _mock_response(200, payload)
        client = _FakeClient(response)
        with patch("app.api_client._get_client", return_value=client):
            get_audit_logs(user_id=1, action="login", limit=10)
        assert client.last_kwargs.get("params", {}).get("user_id") == 1
