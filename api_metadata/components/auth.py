import streamlit as st

LOGIN_PAGE = "pages/login.py"


def ensure_auth_state():
    st.session_state.setdefault("authenticated", False)
    st.session_state.setdefault("token", None)
    st.session_state.setdefault("username", "")


def logout():
    # reset propre (sans clear total)
    for k in [
        "authenticated",
        "token",
        "username",
        "selected_metadata_id",
        "nav_idx",
        "nav_label",
    ]:
        st.session_state.pop(k, None)

    st.switch_page(LOGIN_PAGE)
