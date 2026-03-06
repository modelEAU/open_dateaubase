from __future__ import annotations

from datetime import datetime, time
import streamlit as st

from api_metadata.ui_style import apply_global_style, render_header_logos
from api_metadata.services.db_client import api_get, api_post, ApiError


def _ts_from_date(d) -> int:
    return int(datetime.combine(d, time.min).timestamp())


def _select_or_create(label: str, lookup_path: str, key: str):
    """
    Affiche un selectbox peuplé depuis l'API.
    Permet aussi de créer une nouvelle valeur lookup.
    Retourne l'id sélectionné/créé (int) ou None.
    """
    try:
        items = api_get(lookup_path)
    except ApiError as e:
        st.warning(f"Impossible de charger {label}: {e}")
        return None

    options = items + [{"id": -1, "label": "➕ Ajouter…"}]

    def _fmt(x):
        if x["id"] == -1:
            return x["label"]
        return f"{x['id']} — {x['label']}"

    choice = st.selectbox(label, options, format_func=_fmt, key=key)

    if choice["id"] != -1:
        return int(choice["id"])

    new_label = st.text_input(
        f"{label} (nouveau)",
        key=f"{key}_new",
        placeholder="Saisir le nom…",
    )

    if not new_label or not new_label.strip():
        return None

    if st.button(f"Créer : {label}", key=f"{key}_create"):
        try:
            created = api_post(lookup_path, json={"label": new_label.strip()})
            st.success(f"Créé ✅ ({created['id']} — {created['label']})")
            st.rerun()
        except ApiError as e:
            st.error(f"Erreur lors de la création : {e}")

    return None


def main():
    apply_global_style()
    st.markdown("<div class='authenticated'>", unsafe_allow_html=True)

    render_header_logos()

    st.title("➕ Créer une métadonnée")
    st.caption("Tout passe par FastAPI (UI → API → DB).")

    st.markdown("### Champs")
    col1, col2 = st.columns(2)

    with col1:
        equipment_id = _select_or_create("Équipement", "/lookups/equipment", "equipment")
        parameter_id = _select_or_create("Paramètre", "/lookups/parameter", "parameter")
        unit_id = _select_or_create("Unité", "/lookups/unit", "unit")
        purpose_id = _select_or_create("Purpose", "/lookups/purpose", "purpose")
        project_id = _select_or_create("Projet", "/lookups/project", "project")

    with col2:
        sampling_point_id = _select_or_create(
            "Point d'échantillonnage",
            "/lookups/sampling_points",
            "sampling",
        )
        procedure_id = _select_or_create("Procédure", "/lookups/procedures", "procedure")
        contact_id = _select_or_create("Contact", "/lookups/contact", "contact")
        condition_id = _select_or_create(
            "Condition météo",
            "/lookups/weather_condition",
            "condition",
        )

    st.markdown("### Période de validité")
    start_date = st.date_input("Start Date")
    has_end = st.checkbox("Définir une date de fin ?")
    end_date = st.date_input("End Date") if has_end else None

    if st.button("✅ Créer métadonnée", use_container_width=True):
        required = {
            "equipment_id": equipment_id,
            "parameter_id": parameter_id,
            "unit_id": unit_id,
            "purpose_id": purpose_id,
            "project_id": project_id,
            "sampling_point_id": sampling_point_id,
        }

        missing = [k for k, v in required.items() if v is None]
        if missing:
            st.error("Champs obligatoires manquants : " + ", ".join(missing))
            st.markdown("</div>", unsafe_allow_html=True)
            return

        payload = {
            "equipment_id": int(equipment_id),
            "parameter_id": int(parameter_id),
            "unit_id": int(unit_id),
            "purpose_id": int(purpose_id),
            "project_id": int(project_id),
            "sampling_point_id": int(sampling_point_id),
            "procedure_id": int(procedure_id) if procedure_id is not None else None,
            "contact_id": int(contact_id) if contact_id is not None else None,
            "condition_id": int(condition_id) if condition_id is not None else None,
            "start_ts": _ts_from_date(start_date),
            "end_ts": _ts_from_date(end_date) if end_date else None,
        }

        try:
            res = api_post("/metadata", json=payload)
            st.success(f"Métadonnée créée 🎉 (Metadata_ID = {res['metadata_id']})")
            st.rerun()
        except ApiError as e:
            st.error(f"Erreur API : {e}")
        except Exception as e:
            st.error(f"Erreur inattendue : {e}")

    st.markdown("</div>", unsafe_allow_html=True)


if __name__ == "__main__":
    main()