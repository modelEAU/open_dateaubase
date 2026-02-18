import pandas as pd
import streamlit as st

from api_metadata.ui_style import apply_global_style, render_header_logos
from api_metadata.services.db_client import api_get
from api_metadata.services import db_client

LOGIN_PAGE = "pages/login.py"

def _require_login():
    if not st.session_state.get("authenticated") or not st.session_state.get("token"):
        st.switch_page(LOGIN_PAGE)


def _logout():
    for k in ["authenticated", "token", "username", "selected_metadata_id"]:
        st.session_state.pop(k, None)
    st.switch_page(LOGIN_PAGE)


def main():
    _require_login()

    apply_global_style()
    st.markdown("<div class='authenticated'>", unsafe_allow_html=True)

    # Debug (tu peux l’enlever après)
    st.write("API_BASE_URL =", db_client.API_BASE_URL)

    # Sidebar logout
    if st.sidebar.button("Se déconnecter"):
        _logout()

    render_header_logos()

    st.title("📊 Tableau de bord datEAUbase")
    st.caption(f"Connecté : {st.session_state.get('username','')}")

    # ---- Filters (simple v1: IDs) ----
    st.sidebar.markdown("### Filtres (optionnel)")
    project_id = st.sidebar.text_input("Project_ID", placeholder="ex: 1")
    sampling_point_id = st.sidebar.text_input("Sampling_point_ID", placeholder="ex: 3")
    equipment_id = st.sidebar.text_input("Equipment_ID", placeholder="ex: 2")
    parameter_id = st.sidebar.text_input("Parameter_ID", placeholder="ex: 5")

    def _int_or_none(x: str):
        x = (x or "").strip()
        return int(x) if x.isdigit() else None

    params = {
        "project_id": _int_or_none(project_id),
        "sampling_point_id": _int_or_none(sampling_point_id),
        "equipment_id": _int_or_none(equipment_id),
        "parameter_id": _int_or_none(parameter_id),
    }
    params = {k: v for k, v in params.items() if v is not None}

    # ---- Load summary ----
    try:
        summary = api_get("/dashboard/summary", params=params)
    except Exception as e:
        st.error(f"Impossible de charger le dashboard (API). Détail: {e}")
        st.markdown("</div>", unsafe_allow_html=True)
        return

    c1, c2, c3 = st.columns(3)
    c1.metric("Valeurs en base", summary.get("total_values", 0))
    c2.metric("Points d’échantillonnage", summary.get("sampling_points", 0))
    c3.metric("Métadonnées actives", summary.get("active_metadata", 0))

    st.markdown("---")

    # ---- Activity 30d ----
    st.subheader("📈 Activité (30 derniers jours)")
    try:
        activity = api_get("/dashboard/activity_30d", params=params)
        df_daily = pd.DataFrame(activity)
    except Exception as e:
        st.warning(f"Impossible de charger l’activité 30j. ({e})")
        df_daily = pd.DataFrame()

    if df_daily.empty:
        st.info("Aucune valeur trouvée dans les 30 derniers jours.")
    else:
        df_daily["day"] = pd.to_datetime(df_daily["day"])
        df_daily = df_daily.sort_values("day").set_index("day")
        st.line_chart(df_daily["count"])

    # ---- Top parameters 30d ----
    st.subheader("🏷️ Répartition par paramètre (30 jours)")
    try:
        top_params = api_get("/dashboard/top_parameters_30d", params={**params, "limit": 12})
        df_param = pd.DataFrame(top_params)
    except Exception as e:
        st.warning(f"Impossible de charger la répartition par paramètre. ({e})")
        df_param = pd.DataFrame()

    if df_param.empty:
        st.info("Aucune valeur trouvée.")
    else:
        df_param = df_param.rename(columns={"parameter": "Paramètre", "count": "Nb valeurs"})
        df_param = df_param.set_index("Paramètre")
        st.bar_chart(df_param["Nb valeurs"])
        with st.expander("Voir le tableau"):
            st.dataframe(df_param.reset_index(), use_container_width=True)

    st.markdown("</div>", unsafe_allow_html=True)


if __name__ == "__main__":
    main()
