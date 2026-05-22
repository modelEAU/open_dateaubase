"""Authentication helpers for the Streamlit app."""

from __future__ import annotations

import os

import streamlit as st

from app.api_client import APIError, get_me, login, signup

def _ensure_auth_state() -> None:
    st.session_state.setdefault("authenticated", False)
    st.session_state.setdefault("access_token", None)
    st.session_state.setdefault("user", None)

    if os.getenv("APP_DEV_AUTO_LOGIN") == "1" and not st.session_state["authenticated"]:
        st.session_state["authenticated"] = True
        st.session_state["access_token"] = "dev"
        st.session_state["user"] = {
            "user_id": 0,
            "email": os.getenv("APP_DEV_EMAIL", "dev@localhost"),
            "full_name": os.getenv("APP_DEV_NAME", "Dev User"),
            "is_active": True,
            "is_verified": True,
            "created_at": None,
            "updated_at": None,
        }


def is_authenticated() -> bool:
    _ensure_auth_state()
    return bool(st.session_state.get("authenticated") and st.session_state.get("user"))


def require_auth(show_login: bool = False) -> None:
    """Guard pages that require authentication."""
    _ensure_auth_state()

    if is_authenticated():
        return

    if show_login:
        _show_auth_page()
    else:
        st.title("Authentication required")
        st.info("Please sign in from the Home page to access the application.")
    st.stop()


def get_current_user() -> dict | None:
    _ensure_auth_state()
    return st.session_state.get("user")


def logout() -> None:
    st.session_state["authenticated"] = False
    st.session_state["access_token"] = None
    st.session_state["user"] = None
    st.rerun()


def _complete_auth(auth_response: dict) -> None:
    st.session_state["access_token"] = auth_response["access_token"]
    st.session_state["authenticated"] = True
    st.session_state["user"] = auth_response["user"]


def _show_auth_page() -> None:
    _ensure_auth_state()

    st.title("open_datEAUbase")
    st.caption("Water quality data management")

    tab_login, tab_signup = st.tabs(["Sign in", "Sign up"])

    with tab_login:
        with st.form("login_form"):
            email = st.text_input("Email", key="login_email")
            password = st.text_input("Password", type="password", key="login_password")
            submitted = st.form_submit_button("Sign in")

        if submitted:
            if not email or not password:
                st.error("Please enter your email and password.")
            else:
                try:
                    auth_response = login(email=email, password=password)
                    _complete_auth(auth_response)
                    st.rerun()
                except APIError as e:
                    st.error(e.message)

    with tab_signup:
        with st.form("signup_form"):
            full_name = st.text_input("Full name", key="signup_full_name")
            email = st.text_input("Email", key="signup_email")
            password = st.text_input("Password", type="password", key="signup_password")
            confirm_password = st.text_input(
                "Confirm password", type="password", key="signup_confirm_password"
            )
            submitted = st.form_submit_button("Create account")

        if submitted:
            if not full_name or not email or not password or not confirm_password:
                st.error("Please fill in all fields.")
            elif password != confirm_password:
                st.error("Passwords do not match.")
            elif len(password) < 8:
                st.error("Password must be at least 8 characters long.")
            else:
                try:
                    auth_response = signup(
                        email=email,
                        full_name=full_name,
                        password=password,
                    )
                    _complete_auth(auth_response)
                    st.rerun()
                except APIError as e:
                    st.error(e.message)


def refresh_current_user() -> None:
    _ensure_auth_state()
    token = st.session_state.get("access_token")
    if not token:
        return

    try:
        user = get_me()
        st.session_state["user"] = user
        st.session_state["authenticated"] = True
    except APIError:
        logout()
