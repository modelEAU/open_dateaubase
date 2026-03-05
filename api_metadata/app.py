import streamlit as st

from api_metadata.components.auth import ensure_auth_state, render_login, logout
from api_metadata.components.sidebar import render_sidebar
from api_metadata.services.db_client import api_get
from api_metadata.ui_style import apply_global_style

# ✅ Corrige: on importe depuis api_metadata/pages (les vrais fichiers)
from api_metadata.pages import dashboard
from api_metadata.pages import Metadata_Explorer as metadata_explorer  # adapte si tu renomme en minuscules


def workspace():
    try:
        api_get("/auth/me")
    except Exception:
        logout()
        st.stop()

    route = render_sidebar(st.session_state.get("username", ""))

    if route == "dashboard":
        # ⚠️ selon ton dashboard.py ça peut être main() ou render()
        if hasattr(dashboard, "render"):
            dashboard.render()
        else:
            dashboard.main()
    elif route == "metadata_list":
        metadata_explorer.render_list()
    elif route == "metadata_create":
        metadata_explorer.render_create()
    else:
        st.error("Page inconnue.")


def main():
    ensure_auth_state()
    is_auth = bool(st.session_state.get("authenticated") and st.session_state.get("token"))

    # ✅ IMPORTANT: apply_global_style doit être le SEUL endroit qui fait set_page_config
    apply_global_style(authenticated=is_auth)

    if not is_auth:
        render_login()
        st.stop()

    workspace()


if __name__ == "__main__":
    main()
