# api_metadata/services/db_client.py
from __future__ import annotations

import os
from typing import Any, Optional

import requests
import streamlit as st


API_BASE_URL = os.getenv("API_BASE_URL", "http://api:8000")
TIMEOUT_SECONDS = int(os.getenv("API_TIMEOUT", "20"))


class ApiError(RuntimeError):
    def __init__(self, status_code: int, message: str, raw: str | None = None):
        super().__init__(f"{status_code}: {message}")
        self.status_code = status_code
        self.message = message
        self.raw = raw


def _headers(with_auth: bool = True) -> dict:
    headers = {"Content-Type": "application/json"}
    if with_auth:
        token = st.session_state.get("token")
        if token:
            headers["Authorization"] = f"Bearer {token}"
    return headers


def _parse_error(resp: requests.Response) -> str:
    try:
        data = resp.json()
        detail = data.get("detail")
        if isinstance(detail, str):
            return detail
        if isinstance(detail, list):
            return "Validation error"
    except Exception:
        pass
    return resp.text or "Unknown error"


def _handle_unauthorized():
    st.session_state["authenticated"] = False
    st.session_state["token"] = None
    st.session_state["username"] = None


def _request(
    method: str,
    path: str,
    *,
    params: Optional[dict] = None,
    json: Optional[dict] = None,
    with_auth: bool = True,
) -> Any:
    url = f"{API_BASE_URL}{path}"

    try:
        resp = requests.request(
            method,
            url,
            params=params,
            json=json,
            headers=_headers(with_auth),
            timeout=TIMEOUT_SECONDS,
        )
    except requests.RequestException as e:
        raise ApiError(0, f"API unreachable: {e}") from e

    if resp.status_code >= 400:
        msg = _parse_error(resp)

        if resp.status_code == 401 and with_auth:
            _handle_unauthorized()

        raise ApiError(resp.status_code, msg, raw=resp.text)

    if not resp.content:
        return None

    try:
        return resp.json()
    except Exception as e:
        raise ApiError(resp.status_code, "Invalid JSON response from API", raw=resp.text) from e


def api_get(path: str, params: dict | None = None, with_auth: bool = True):
    return _request("GET", path, params=params, with_auth=with_auth)


def api_post(path: str, json: dict | None = None, with_auth: bool = True):
    return _request("POST", path, json=json, with_auth=with_auth)
