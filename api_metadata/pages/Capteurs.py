import pandas as pd
import streamlit as st

from api_metadata.ui_style import apply_global_style, render_header_logos
from api_metadata.services.db_client import api_get, ApiError
from api_metadata.components.auth import ensure_auth_state, logout

LOGIN_PAGE = "pages/login.py"

def main():
    apply_global_style()
    ensure_auth_state()

    if not st.session_state.get("token"):
        st.switch_page(LOGIN_PAGE)

    try:
        api_get("/auth/me")
    except Exception:
        logout()

    render_header_logos()

    st.title("🧭 Capteurs")
    st.caption("Vue des équipements (capteurs) enregistrés dans la base.")

    search = st.text_input("Rechercher (ID ou identifiant)", placeholder="ex: 12, pH, flow, ...")

    try:
        items = api_get("/lookups/equipment")
    except ApiError as e:
        st.error(f"Impossible de charger les équipements depuis l'API. ({e})")
        return

    if not items:
        st.info("Aucun capteur/équipement trouvé.")
        return

    if search.strip():
        s = search.strip().lower()
        items = [
            it for it in items
            if s in str(it["id"]) or s in it["label"].lower()
        ]

    df = pd.DataFrame([{"Equipment_ID": it["id"], "Equipment_identifier": it["label"]} for it in items])
    st.dataframe(df, use_container_width=True)

    st.markdown("---")
    st.subheader("🔗 Liens utiles")
    st.write("Astuce : les capteurs (equipment) sont liés aux métadonnées via `Equipment_ID`.")

if __name__ == "__main__":
    main()