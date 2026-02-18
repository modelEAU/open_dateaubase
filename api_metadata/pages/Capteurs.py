import pandas as pd
from datetime import datetime
import streamlit as st

from api_metadata.ui_style import apply_global_style, render_header_logos
from api_metadata.db import get_connection

LOGIN_PAGE = "pages/login.py"

def main():
    apply_global_style()
    render_header_logos()

    st.title("🧭 Capteurs")
    st.caption("Vue des équipements (capteurs) enregistrés dans la base.")

    search = st.text_input("Rechercher (ID ou identifiant)", placeholder="ex: 12, pH, flow, ...")

    conn = get_connection()
    df = pd.read_sql(
        """
        SELECT Equipment_ID, Equipment_identifier
        FROM equipment
        ORDER BY Equipment_ID
        """,
        conn,
    )
    conn.close()

    if df.empty:
        st.info("Aucun capteur/équipement trouvé.")
        return

    if search.strip():
        s = search.strip().lower()
        df = df[
            df["Equipment_ID"].astype(str).str.contains(s)
            | df["Equipment_identifier"].fillna("").str.lower().str.contains(s)
        ]

    st.dataframe(df, use_container_width=True)

    st.markdown("---")
    st.subheader("🔗 Liens utiles")
    st.write("Astuce : les capteurs (equipment) sont liés aux métadonnées via `Equipment_ID`.")

if __name__ == "__main__":
    main()
