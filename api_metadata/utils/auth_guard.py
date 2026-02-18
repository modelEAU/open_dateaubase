import streamlit as st
from api_metadata.components.auth import ensure_auth_state, render_login

def require_auth():
    """
    Must be called at the very top of app/page.
    If not authenticated, shows login and stops the page.
    """
    ensure_auth_state()
    if not st.session_state.get("authenticated") or not st.session_state.get("token"):
        render_login()
        st.stop()
