"""UI feedback helpers (success, error, warning, info banners)."""

from __future__ import annotations

import streamlit as st


def success(message: str) -> None:
    st.success(message, icon="✅")


def error(message: str) -> None:
    st.error(message, icon="❌")


def warning(message: str) -> None:
    st.warning(message, icon="⚠️")


def info(message: str) -> None:
    st.info(message, icon="ℹ️")


def api_error(exc: Exception) -> None:
    """Display a user-friendly message for an APIError."""
    message = getattr(exc, "message", str(exc))
    st.error(f"API error: {message}", icon="❌")
