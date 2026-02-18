import streamlit as st

from api_metadata.ui_style import (
    apply_global_style,
    render_header_logos,
    open_login_form,
    close_login_form,
)
from api_metadata.services.db_client import api_post, api_get, ApiError

DASHBOARD_PAGE = "pages/dashboard.py"

def main():
    # état session
    st.session_state.setdefault("authenticated", False)
    st.session_state.setdefault("username", "")
    st.session_state.setdefault("token", None)

    if st.session_state.get("authenticated") and st.session_state.get("token"):
        st.switch_page(DASHBOARD_PAGE)

    apply_global_style()

    # Hide multipage sidebar/nav on login (si ton CSS l’utilise)
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
        if not username or not password:
            st.error("Veuillez remplir le nom d’utilisateur et le mot de passe.")
        else:
            try:
                # ✅ Auth via FastAPI
                resp = api_post(
                    "/auth/login",
                    json={"username": username, "password": password},
                    with_auth=False,
                )
                token = resp["access_token"]

                st.session_state["authenticated"] = True
                st.session_state["username"] = username
                st.session_state["token"] = token

                # ✅ sanity check token
                _ = api_get("/auth/me", with_auth=True)

                st.success("Connexion réussie ✅")
                st.switch_page(DASHBOARD_PAGE)

            except ApiError as e:
                msg = str(e)
                if msg.startswith("401:"):
                    st.error("Identifiants invalides ❌")
                else:
                    st.error(f"Erreur lors de la connexion à l’API ❌ ({e})")
            except Exception as e:
                st.error(f"Erreur inattendue ❌ ({e})")

    st.markdown("</div>", unsafe_allow_html=True)

if __name__ == "__main__":
    main()
