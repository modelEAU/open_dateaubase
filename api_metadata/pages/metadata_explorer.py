from __future__ import annotations

import pandas as pd
import streamlit as st

from api_metadata.ui_style import apply_global_style, render_header_logos
from api_metadata.services.db_client import api_get, ApiError
from api_metadata.components.auth import ensure_auth_state, logout

LOGIN_PAGE = "pages/login.py"


def _auth_gate():
    ensure_auth_state()
    if not st.session_state.get("authenticated") or not st.session_state.get("token"):
        st.switch_page(LOGIN_PAGE)
    try:
        api_get("/auth/me")
    except Exception:
        logout()
        st.switch_page(LOGIN_PAGE)


def render_list():
    apply_global_style()
    _auth_gate()

    st.markdown("<div class='authenticated'>", unsafe_allow_html=True)

    if st.sidebar.button("Se déconnecter"):
        st.session_state.clear()
        st.switch_page(LOGIN_PAGE)

    render_header_logos()

    st.markdown("## 🧾 Métadonnées")
    st.caption("Explore la table `metadata` et vérifie rapidement la validité des données.")

    c1, c2, c3, c4 = st.columns([1, 1, 2, 1])
    with c1:
        limit = st.slider("Nombre de lignes", 50, 1000, 200, 50)
    with c2:
        active_only = st.checkbox("Actives seulement", value=False)
    with c3:
        q = st.text_input("Recherche", placeholder="ex: pH, débit, station, …")
    with c4:
        st.button("🔄 Rafraîchir")

    params = {
        "limit": int(limit),
        "offset": 0,
        "active_only": bool(active_only),
    }
    if q and q.strip():
        params["q"] = q.strip()

    try:
        resp  = api_get("/metadata", params=params)
        items = resp.get("items", [])
        total = resp.get("total", 0)
    except ApiError as e:
        st.error(f"Impossible de charger la liste (API): {e}")
        st.markdown("</div>", unsafe_allow_html=True)
        return

    st.caption(f"Total (après filtres): **{total}**")

    if not items:
        st.info("Aucune métadonnée ne correspond aux filtres.")
        st.markdown("</div>", unsafe_allow_html=True)
        return

    rows = []
    for it in items:
        rows.append({
            "Metadata_ID":       it.get("metadata_id"),
            "Equipment":         (it.get("equipment")      or {}).get("label"),
            "Equipment_ID":      (it.get("equipment")      or {}).get("id"),
            "Parameter":         (it.get("parameter")      or {}).get("label"),
            "Parameter_ID":      (it.get("parameter")      or {}).get("id"),
            "Unit":              (it.get("unit")           or {}).get("label"),
            "Unit_ID":           (it.get("unit")           or {}).get("id"),
            "Purpose":           (it.get("purpose")        or {}).get("label"),
            "Purpose_ID":        (it.get("purpose")        or {}).get("id"),
            "Project":           (it.get("project")        or {}).get("label"),
            "Project_ID":        (it.get("project")        or {}).get("id"),
            "Sampling_point":    (it.get("sampling_point") or {}).get("label"),
            "Sampling_point_ID": (it.get("sampling_point") or {}).get("id"),
            "StartDate":         it.get("start_ts"),
            "EndDate":           it.get("end_ts"),
        })

    df = pd.DataFrame(rows)
    for col in ["StartDate", "EndDate"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], unit="s", errors="coerce", utc=True)

    st.dataframe(df, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)


def render_create():
    """Délègue à Creer_Metadata — source unique de vérité."""
    from api_metadata.pages.creer_metadata import main as _create_main
    _create_main()