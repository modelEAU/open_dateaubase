# api_metadata/workspace_pages/metadata_list.py  (ou ton chemin actuel)
import pandas as pd
import streamlit as st

from api_metadata.ui_style import apply_global_style, render_header_logos
from api_metadata.services.db_client import api_get, ApiError

LOGIN_PAGE = "pages/login.py"



def _to_dt(ts):
    if ts is None:
        return None
    try:
        return pd.to_datetime(int(ts), unit="s", utc=True)
    except Exception:
        return None


@st.cache_data(ttl=3600)
def _load_lookup(path: str, token: str):
    """
    token est volontairement un paramètre pour que le cache varie
    selon l'utilisateur / session (évite de garder un 401 en cache).
    """
    return api_get(path, with_auth=True)


def _options(items):
    opts = ["Tous"]
    mapping = {"Tous": None}

    for it in items or []:
        # Supporte {"id":..., "label":...} et variantes
        label = it.get("label") or it.get("name") or str(it.get("id"))
        opt = f"{label} (ID: {it['id']})"
        opts.append(opt)
        mapping[opt] = it["id"]

    return opts, mapping

def main():
    if not st.session_state.get("token"):
        st.switch_page("pages/login.py")


    apply_global_style()
    st.markdown("<div class='authenticated'>", unsafe_allow_html=True)

    # Sidebar logout
    if st.sidebar.button("Se déconnecter"):
        st.session_state.clear()
        st.switch_page(LOGIN_PAGE)

    render_header_logos()

    st.title("🧾 Liste des métadonnées")
    st.caption("Recherche, filtres, et affichage lisible (via FastAPI).")

    # --- Lookups ---
    token = st.session_state.get("token") or ""
    try:
        equipment = _load_lookup("/lookups/equipment", token)
        parameters = _load_lookup("/lookups/parameter", token)
        projects = _load_lookup("/lookups/project", token)
        sampling_points = _load_lookup("/lookups/sampling_points", token)
    except ApiError as e:
        st.error("Impossible de charger les listes (lookups). Vérifie l’API.")
        st.caption(str(e))
        if str(e).startswith("401:"):
            st.info("Ton token est absent/expiré → reconnecte-toi.")
            st.session_state.clear()
            st.switch_page(LOGIN_PAGE)
        st.markdown("</div>", unsafe_allow_html=True)
        return
    except Exception as e:
        st.error("Impossible de charger les listes (lookups).")
        st.caption(str(e))
        st.markdown("</div>", unsafe_allow_html=True)
        return

    eq_opts, eq_map = _options(equipment)
    pa_opts, pa_map = _options(parameters)
    pr_opts, pr_map = _options(projects)
    sp_opts, sp_map = _options(sampling_points)

    # --- UI Filters ---
    with st.container():
        c1, c2, c3, c4 = st.columns([1, 1, 1, 1])
        with c1:
            q = st.text_input("Recherche", placeholder="pH, débit, Roma, station…")
        with c2:
            equipment_choice = st.selectbox("Équipement", eq_opts, index=0)
        with c3:
            parameter_choice = st.selectbox("Paramètre", pa_opts, index=0)
        with c4:
            project_choice = st.selectbox("Projet", pr_opts, index=0)

        c5, c6, c7, c8 = st.columns([1, 1, 1, 1])
        with c5:
            sampling_choice = st.selectbox("Point d’échantillonnage", sp_opts, index=0)
        with c6:
            active_only = st.checkbox("Actives seulement", value=False)
        with c7:
            limit = st.selectbox("Lignes par page", [50, 100, 200, 500], index=2)
        with c8:
            page = st.number_input("Page", min_value=1, value=1, step=1)

        a1, a2 = st.columns([1, 1])
        with a1:
            st.button("✅ Appliquer", use_container_width=True)  # optionnel
        with a2:
            if st.button("♻️ Réinitialiser", use_container_width=True):
                st.rerun()

    offset = (int(page) - 1) * int(limit)

    params = {
        "limit": int(limit),
        "offset": int(offset),
        "active_only": bool(active_only),
    }

    eq_id = eq_map.get(equipment_choice)
    pa_id = pa_map.get(parameter_choice)
    pr_id = pr_map.get(project_choice)
    sp_id = sp_map.get(sampling_choice)

    if q and q.strip():
        params["q"] = q.strip()
    if eq_id is not None:
        params["equipment_id"] = int(eq_id)
    if pa_id is not None:
        params["parameter_id"] = int(pa_id)
    if pr_id is not None:
        params["project_id"] = int(pr_id)
    if sp_id is not None:
        params["sampling_point_id"] = int(sp_id)

    # --- Fetch metadata ---
    try:
        resp = api_get("/metadata", params=params, with_auth=True)
    except ApiError as e:
        st.error(f"Erreur lors du chargement des métadonnées depuis l’API. Détail: {e}")
        if str(e).startswith("401:"):
            st.info("Ton token est absent/expiré → reconnecte-toi.")
            st.session_state.clear()
            st.switch_page(LOGIN_PAGE)
        st.markdown("</div>", unsafe_allow_html=True)
        return
    except Exception as e:
        st.error(f"Erreur lors du chargement des métadonnées depuis l’API. Détail: {e}")
        st.markdown("</div>", unsafe_allow_html=True)
        return

    total = resp.get("total", 0)
    items = resp.get("items", [])

    if total == 0 or not items:
        st.info("Aucune métadonnée ne correspond aux filtres.")
        st.markdown("</div>", unsafe_allow_html=True)
        return

    st.caption(f"Résultats: **{total}** (page {page})")

    rows = []
    for it in items:
        rows.append(
            {
                "Metadata_ID": it.get("metadata_id"),
                "Equipment": (it.get("equipment") or {}).get("label"),
                "Equipment_ID": (it.get("equipment") or {}).get("id"),
                "Parameter": (it.get("parameter") or {}).get("label"),
                "Parameter_ID": (it.get("parameter") or {}).get("id"),
                "Unit": (it.get("unit") or {}).get("label"),
                "Unit_ID": (it.get("unit") or {}).get("id"),
                "Project": (it.get("project") or {}).get("label"),
                "Project_ID": (it.get("project") or {}).get("id"),
                "Sampling_point": (it.get("sampling_point") or {}).get("label"),
                "Sampling_point_ID": (it.get("sampling_point") or {}).get("id"),
                "StartDate": _to_dt(it.get("start_ts")),
                "EndDate": _to_dt(it.get("end_ts")),
            }
        )

    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)

    st.markdown("### Ouvrir une métadonnée")
    selected = st.selectbox(
        "Choisir une Metadata_ID à explorer",
        df["Metadata_ID"].dropna().astype(int).tolist(),
    )
    if st.button("🔍 Ouvrir dans Metadata Explorer", use_container_width=True):
        st.session_state["selected_metadata_id"] = int(selected)
        st.rerun()

    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button(
        "⬇️ Exporter CSV (page actuelle)",
        data=csv,
        file_name="metadata_page.csv",
        mime="text/csv",
        use_container_width=True,
    )

    st.markdown("</div>", unsafe_allow_html=True)


if __name__ == "__main__":
    main()
