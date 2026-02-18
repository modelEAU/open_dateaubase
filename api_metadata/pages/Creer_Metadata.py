from __future__ import annotations

from datetime import datetime, time
import streamlit as st

from api_metadata.ui_style import apply_global_style, render_header_logos
from api_metadata.components.auth import ensure_auth_state, logout
from api_metadata.services.db_client import api_get, api_post, ApiError

LOGIN_PAGE = "pages/login.py"



def _ts_from_date(d) -> int:
    return int(datetime.combine(d, time.min).timestamp())


def _select_or_create(label: str, lookup_path: str, create_path: str, key: str):
    """
    lookup_path: ex "/lookups/equipment"
    create_path: ex "/lookups/equipment"
    Retourne l'id choisi/créé (int) ou None si aucune option.
    """
    # Charge la liste depuis l'API
    items = api_get(lookup_path)  # [{id, label}, ...]
    options = items + [{"id": -1, "label": "➕ Ajouter…"}]

    def _fmt(x):
        if x["id"] == -1:
            return x["label"]
        return f'{x["id"]} — {x["label"]}'

    choice = st.selectbox(label, options, format_func=_fmt, key=key)

    if choice["id"] != -1:
        return int(choice["id"])

    new_label = st.text_input(f"{label} (nouveau)", key=f"{key}_new", placeholder="Saisir le nom…")
    if not new_label or not new_label.strip():
        return None

    if st.button(f"Créer: {label}", key=f"{key}_create"):
        created = api_post(create_path, json={"label": new_label.strip()})
        st.success(f"Créé ✅ ({created['id']} — {created['label']})")
        st.rerun()

    return None


def main():
    apply_global_style()
    ensure_auth_state()

    # Auth gate
    if (not st.session_state.get("authenticated")) or (not st.session_state.get("token")):
        st.switch_page(LOGIN_PAGE)

    # Token still valid?
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

    st.title("➕ Créer une métadonnée")
    st.caption("Tout passe par FastAPI (UI → API → DB).")

    # --- Form ---
    with st.form("create_metadata_form", clear_on_submit=False):
        col1, col2 = st.columns(2)

        with col1:
            equipment_id = _select_or_create(
                "Équipement", "/lookups/equipment", "/lookups/equipment", "equipment"
            )
            parameter_id = _select_or_create(
                "Paramètre", "/lookups/parameter", "/lookups/parameter", "parameter"
            )
            unit_id = _select_or_create(
                "Unité", "/lookups/unit", "/lookups/unit", "unit"
            )
            purpose_id = _select_or_create(
                "Purpose", "/lookups/purpose", "/lookups/purpose", "purpose"
            )
            project_id = _select_or_create(
                "Projet", "/lookups/project", "/lookups/project", "project"
            )

        with col2:
            sampling_point_id = _select_or_create(
                "Point d’échantillonnage", "/lookups/sampling_points", "/lookups/sampling_points", "sampling"
            )
            procedure_id = _select_or_create(
                "Procédure", "/lookups/procedures", "/lookups/procedures", "procedure"
            )
            contact_id = _select_or_create(
                "Contact", "/lookups/contact", "/lookups/contact", "contact"
            )
            condition_id = _select_or_create(
                "Condition météo", "/lookups/weather_condition", "/lookups/weather_condition", "condition"
            )

        st.markdown("### Période de validité")
        start_date = st.date_input("Start Date")
        has_end = st.checkbox("Définir une date de fin ?")
        end_date = st.date_input("End Date") if has_end else None

        submit = st.form_submit_button("✅ Créer métadonnée", use_container_width=True)

    if submit:
        # Validate required ids
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
            st.error("Champs manquants (crée/choisis une valeur) : " + ", ".join(missing))
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


if __name__ == "__main__":
    main()
