import streamlit as st
from api_metadata.components.auth import ensure_auth_state, render_login, logout
from api_metadata.components.sidebar import render_sidebar
from api_metadata.services.db_client import api_get
from api_metadata.ui_style import apply_global_style
from api_metadata.workspace_pages import dashboard, metadata_explorer

st.set_page_config(page_title="datEAUbase", layout="wide", initial_sidebar_state="collapsed")

def workspace():
    try:
        api_get("/auth/me")
    except Exception:
        logout()
        st.stop()

    route = render_sidebar(st.session_state.get("username", ""))

    if route == "dashboard":
        dashboard.render()
    elif route == "metadata_list":
        metadata_explorer.render_list()
    elif route == "metadata_create":
        metadata_explorer.render_create()
    else:
        st.error("Page inconnue.")

def main():
    ensure_auth_state()
    is_auth = bool(st.session_state.get("authenticated") and st.session_state.get("token"))

    # IMPORTANT: assure-toi que apply_global_style accepte authenticated=...
    apply_global_style(authenticated=is_auth)

    if not is_auth:
        render_login()
        st.stop()

    workspace()

if __name__ == "__main__":
    main()
