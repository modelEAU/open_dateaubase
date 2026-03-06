import requests
import streamlit as st


def ensure_auth_state():
    st.session_state.setdefault("authenticated", False)
    st.session_state.setdefault("token", None)
    st.session_state.setdefault("username", "")


def render_login(api_base_url: str):
    st.title("Connexion")

    username = st.text_input("Nom d'utilisateur")
    password = st.text_input("Mot de passe", type="password")

    if st.button("Se connecter"):
        try:
            resp = requests.post(
                f"{api_base_url}/auth/login",
                json={
                    "username": username,
                    "password": password,
                },
                timeout=10,
            )

            if resp.status_code == 200:
                data = resp.json()
                st.session_state["authenticated"] = True
                st.session_state["token"] = data["access_token"]
                st.session_state["username"] = username
                st.success("Connexion réussie")
                st.rerun()
            else:
                st.error("Identifiants invalides")
        except Exception as e:
            st.error(f"Erreur de connexion à l'API: {e}")


def logout():
    for k in [
        "authenticated",
        "token",
        "username",
        "selected_metadata_id",
        "nav_idx",
        "nav_label",
        "sensor_equipment_id_filter",
    ]:
        st.session_state.pop(k, None)

    st.rerun()