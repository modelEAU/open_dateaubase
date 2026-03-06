import pandas as pd
import streamlit as st

from api_metadata.ui_style import apply_global_style, render_header_logos
from api_metadata.services.db_client import api_get, ApiError


def main():
    apply_global_style()
    st.markdown("<div class='authenticated'>", unsafe_allow_html=True)

    render_header_logos()

    st.title("🧭 Capteurs")
    st.caption("Vue des équipements (capteurs) enregistrés dans la base.")

    search = st.text_input(
        "Rechercher (ID ou identifiant)",
        placeholder="ex: 12, pH, flow, ...",
    )

    try:
        items = api_get("/lookups/equipment")
    except ApiError as e:
        st.error(f"Impossible de charger les équipements depuis l'API. ({e})")
        st.markdown("</div>", unsafe_allow_html=True)
        return
    except Exception as e:
        st.error(f"Erreur inattendue lors du chargement des équipements. ({e})")
        st.markdown("</div>", unsafe_allow_html=True)
        return

    if not items:
        st.info("Aucun capteur/équipement trouvé.")
        st.markdown("</div>", unsafe_allow_html=True)
        return

    if search.strip():
        s = search.strip().lower()
        items = [
            it for it in items
            if s in str(it["id"]) or s in (it["label"] or "").lower()
        ]

    if not items:
        st.info("Aucun capteur ne correspond à la recherche.")
        st.markdown("</div>", unsafe_allow_html=True)
        return

    df = pd.DataFrame(
        [
            {
                "Equipment_ID": it["id"],
                "Equipment_identifier": it["label"],
            }
            for it in items
        ]
    )

    st.dataframe(df, use_container_width=True, hide_index=True)

    st.markdown("---")
    st.subheader("🔗 Liens utiles")
    st.write("Astuce : les capteurs (equipment) sont liés aux métadonnées via `Equipment_ID`.")

    selected = st.selectbox(
        "Choisir un capteur",
        df["Equipment_ID"].astype(int).tolist(),
    )

    if st.button("Voir les métadonnées liées", use_container_width=True):
        st.session_state["sensor_equipment_id_filter"] = int(selected)
        st.session_state["nav_idx"] = 1
        st.session_state["nav_label"] = "🧾 Métadonnées"
        st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)


if __name__ == "__main__":
    main()