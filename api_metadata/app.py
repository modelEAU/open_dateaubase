import streamlit as st

from api_metadata.components.auth import ensure_auth_state, render_login
from api_metadata.components.sidebar import render_sidebar
from api_metadata.pages import dashboard, metadata_explorer

st.set_page_config(
    page_title="datEAUbase",
    layout="wide",
    initial_sidebar_state="expanded",
)
def main():
    ensure_auth_state()

    if not st.session_state["authenticated"]:
        render_login()
        return

    route = render_sidebar(st.session_state.get("username", ""))

    if route == "dashboard":
        dashboard.render()
    elif route == "metadata_list":
        metadata_explorer.render_list()
    elif route == "metadata_create":
        metadata_explorer.render_create()
    else:
        st.error("Page inconnue.")

if __name__ == "__main__":
    main()