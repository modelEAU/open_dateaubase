import streamlit as st
from api_metadata.services.db_client import api_post, api_get, ApiError

def ensure_auth_state():
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False
    if "token" not in st.session_state:
        st.session_state["token"] = None
    if "username" not in st.session_state:
        st.session_state["username"] = None

def logout():
    st.session_state["authenticated"] = False
    st.session_state["token"] = None
    st.session_state["username"] = None
    st.rerun()

def render_login():
    if st.session_state.get("authenticated") and st.session_state.get("token"):
        st.info(f"Connecté en tant que **{st.session_state.get('username')}**")
        if st.button("Se déconnecter"):
            logout()
        return

    st.title("datEAUbase — Connexion")

    with st.form("login_form", clear_on_submit=False):
        username = st.text_input("Nom d’utilisateur")
        password = st.text_input("Mot de passe", type="password")
        submitted = st.form_submit_button("Se connecter")

    if not submitted:
        return

    if not username or not password:
        st.error("Veuillez remplir le nom d’utilisateur et le mot de passe.")
        return

    try:
        resp = api_post(
            "/auth/login",
            json={"username": username, "password": password},
            with_auth=False
        )
        token = resp["access_token"]

        st.session_state["authenticated"] = True
        st.session_state["token"] = token
        st.session_state["username"] = username

        _ = api_get("/auth/me")

        st.success("Connexion réussie ✅")
        st.rerun()

    except ApiError as e:
        msg = str(e)
        if msg.startswith("401:"):
            st.error("Identifiants invalides ❌")
        else:
            st.error("Erreur lors de la connexion à l’API ❌")
    except Exception:
        st.error("Erreur inattendue ❌")
