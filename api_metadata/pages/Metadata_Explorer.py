import pandas as pd
import streamlit as st

from api_metadata.ui_style import apply_global_style, render_header_logos
from api_metadata.services import metadata_service as ms

def render_list():
    apply_global_style()
    render_header_logos()

    st.markdown("## 🧾 Métadonnées")
    st.caption("Explore la table `metadata` et vérifie rapidement la validité des données.")

    limit = st.slider("Nombre de lignes à afficher", 50, 500, 100, 50)
    df = ms.fetch_metadata(limit=limit)

    if df.empty:
        st.info("La table `metadata` est vide.")
        return

    df_display = df.copy()
    for col in ["StartDate", "EndDate"]:
        if col in df_display.columns:
            df_display[col] = pd.to_datetime(df_display[col], unit="s", errors="coerce", utc=True)

    st.dataframe(df_display, use_container_width=True)

def render_create():
    apply_global_style()
    render_header_logos()

    st.markdown("## ➕ Créer une métadonnée")
    st.caption("Choisis des valeurs existantes ou crée une nouvelle entrée (NEW).")

    # Fetch dropdown options
    equipments = ms.fetch_pairs("SELECT Equipment_ID, Equipment_identifier FROM equipment ORDER BY Equipment_ID")
    parameters = ms.fetch_pairs("SELECT Parameter_ID, Parameter FROM parameter ORDER BY Parameter_ID")
    units = ms.fetch_pairs("SELECT Unit_ID, Unit FROM unit ORDER BY Unit_ID")
    purposes = ms.fetch_pairs("SELECT Purpose_ID, Purpose FROM purpose ORDER BY Purpose_ID")
    projects = ms.fetch_pairs("SELECT Project_ID, Project_name FROM project ORDER BY Project_ID")
    sampling_points = ms.fetch_pairs("SELECT Sampling_point_ID, Sampling_point FROM sampling_points ORDER BY Sampling_point_ID")
    procedures = ms.fetch_pairs("SELECT Procedure_ID, Procedure_name FROM procedures ORDER BY Procedure_ID")
    contacts = ms.fetch_pairs("SELECT Contact_ID, First_name FROM contact ORDER BY Contact_ID")
    conditions = ms.fetch_pairs("SELECT Condition_ID, Weather_condition FROM weather_condition ORDER BY Condition_ID")

    def select_with_new(label, rows, new_label, key_prefix):
        options = list(rows) + [("NEW", None)]
        choice = st.selectbox(
            label,
            options,
            key=key_prefix,
            format_func=lambda x: (f"{x[0]} — {x[1]}" if x[0] != "NEW" else f"➕ {new_label}"),
        )
        new_value = None
        if choice[0] == "NEW":
            new_value = st.text_input(new_label, key=key_prefix + "_new")
        return choice, new_value

    def resolve_id(choice, new_name, table, id_col, name_col):
        if choice[0] != "NEW":
            return int(choice[0])
        return ms.create_or_get_id(table, id_col, name_col, new_name)

    st.markdown("### Identifiants")
    c1, c2 = st.columns(2)

    with c1:
        equipment_choice, equipment_new = select_with_new("Equipment", equipments, "Nouvel équipement", "equipment")
        parameter_choice, parameter_new = select_with_new("Parameter", parameters, "Nouveau paramètre", "parameter")
        unit_choice, unit_new = select_with_new("Unit", units, "Nouvelle unité", "unit")
        purpose_choice, purpose_new = select_with_new("Purpose", purposes, "Nouveau purpose", "purpose")
        project_choice, project_new = select_with_new("Project", projects, "Nouveau projet", "project")

    with c2:
        sampling_choice, sampling_new = select_with_new("Sampling point", sampling_points, "Nouveau point", "sampling")
        procedure_choice, procedure_new = select_with_new("Procedure", procedures, "Nouvelle procédure", "procedure")
        contact_choice, contact_new = select_with_new("Contact", contacts, "Nouveau contact", "contact")
        condition_choice, condition_new = select_with_new("Condition", conditions, "Nouvelle condition", "condition")

    st.markdown("### Période de validité")
    start_date = st.date_input("Start Date")
    has_end = st.checkbox("Définir une date de fin ?")
    end_date = st.date_input("End Date") if has_end else None

    st.markdown("---")
    submit = st.button("✅ Créer métadonnée", use_container_width=True)

    if submit:
        try:
            equipment_id = resolve_id(equipment_choice, equipment_new, "equipment", "Equipment_ID", "Equipment_identifier")
            parameter_id = resolve_id(parameter_choice, parameter_new, "parameter", "Parameter_ID", "Parameter")
            unit_id = resolve_id(unit_choice, unit_new, "unit", "Unit_ID", "Unit")
            purpose_id = resolve_id(purpose_choice, purpose_new, "purpose", "Purpose_ID", "Purpose")
            project_id = resolve_id(project_choice, project_new, "project", "Project_ID", "Project_name")

            sampling_point_id = resolve_id(sampling_choice, sampling_new, "sampling_points", "Sampling_point_ID", "Sampling_point")
            procedure_id = resolve_id(procedure_choice, procedure_new, "procedures", "Procedure_ID", "Procedure_name")
            contact_id = resolve_id(contact_choice, contact_new, "contact", "Contact_ID", "First_name")
            condition_id = resolve_id(condition_choice, condition_new, "weather_condition", "Condition_ID", "Weather_condition")

            new_id = ms.create_metadata(
                equipment_id=equipment_id,
                parameter_id=parameter_id,
                unit_id=unit_id,
                purpose_id=purpose_id,
                sampling_point_id=sampling_point_id,
                project_id=project_id,
                procedure_id=procedure_id,
                contact_id=contact_id,
                condition_id=condition_id,
                start_date=start_date,
                end_date=end_date,
            )

            st.success(f"Métadonnée créée 🎉 (Metadata_ID = {new_id})")

        except Exception as e:
            st.error(f"Erreur lors de la création : {e}")