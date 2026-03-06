import pandas as pd
import streamlit as st

from api_metadata.ui_style import apply_global_style, render_header_logos
from api_metadata.services.db_client import api_get, ApiError
from api_metadata.components.auth import ensure_auth_state, logout

LOGIN_PAGE = "pages/login.py"


@st.cache_data(ttl=3600)
def _load_lookup(path: str, token: str):
    return api_get(path, with_auth=True)


def _require_login():
    ensure_auth_state()
    if not st.session_state.get("authenticated") or not st.session_state.get("token"):
        st.switch_page(LOGIN_PAGE)
    try:
        api_get("/auth/me")
    except Exception:
        logout()


def main():
    _require_login()

    apply_global_style()
    st.markdown("<div class='authenticated'>", unsafe_allow_html=True)

    if st.sidebar.button("Se déconnecter"):
        for k in ["authenticated", "token", "username", "selected_metadata_id"]:
            st.session_state.pop(k, None)
        st.switch_page(LOGIN_PAGE)

    render_header_logos()

    st.title("📊 Tableau de bord datEAUbase")
    st.caption(f"Connecté : {st.session_state.get('username', '')}")

    # ---- Filtres sidebar (dropdowns) ----
    st.sidebar.markdown("### Filtres (optionnel)")

    token = st.session_state.get("token") or ""
    try:
        eq_items = _load_lookup("/lookups/equipment",       token)
        pa_items = _load_lookup("/lookups/parameter",       token)
        pr_items = _load_lookup("/lookups/project",         token)
        sp_items = _load_lookup("/lookups/sampling_points", token)
    except ApiError:
        eq_items = pa_items = pr_items = sp_items = []

    def _options(items):
        opts    = ["Tous"]
        mapping = {"Tous": None}
        for it in items or []:
            opt = f"{it['label']} (ID: {it['id']})"
            opts.append(opt)
            mapping[opt] = it["id"]
        return opts, mapping

    eq_opts, eq_map = _options(eq_items)
    pa_opts, pa_map = _options(pa_items)
    pr_opts, pr_map = _options(pr_items)
    sp_opts, sp_map = _options(sp_items)

    eq_choice = st.sidebar.selectbox("Équipement",               eq_opts, index=0)
    pa_choice = st.sidebar.selectbox("Paramètre",                pa_opts, index=0)
    pr_choice = st.sidebar.selectbox("Projet",                   pr_opts, index=0)
    sp_choice = st.sidebar.selectbox("Point d'échantillonnage",  sp_opts, index=0)

    params = {k: v for k, v in {
        "equipment_id":      eq_map.get(eq_choice),
        "parameter_id":      pa_map.get(pa_choice),
        "project_id":        pr_map.get(pr_choice),
        "sampling_point_id": sp_map.get(sp_choice),
    }.items() if v is not None}

    # ---- KPIs ----
    try:
        summary = api_get("/dashboard/summary", params=params)
    except Exception as e:
        st.error(f"Impossible de charger le dashboard (API). Détail: {e}")
        st.markdown("</div>", unsafe_allow_html=True)
        return

    c1, c2, c3 = st.columns(3)
    c1.metric("Valeurs en base",          summary.get("total_values", 0))
    c2.metric("Points d'échantillonnage", summary.get("sampling_points", 0))
    c3.metric("Métadonnées actives",      summary.get("active_metadata", 0))

    st.markdown("---")

    # ---- Activity 30d ----
    st.subheader("📈 Activité (30 derniers jours)")
    try:
        activity = api_get("/dashboard/activity_30d", params=params)
        df_daily = pd.DataFrame(activity)
    except Exception as e:
        st.warning(f"Impossible de charger l'activité 30j. ({e})")
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
        df_param   = pd.DataFrame(top_params)
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
    