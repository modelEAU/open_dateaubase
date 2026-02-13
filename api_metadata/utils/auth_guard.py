import streamlit as st

LOGIN_PAGE = "api_metadata/pages/login.py"

def require_login():
    st.session_state.setdefault("authenticated", False)
    st.session_state.setdefault("username", "")

    if not st.session_state["authenticated"]:
        st.switch_page(LOGIN_PAGE)
