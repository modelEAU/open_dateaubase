from datetime import datetime
import streamlit as st

from api_metadata.utils.auth_guard import require_login
from api_metadata.ui_style import apply_global_style, render_header_logos
from api_metadata.db import get_connection

LOGIN_PAGE = "api_metadata/pages/login.py"

def main():
    require_login()
    apply_global_style()

    st.markdown("<div class='authenticated'>", unsafe_allow_html=True)

    # Sidebar logout
    if st.sidebar.button("Se déconnecter"):
        st.session_state.clear()
        st.switch_page(LOGIN_PAGE)

    render_header_logos()

    st.title("➕ Créer une métadonnée")
    st.caption("Choisis une valeur existante ou sélectionne ➕ pour créer une nouvelle entrée (créée en base).")

    conn = get_connection()
    cur = conn.cursor()

    def fetch_pairs(query: str):
        cur.execute(query)
        return cur.fetchall()

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
            new_value = st.text_input(new_label, key=key_prefix + "_new", placeholder="Saisir le nom…")
        return choice, new_value

    def ensure_id(choice, new_name, table, id_col, name_col):
        # Existing
        if choice[0] != "NEW":
            return int(choice[0])

        # New required
        if not new_name or not new_name.strip():
            raise ValueError(f"Le champ '{name_col}' est obligatoire quand tu choisis 'nouveau'.")

        name_value = new_name.strip()

        # If exists already, reuse it
        cur.execute(f"SELECT {id_col} FROM {table} WHERE {name_col} = ?", name_value)
        row = cur.fetchone()
        if row:
            return int(row[0])

        # Otherwise create new id
        cur.execute(f"SELECT ISNULL(MAX({id_col}), 0) FROM {table}")
        max_id = int(cur.fetchone()[0] or 0)
        new_id = max_id + 1

        cur.execute(
            f"INSERT INTO {table} ({id_col}, {name_col}) VALUES (?, ?)",
            (new_id, name_value),
        )

        return new_id

    # ---------- Load options ----------
    equipments = fetch_pairs("SELECT Equipment_ID, Equipment_identifier FROM equipment ORDER BY Equipment_ID")
    parameters = fetch_pairs("SELECT Parameter_ID, Parameter FROM parameter ORDER BY Parameter_ID")
    units = fetch_pairs("SELECT Unit_ID, Unit FROM unit ORDER BY Unit_ID")
    purposes = fetch_pairs("SELECT Purpose_ID, Purpose FROM purpose ORDER BY Purpose_ID")
    projects = fetch_pairs("SELECT Project_ID, Project_name FROM project ORDER BY Project_ID")
    sampling_points = fetch_pairs("SELECT Sampling_point_ID, Sampling_point FROM sampling_points ORDER BY Sampling_point_ID")
    procedures = fetch_pairs("SELECT Procedure_ID, Procedure_name FROM procedures ORDER BY Procedure_ID")
    contacts = fetch_pairs("SELECT Contact_ID, First_name FROM contact ORDER BY Contact_ID")
    conditions = fetch_pairs("SELECT Condition_ID, Weather_condition FROM weather_condition ORDER BY Condition_ID")

    # ---------- Form ----------
    with st.form("create_metadata_form", clear_on_submit=False):
        col1, col2 = st.columns(2)

        with col1:
            equipment_choice, equipment_new = select_with_new(
                "Équipement", equipments, "Ajouter un nouvel équipement", "equipment"
            )
            parameter_choice, parameter_new = select_with_new(
                "Paramètre", parameters, "Ajouter un nouveau paramètre", "parameter"
            )
            unit_choice, unit_new = select_with_new(
                "Unité", units, "Ajouter une nouvelle unité", "unit"
            )
            purpose_choice, purpose_new = select_with_new(
                "Purpose", purposes, "Ajouter un nouveau purpose", "purpose"
            )
            project_choice, project_new = select_with_new(
                "Projet", projects, "Ajouter un nouveau projet", "project"
            )

        with col2:
            sampling_choice, sampling_new = select_with_new(
                "Point d’échantillonnage", sampling_points, "Ajouter un nouveau point", "sampling"
            )
            procedure_choice, procedure_new = select_with_new(
                "Procédure", procedures, "Ajouter une nouvelle procédure", "procedure"
            )
            contact_choice, contact_new = select_with_new(
                "Contact", contacts, "Ajouter un nouveau contact", "contact"
            )
            condition_choice, condition_new = select_with_new(
                "Condition météo", conditions, "Ajouter une nouvelle condition", "condition"
            )

        st.markdown("### Période de validité")
        start_date = st.date_input("Start Date")
        has_end = st.checkbox("Définir une date de fin ?")
        end_date = st.date_input("End Date") if has_end else None

        submit = st.form_submit_button("✅ Créer métadonnée", use_container_width=True)

    # ---------- Submit ----------
    if submit:
        try:
            # 1) Resolve/create referenced IDs
            equipment_id = ensure_id(equipment_choice, equipment_new, "equipment", "Equipment_ID", "Equipment_identifier")
            parameter_id = ensure_id(parameter_choice, parameter_new, "parameter", "Parameter_ID", "Parameter")
            unit_id = ensure_id(unit_choice, unit_new, "unit", "Unit_ID", "Unit")
            purpose_id = ensure_id(purpose_choice, purpose_new, "purpose", "Purpose_ID", "Purpose")
            project_id = ensure_id(project_choice, project_new, "project", "Project_ID", "Project_name")

            sampling_point_id = ensure_id(sampling_choice, sampling_new, "sampling_points", "Sampling_point_ID", "Sampling_point")
            procedure_id = ensure_id(procedure_choice, procedure_new, "procedures", "Procedure_ID", "Procedure_name")
            contact_id = ensure_id(contact_choice, contact_new, "contact", "Contact_ID", "First_name")
            condition_id = ensure_id(condition_choice, condition_new, "weather_condition", "Condition_ID", "Weather_condition")

            # ✅ Commit here so newly created rows are real before inserting metadata (avoids FK edge cases)
            conn.commit()

            # 2) Create metadata row
            cur.execute("SELECT ISNULL(MAX(Metadata_ID), 0) FROM metadata")
            new_metadata_id = int(cur.fetchone()[0] or 0) + 1

            start_ts = int(datetime.combine(start_date, datetime.min.time()).timestamp())
            end_ts = int(datetime.combine(end_date, datetime.min.time()).timestamp()) if end_date else None

            cur.execute(
                """
                INSERT INTO metadata
                (Metadata_ID,
                 Parameter_ID, Unit_ID, Purpose_ID,
                 Equipment_ID, Procedure_ID, Condition_ID,
                 Sampling_point_ID, Contact_ID, Project_ID,
                 StartDate, EndDate)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    new_metadata_id,
                    parameter_id,
                    unit_id,
                    purpose_id,
                    equipment_id,
                    procedure_id,
                    condition_id,
                    sampling_point_id,
                    contact_id,
                    project_id,
                    start_ts,
                    end_ts,
                ),
            )

            conn.commit()
            st.success(f"Métadonnée créée 🎉 (Metadata_ID = {new_metadata_id})")

            # ✅ Refresh page so dropdowns include any NEW items just created
            st.rerun()

        except Exception as e:
            conn.rollback()
            st.error(f"Erreur : {e}")

    cur.close()
    conn.close()

    st.markdown("</div>", unsafe_allow_html=True)

if __name__ == "__main__":
    main()
