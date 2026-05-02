"""Typed HTTP client for the open_datEAUbase FastAPI backend.

One function per API route. All functions are synchronous (no async/await).
On non-2xx responses: raises APIError(status_code, message).
On connection failure: raises APIError(503, "Cannot reach API").
"""

from __future__ import annotations

import httpx
import streamlit as st

from app.config import settings


class APIError(Exception):
    """Raised when the API returns a non-2xx response or is unreachable."""

    def __init__(self, status_code: int, message: str) -> None:
        self.status_code = status_code
        self.message = message
        super().__init__(f"APIError {status_code}: {message}")


def _get_client() -> httpx.Client:
    headers = {}
    token = st.session_state.get("access_token")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return httpx.Client(base_url=settings.API_BASE_URL, timeout=30, headers=headers)


def _raise_for_status(response: httpx.Response) -> None:
    if response.status_code == 401 and st.session_state.get("access_token"):
        st.session_state.clear()
        st.error("Session expired. Please log in again.")
        st.rerun()
    if not response.is_success:
        try:
            detail = response.json().get("detail", response.text)
        except Exception:
            detail = response.text
        raise APIError(response.status_code, str(detail))


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

def get_health() -> dict:
    try:
        with _get_client() as client:
            r = client.get("/health")
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)
    return r.json()


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

def signup(email: str, full_name: str, password: str) -> dict:
    try:
        with _get_client() as client:
            r = client.post(
                "/auth/signup",
                json={"email": email, "full_name": full_name, "password": password},
            )
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)
    return r.json()


def login(email: str, password: str) -> dict:
    try:
        with _get_client() as client:
            r = client.post(
                "/auth/login",
                json={"email": email, "password": password},
            )
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)
    return r.json()


def get_me() -> dict:
    try:
        with _get_client() as client:
            r = client.get("/auth/me")
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)
    return r.json()


# ---------------------------------------------------------------------------
# Audit
# ---------------------------------------------------------------------------

def get_audit_logs(
    *,
    user_id: int | None = None,
    action: str | None = None,
    resource_type: str | None = None,
    from_dt: str | None = None,
    to_dt: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> dict:
    params: dict = {"limit": limit, "offset": offset}
    if user_id is not None:
        params["user_id"] = user_id
    if action:
        params["action"] = action
    if resource_type:
        params["resource_type"] = resource_type
    if from_dt:
        params["from_dt"] = from_dt
    if to_dt:
        params["to_dt"] = to_dt

    try:
        with _get_client() as client:
            r = client.get("/audit/logs", params=params)
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)
    return r.json()
