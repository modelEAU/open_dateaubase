import os
import streamlit as st
from api_metadata.ui_style import (
    apply_global_style,
    render_header_logos,
    open_login_form,
    close_login_form,
)

USERS = {
    "admin": os.getenv("UI_ADMIN_PASSWORD", "admin123"),
    "user": os.getenv("UI_USER_PASSWORD", "user123"),
}

DASHBOARD_PAGE = "api_metadata/pages/dashboard.py"

def check_credentials(username: str, password: str) -> bool:
    return username in USERS and USERS[username] == password

def main():
    st.session_state.setdefault("authenticated", False)
    st.session_state.setdefault("username", "")

    # If already logged in, go straight to app
    if st.session_state["authenticated"]:
        st.switch_page(DASHBOARD_PAGE)

    apply_global_style()

    # Hide multipage sidebar/nav on login
    st.markdown("<div class='unauthenticated'>", unsafe_allow_html=True)

    render_header_logos()
    open_login_form()

    st.markdown("<div class='ui-login-wrap'>", unsafe_allow_html=True)
    st.markdown("<div class='ui-login-title'>datEAUbase – Connexion</div>", unsafe_allow_html=True)
    st.markdown("<div class='ui-login-sub'>Accès sécurisé à l’interface de métadonnées.</div>", unsafe_allow_html=True)

    username = st.text_input("Nom d’utilisateur")
    password = st.text_input("Mot de passe", type="password")

    st.markdown("<div class='ui-btn-green'>", unsafe_allow_html=True)
    login_btn = st.button("Se connecter", use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)
    close_login_form()

    if login_btn:
        if check_credentials(username, password):
            st.session_state["authenticated"] = True
            st.session_state["username"] = username
            st.success("Connexion réussie ✅")
            st.switch_page(DASHBOARD_PAGE)
        else:
            st.error("Identifiants invalides ❌")

    st.markdown("</div>", unsafe_allow_html=True)

if __name__ == "__main__":
    main()
