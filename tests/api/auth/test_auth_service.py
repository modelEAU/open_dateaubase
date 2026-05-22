"""Unit tests for AuthService."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from api.v1.services.auth_service import AuthService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_user(**kwargs) -> dict:
    defaults = {
        "user_id": 1,
        "email": "alice@example.com",
        "full_name": "Alice",
        "password_hash": "",
        "is_active": True,
        "is_verified": True,
        "created_at": "2024-01-01T00:00:00",
        "updated_at": "2024-01-01T00:00:00",
    }
    return {**defaults, **kwargs}


def _make_service(repo=None) -> AuthService:
    if repo is None:
        repo = MagicMock()
    svc = AuthService(repo)
    svc.secret = "test-secret"
    return svc


# ---------------------------------------------------------------------------
# Password hashing
# ---------------------------------------------------------------------------

class TestPasswordHashing:
    def test_hash_is_not_plaintext(self):
        svc = _make_service()
        h = svc._hash_password("mysecretpassword")
        assert "mysecretpassword" not in h

    def test_verify_correct_password(self):
        svc = _make_service()
        h = svc._hash_password("correct-horse-battery-staple")
        assert svc._verify_password("correct-horse-battery-staple", h) is True

    def test_verify_wrong_password(self):
        svc = _make_service()
        h = svc._hash_password("correct-horse-battery-staple")
        assert svc._verify_password("wrong-password", h) is False

    def test_verify_malformed_hash_returns_false(self):
        svc = _make_service()
        assert svc._verify_password("password", "not-a-valid-hash") is False

    def test_different_salts_produce_different_hashes(self):
        svc = _make_service()
        h1 = svc._hash_password("same-password")
        h2 = svc._hash_password("same-password")
        assert h1 != h2


# ---------------------------------------------------------------------------
# Token generation and decoding
# ---------------------------------------------------------------------------

class TestTokens:
    def test_generate_and_decode_roundtrip(self):
        svc = _make_service()
        token = svc._generate_token(42, "alice@example.com")
        payload = svc._decode_token(token)
        assert payload["sub"] == "42"
        assert payload["email"] == "alice@example.com"
        assert "exp" in payload

    def test_tampered_token_raises(self):
        from fastapi import HTTPException

        svc = _make_service()
        token = svc._generate_token(1, "alice@example.com")
        tampered = token[:-4] + "XXXX"
        with pytest.raises(HTTPException) as exc_info:
            svc._decode_token(tampered)
        assert exc_info.value.status_code == 401

    def test_malformed_token_raises(self):
        from fastapi import HTTPException

        svc = _make_service()
        with pytest.raises(HTTPException) as exc_info:
            svc._decode_token("notavalidtoken")
        assert exc_info.value.status_code == 401

    def test_expired_token_raises(self):
        from datetime import datetime, timezone
        from fastapi import HTTPException
        import json, base64, hmac, hashlib

        svc = _make_service()
        payload = {"sub": 1, "email": "a@b.com", "exp": 0.0}  # epoch = expired
        payload_bytes = json.dumps(payload, separators=(",", ":")).encode()
        payload_b64 = base64.urlsafe_b64encode(payload_bytes).decode().rstrip("=")
        sig = hmac.new(svc.secret.encode(), payload_b64.encode(), hashlib.sha256).digest()
        sig_b64 = base64.urlsafe_b64encode(sig).decode().rstrip("=")
        token = f"{payload_b64}.{sig_b64}"

        with pytest.raises(HTTPException) as exc_info:
            svc.get_current_user_from_token(token)
        assert exc_info.value.status_code == 401


# ---------------------------------------------------------------------------
# Signup
# ---------------------------------------------------------------------------

class TestSignup:
    def test_signup_creates_user_and_returns_token(self):
        repo = MagicMock()
        repo.get_user_by_email.return_value = None
        new_user = _make_user()
        repo.create_user.return_value = {k: v for k, v in new_user.items() if k != "password_hash"}
        svc = _make_service(repo)

        result = svc.signup("alice@example.com", "Alice", "securepass")

        assert "access_token" in result
        assert result["token_type"] == "bearer"
        assert result["user"]["email"] == "alice@example.com"
        repo.create_user.assert_called_once()

    def test_signup_duplicate_email_raises(self):
        from fastapi import HTTPException

        repo = MagicMock()
        repo.get_user_by_email.return_value = _make_user()
        svc = _make_service(repo)

        with pytest.raises(HTTPException) as exc_info:
            svc.signup("alice@example.com", "Alice", "securepass")
        assert exc_info.value.status_code == 400


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------

class TestLogin:
    def test_login_valid_credentials(self):
        svc = _make_service()
        password = "correct-password"
        user = _make_user(password_hash=svc._hash_password(password))
        svc.repo.get_user_by_email.return_value = user

        result = svc.login("alice@example.com", password)

        assert "access_token" in result
        assert result["user"]["email"] == "alice@example.com"
        assert "password_hash" not in result["user"]

    def test_login_wrong_password_raises(self):
        from fastapi import HTTPException

        svc = _make_service()
        user = _make_user(password_hash=svc._hash_password("correct"))
        svc.repo.get_user_by_email.return_value = user

        with pytest.raises(HTTPException) as exc_info:
            svc.login("alice@example.com", "wrong")
        assert exc_info.value.status_code == 401

    def test_login_unknown_email_raises(self):
        from fastapi import HTTPException

        svc = _make_service()
        svc.repo.get_user_by_email.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            svc.login("nobody@example.com", "pass")
        assert exc_info.value.status_code == 401

    def test_login_inactive_user_raises(self):
        from fastapi import HTTPException

        svc = _make_service()
        password = "mypass"
        user = _make_user(password_hash=svc._hash_password(password), is_active=False)
        svc.repo.get_user_by_email.return_value = user

        with pytest.raises(HTTPException) as exc_info:
            svc.login("alice@example.com", password)
        assert exc_info.value.status_code == 403


# ---------------------------------------------------------------------------
# get_current_user_from_token
# ---------------------------------------------------------------------------

class TestGetCurrentUser:
    def test_valid_token_returns_user(self):
        svc = _make_service()
        user = _make_user()
        svc.repo.get_user_by_id.return_value = user
        token = svc._generate_token(user["user_id"], user["email"])

        result = svc.get_current_user_from_token(token)

        assert result["user_id"] == 1
        assert "password_hash" not in result

    def test_user_not_found_raises(self):
        from fastapi import HTTPException

        svc = _make_service()
        svc.repo.get_user_by_id.return_value = None
        token = svc._generate_token(99, "ghost@example.com")

        with pytest.raises(HTTPException) as exc_info:
            svc.get_current_user_from_token(token)
        assert exc_info.value.status_code == 401

    def test_inactive_user_raises(self):
        from fastapi import HTTPException

        svc = _make_service()
        user = _make_user(is_active=False)
        svc.repo.get_user_by_id.return_value = user
        token = svc._generate_token(user["user_id"], user["email"])

        with pytest.raises(HTTPException) as exc_info:
            svc.get_current_user_from_token(token)
        assert exc_info.value.status_code == 403
