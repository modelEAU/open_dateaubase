import streamlit as st
from api_metadata.components.auth import logout

NAV = [
    ("📊 Dashboard", "dashboard"),
    ("🧾 Métadonnées", "metadata_list"),
    ("➕ Créer une métadonnée", "metadata_create"),
]

def render_sidebar(username: str) -> str:
    st.sidebar.markdown("### datEAUbase")
    st.sidebar.markdown(f"**Connecté :** {username}")

    if st.sidebar.button("Se déconnecter", use_container_width=True):
        logout()

    st.sidebar.divider()

    labels = [label for label, _ in NAV]
    values = [value for _, value in NAV]

    # ✅ persiste le choix
    default_idx = st.session_state.get("nav_idx", 0)
    choice_label = st.sidebar.radio("Navigation", labels, index=default_idx, key="nav_label")

    idx = labels.index(choice_label)
    st.session_state["nav_idx"] = idx
    return values[idx]

