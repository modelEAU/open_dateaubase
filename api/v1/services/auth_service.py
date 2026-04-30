"""Service layer for authentication."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status

from ..repositories.auth_repository import AuthRepository


class AuthService:
    """Business logic for signup, login, and token validation."""

    def __init__(self, repo: AuthRepository):
        self.repo = repo
        self.secret = os.getenv("APP_AUTH_SECRET", "dev-only-auth-secret-change-me")
        self.token_ttl_hours = int(os.getenv("APP_AUTH_TOKEN_TTL_HOURS", "24"))

    def signup(self, email: str, full_name: str, password: str) -> dict:
        existing_user = self.repo.get_user_by_email(email)
        if existing_user is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="An account with this email already exists.",
            )

        password_hash = self._hash_password(password)
        user = self.repo.create_user(email=email, full_name=full_name, password_hash=password_hash)
        token = self._generate_token(user["user_id"], user["email"])

        return {
            "access_token": token,
            "token_type": "bearer",
            "user": user,
        }

    def login(self, email: str, password: str) -> dict:
        user = self.repo.get_user_by_email(email)
        if user is None or not self._verify_password(password, user["password_hash"]):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password.",
            )

        if not user["is_active"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This account is inactive.",
            )

        token = self._generate_token(user["user_id"], user["email"])

        return {
            "access_token": token,
            "token_type": "bearer",
            "user": self._public_user(user),
        }

    def get_current_user_from_token(self, token: str) -> dict:
        payload = self._decode_token(token)

        exp = payload.get("exp")
        user_id = payload.get("sub")

        if exp is None or user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication token.",
            )

        if datetime.now(timezone.utc).timestamp() > exp:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication token has expired.",
            )

        user = self.repo.get_user_by_id(int(user_id))
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found.",
            )

        if not user["is_active"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This account is inactive.",
            )

        return self._public_user(user)

    def _public_user(self, user: dict) -> dict:
        return {
            "user_id": user["user_id"],
            "email": user["email"],
            "full_name": user["full_name"],
            "is_active": user["is_active"],
            "is_verified": user["is_verified"],
            "created_at": user["created_at"],
            "updated_at": user["updated_at"],
        }

    def _hash_password(self, password: str) -> str:
        iterations = 100_000
        salt = secrets.token_hex(16)
        derived = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt.encode("utf-8"),
            iterations,
        )
        digest = base64.urlsafe_b64encode(derived).decode("utf-8")
        return f"pbkdf2_sha256${iterations}${salt}${digest}"

    def _verify_password(self, password: str, stored_hash: str) -> bool:
        try:
            algorithm, iterations_str, salt, expected_digest = stored_hash.split("$", 3)
            if algorithm != "pbkdf2_sha256":
                return False

            iterations = int(iterations_str)
            derived = hashlib.pbkdf2_hmac(
                "sha256",
                password.encode("utf-8"),
                salt.encode("utf-8"),
                iterations,
            )
            actual_digest = base64.urlsafe_b64encode(derived).decode("utf-8")
            return hmac.compare_digest(actual_digest, expected_digest)
        except Exception:
            return False

    def _generate_token(self, user_id: int, email: str) -> str:
        expires_at = datetime.now(timezone.utc) + timedelta(hours=self.token_ttl_hours)
        payload = {
            "sub": user_id,
            "email": email,
            "exp": expires_at.timestamp(),
        }

        payload_bytes = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        payload_b64 = base64.urlsafe_b64encode(payload_bytes).decode("utf-8").rstrip("=")

        signature = hmac.new(
            self.secret.encode("utf-8"),
            payload_b64.encode("utf-8"),
            hashlib.sha256,
        ).digest()
        signature_b64 = base64.urlsafe_b64encode(signature).decode("utf-8").rstrip("=")

        return f"{payload_b64}.{signature_b64}"

    def _decode_token(self, token: str) -> dict:
        try:
            payload_b64, signature_b64 = token.split(".", 1)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication token.",
            ) from exc

        expected_signature = hmac.new(
            self.secret.encode("utf-8"),
            payload_b64.encode("utf-8"),
            hashlib.sha256,
        ).digest()
        expected_signature_b64 = base64.urlsafe_b64encode(expected_signature).decode("utf-8").rstrip("=")

        if not hmac.compare_digest(signature_b64, expected_signature_b64):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication token.",
            )

        padded_payload = payload_b64 + "=" * (-len(payload_b64) % 4)
        payload_bytes = base64.urlsafe_b64decode(padded_payload.encode("utf-8"))
        return json.loads(payload_bytes.decode("utf-8"))
