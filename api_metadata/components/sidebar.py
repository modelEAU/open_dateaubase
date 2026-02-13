import streamlit as st

NAV = [
    ("📊 Dashboard", "dashboard"),
    ("🧾 Métadonnées", "metadata_list"),
    ("➕ Créer une métadonnée", "metadata_create"),
]

def render_sidebar(username: str) -> str:
    st.sidebar.markdown(f"**Connecté :** {username}")

    if st.sidebar.button("Se déconnecter"):
        st.session_state.clear()
        st.rerun()

    labels = [x[0] for x in NAV]
    values = [x[1] for x in NAV]

    choice = st.sidebar.radio("Navigation", labels, index=0)
    return values[labels.index(choice)]