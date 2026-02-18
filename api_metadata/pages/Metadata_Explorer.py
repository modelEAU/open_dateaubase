from __future__ import annotations

from datetime import datetime, time
import pandas as pd
import streamlit as st

from api_metadata.ui_style import apply_global_style, render_header_logos
from api_metadata.services.db_client import api_get, api_post, ApiError
from api_metadata.components.auth import ensure_auth_state, logout

LOGIN_PAGE = "pages/login.py"


def _ts_from_date(d) -> int:
    return int(datetime.combine(d, time.min).timestamp())


def _fmt_lookup_item(x: dict) -> str:
    # x = {"id": 1, "label": "pH"}
    return f"{x['id']} — {x['label']}"


def _select_or_add(label: str, lookup_path: str, kind: str, key: str) -> int | None:
    """
    kind: "equipment" | "parameter" | "unit" | "purpose" | "project" | "sampling_points" | "procedures" | "contact" | "weather_condition"
    lookup_path: ex "/lookups/equipment"
    """
    items = api_get(lookup_path) 
    options = items + [{"id": -1, "label": "➕ Ajouter…"}]

    choice = st.selectbox(
        label,
        options,
        key=key,
        format_func=lambda x: x["label"] if x["id"] == -1 else _fmt_lookup_item(x),
    )

    if choice["id"] != -1:
        return int(choice["id"])

    new_label = st.text_input(f"{label} (nouveau)", key=f"{key}_new", placeholder="Saisir le nom…")
    if not new_label or not new_label.strip():
        return None

    if st.button(f"Créer {label}", key=f"{key}_create"):
        created = api_post(f"/lookups/{kind}", json={"label": new_label.strip()})
        st.success(f"Créé ✅ {_fmt_lookup_item(created)}")
        st.rerun()

    return None


def render_list():
    apply_global_style()
    ensure_auth_state()

    if (not st.session_state.get("authenticated")) or (not st.session_state.get("token")):
        st.switch_page(LOGIN_PAGE)

    try:
        api_get("/auth/me")
    except Exception:
        logout()
        st.switch_page(LOGIN_PAGE)

    st.markdown("<div class='authenticated'>", unsafe_allow_html=True)

    # Sidebar logout
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
        refresh = st.button("🔄 Rafraîchir")

    params = {
        "limit": int(limit),
        "offset": 0,
        "active_only": bool(active_only),
    }
    if q and q.strip():
        params["q"] = q.strip()

    try:
        resp = api_get("/metadata", params=params)
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

    # Flatten for dataframe
    rows = []
    for it in items:
        rows.append({
            "Metadata_ID": it.get("metadata_id"),
            "Equipment": (it.get("equipment") or {}).get("label"),
            "Equipment_ID": (it.get("equipment") or {}).get("id"),
            "Parameter": (it.get("parameter") or {}).get("label"),
            "Parameter_ID": (it.get("parameter") or {}).get("id"),
            "Unit": (it.get("unit") or {}).get("label"),
            "Unit_ID": (it.get("unit") or {}).get("id"),
            "Purpose": (it.get("purpose") or {}).get("label"),
            "Purpose_ID": (it.get("purpose") or {}).get("id"),
            "Project": (it.get("project") or {}).get("label"),
            "Project_ID": (it.get("project") or {}).get("id"),
            "Sampling_point": (it.get("sampling_point") or {}).get("label"),
            "Sampling_point_ID": (it.get("sampling_point") or {}).get("id"),
            "StartDate": it.get("start_ts"),
            "EndDate": it.get("end_ts"),
        })

    df = pd.DataFrame(rows)

    for col in ["StartDate", "EndDate"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], unit="s", errors="coerce", utc=True)

    st.dataframe(df, use_container_width=True)

    st.markdown("</div>", unsafe_allow_html=True)


def render_create():
    apply_global_style()
    ensure_auth_state()

    if (not st.session_state.get("authenticated")) or (not st.session_state.get("token")):
        st.switch_page(LOGIN_PAGE)

    try:
        api_get("/auth/me")
    except Exception:
        logout()
        st.switch_page(LOGIN_PAGE)

    st.markdown("<div class='authenticated'>", unsafe_allow_html=True)

    if st.sidebar.button("Se déconnecter"):
        st.session_state.clear()
        st.switch_page(LOGIN_PAGE)

    render_header_logos()

    st.markdown("## ➕ Créer une métadonnée")
    st.caption("Choisis des valeurs existantes ou crée de nouvelles entrées (tout via l’API).")

    with st.form("create_metadata_form"):
        col1, col2 = st.columns(2)

        with col1:
            equipment_id = _select_or_add("Équipement", "/lookups/equipment", "equipment", "equipment")
            parameter_id = _select_or_add("Paramètre", "/lookups/parameter", "parameter", "parameter")
            unit_id = _select_or_add("Unité", "/lookups/unit", "unit", "unit")
            purpose_id = _select_or_add("Purpose", "/lookups/purpose", "purpose", "purpose")
            project_id = _select_or_add("Projet", "/lookups/project", "project", "project")

        with col2:
            sampling_point_id = _select_or_add("Point d’échantillonnage", "/lookups/sampling_points", "sampling_points", "sampling_points")
            procedure_id = _select_or_add("Procédure", "/lookups/procedures", "procedures", "procedures")
            contact_id = _select_or_add("Contact", "/lookups/contact", "contact", "contact")
            condition_id = _select_or_add("Condition météo", "/lookups/weather_condition", "weather_condition", "weather_condition")

        st.markdown("### Période de validité")
        start_date = st.date_input("Start Date")
        has_end = st.checkbox("Définir une date de fin ?")
        end_date = st.date_input("End Date") if has_end else None

        submit = st.form_submit_button("✅ Créer métadonnée", use_container_width=True)

    if submit:
        required = {
            "equipment_id": equipment_id,
            "parameter_id": parameter_id,
            "unit_id": unit_id,
            "purpose_id": purpose_id,
            "project_id": project_id,
            "sampling_point_id": sampling_point_id,
            "procedure_id": procedure_id,
            "contact_id": contact_id,
            "condition_id": condition_id,
        }
        missing = [k for k, v in required.items() if v is None]
        if missing:
            st.error("Champs manquants: " + ", ".join(missing))
            st.markdown("</div>", unsafe_allow_html=True)
            return

        payload = {
            **{k: int(v) for k, v in required.items()},
            "start_ts": _ts_from_date(start_date),
            "end_ts": _ts_from_date(end_date) if end_date else None,
        }

        try:
            res = api_post("/metadata", json=payload)
            st.success(f"Métadonnée créée 🎉 (Metadata_ID = {res['metadata_id']})")
            st.rerun()
        except ApiError as e:
            st.error(f"Erreur API: {e}")
        except Exception as e:
            st.error(f"Erreur inattendue: {e}")

    st.markdown("</div>", unsafe_allow_html=True)
