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
        logout()  # ✅ reset propre + rerun

    st.sidebar.divider()

    labels = [label for label, _ in NAV]
    values = [value for _, value in NAV]

    choice_label = st.sidebar.radio("Navigation", labels, index=0)
    return values[labels.index(choice_label)]
