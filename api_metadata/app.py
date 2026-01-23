import os
from datetime import datetime

import streamlit as st
import pandas as pd

from db import get_connection
from ui_style import (
    apply_global_style,
    render_header_logos,
    open_login_form,
    close_login_form,
)




USERS = {
    "admin": os.getenv("UI_ADMIN_PASSWORD", "admin123"),
    "user": os.getenv("UI_USER_PASSWORD", "user123"),
}


def check_credentials(username: str, password: str) -> bool:
    return username in USERS and USERS[username] == password


def page_login():
    apply_global_style()
    render_header_logos()

    open_login_form()

    st.markdown("<div class='ui-login-wrap'>", unsafe_allow_html=True)
    st.markdown("<div class='ui-login-title'>datEAUbase – Connexion</div>", unsafe_allow_html=True)
    st.markdown("<div class='ui-login-sub'>Accès sécurisé à l’interface de métadonnées.</div>", unsafe_allow_html=True)

    username = st.text_input("Nom d’utilisateur")
    password = st.text_input("Mot de passe", type="password")

    st.markdown("<div class='ui-btn-green'>", unsafe_allow_html=True)
    login_btn = st.button("Se connecter", use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)  
    close_login_form()

    if login_btn:
        if check_credentials(username, password):
            st.session_state["authenticated"] = True
            st.session_state["username"] = username
            st.success("Connexion réussie ✅")
            st.rerun()
        else:
            st.error("Identifiants invalides ❌")



def page_metadata_list():
    apply_global_style()
    st.title("Liste des métadonnées")
    st.write("Affichage des lignes de la table `metadata`.")

    try:
        conn = get_connection()
    except Exception as e:
        st.error("Impossible de se connecter à la base de données 😢\n\n" f"Détail : {e}")
        return

    query = """
        SELECT TOP 100
            Metadata_ID,
            Parameter_ID,
            Unit_ID,
            Purpose_ID,
            Equipment_ID,
            Procedure_ID,
            Condition_ID,
            Sampling_point_ID,
            Contact_ID,
            Project_ID,
            StartDate,
            EndDate
        FROM metadata
        ORDER BY Metadata_ID
    """

    try:
        df = pd.read_sql(query, conn)
    except Exception as e:
        conn.close()
        st.error("Erreur lors de la lecture de la table `metadata` \n\n" f"Détail : {e}")
        return
    finally:
        conn.close()

    if df.empty:
        st.info("La table `metadata` est vide pour l’instant.")
        return

    df_display = df.copy()
    df_display.index = df_display.index + 1
    df_display.index.name = "#"

    # Convertir timestamps unix -> datetime UTC (affichage)
    for col in ["StartDate", "EndDate"]:
        if col in df_display.columns:
            df_display[col] = pd.to_datetime(df_display[col], unit="s", errors="coerce", utc=True)

    st.dataframe(df_display, use_container_width=True)


def page_create_metadata():
    apply_global_style()
    st.title("Créer une métadonnée")

    st.write(
        "Formulaire avec menus déroulants : tu peux choisir une valeur existante "
        "ou créer une nouvelle entrée si elle n'existe pas encore."
    )

    try:
        conn = get_connection()
        cur = conn.cursor()
    except Exception as e:
        st.error("Impossible de se connecter à la base de données 😢\n\n" f"Détail : {e}")
        return

    # ---- helpers ----
    def fetch_pairs(query: str):
        cur.execute(query)
        return cur.fetchall()

    def select_with_new(label, rows, new_label, key_prefix):
        options = list(rows) + [("NEW", None)]
        choice = st.selectbox(
            label,
            options,
            key=key_prefix,
            format_func=lambda x: (f"{x[0]} – {x[1]}" if x[0] != "NEW" else f"➕ {new_label}"),
        )
        new_value = None
        if choice[0] == "NEW":
            new_value = st.text_input(new_label, key=key_prefix + "_new")
        return choice, new_value

    def ensure_id(choice, new_name, table, id_col, name_col):
        if choice[0] != "NEW":
            return int(choice[0])

        if not new_name or not new_name.strip():
            raise ValueError(f"Le champ '{name_col}' est obligatoire quand tu choisis 'nouveau'.")

        name_value = new_name.strip()

        cur.execute(f"SELECT {id_col} FROM {table} WHERE {name_col} = ?", name_value)
        row = cur.fetchone()
        if row:
            return row[0]

        cur.execute(f"SELECT ISNULL(MAX({id_col}), 0) FROM {table}")
        max_id = cur.fetchone()[0]
        new_id = max_id + 1

        cur.execute(
            f"INSERT INTO {table} ({id_col}, {name_col}) VALUES (?, ?)",
            (new_id, name_value),
        )
        return new_id

    equipments = fetch_pairs("SELECT Equipment_ID, Equipment_identifier FROM equipment ORDER BY Equipment_ID")
    parameters = fetch_pairs("SELECT Parameter_ID, Parameter FROM parameter ORDER BY Parameter_ID")
    units = fetch_pairs("SELECT Unit_ID, Unit FROM unit ORDER BY Unit_ID")
    purposes = fetch_pairs("SELECT Purpose_ID, Purpose FROM purpose ORDER BY Purpose_ID")
    projects = fetch_pairs("SELECT Project_ID, Project_name FROM project ORDER BY Project_ID")
    sampling_points = fetch_pairs("SELECT Sampling_point_ID, Sampling_point FROM sampling_points ORDER BY Sampling_point_ID")
    procedures = fetch_pairs("SELECT Procedure_ID, Procedure_name FROM procedures ORDER BY Procedure_ID")
    contacts = fetch_pairs("SELECT Contact_ID, First_name FROM contact ORDER BY Contact_ID")
    conditions = fetch_pairs("SELECT Condition_ID, Weather_condition FROM weather_condition ORDER BY Condition_ID")

    col1, col2 = st.columns(2)

    with col1:
        equipment_choice, equipment_new = select_with_new("Equipment_ID", equipments, "Nom du nouvel équipement", "equipment")
        parameter_choice, parameter_new = select_with_new("Parameter_ID", parameters, "Nom du nouveau paramètre", "parameter")
        unit_choice, unit_new = select_with_new("Unit_ID", units, "Nom de la nouvelle unité", "unit")
        purpose_choice, purpose_new = select_with_new("Purpose_ID", purposes, "Nom du nouveau purpose", "purpose")
        project_choice, project_new = select_with_new("Project_ID", projects, "Nom du nouveau projet", "project")

    with col2:
        sampling_choice, sampling_new = select_with_new("Sampling_point_ID", sampling_points, "Nom du nouveau point d'échantillonnage", "sampling")
        procedure_choice, procedure_new = select_with_new("Procedure_ID", procedures, "Nom de la nouvelle procédure", "procedure")
        contact_choice, contact_new = select_with_new("Contact_ID", contacts, "Nom du nouveau contact", "contact")
        condition_choice, condition_new = select_with_new("Condition_ID", conditions, "Nouvelle condition météo", "condition")

    start_date = st.date_input("Start Date")
    has_end = st.checkbox("Définir une date de fin ?")
    end_date = st.date_input("End Date") if has_end else None

    submit = st.button("Créer métadonnée", use_container_width=True)

    if submit:
        try:
            equipment_id = ensure_id(equipment_choice, equipment_new, "equipment", "Equipment_ID", "Equipment_identifier")
            parameter_id = ensure_id(parameter_choice, parameter_new, "parameter", "Parameter_ID", "Parameter")
            unit_id = ensure_id(unit_choice, unit_new, "unit", "Unit_ID", "Unit")
            purpose_id = ensure_id(purpose_choice, purpose_new, "purpose", "Purpose_ID", "Purpose")
            project_id = ensure_id(project_choice, project_new, "project", "Project_ID", "Project_name")

            sampling_point_id = ensure_id(sampling_choice, sampling_new, "sampling_points", "Sampling_point_ID", "Sampling_point")
            procedure_id = ensure_id(procedure_choice, procedure_new, "procedures", "Procedure_ID", "Procedure_name")
            contact_id = ensure_id(contact_choice, contact_new, "contact", "Contact_ID", "First_name")
            condition_id = ensure_id(condition_choice, condition_new, "weather_condition", "Condition_ID", "Weather_condition")

            cur.execute("SELECT ISNULL(MAX(Metadata_ID), 0) FROM metadata")
            max_meta = cur.fetchone()[0]
            new_metadata_id = max_meta + 1

            start_dt = datetime.combine(start_date, datetime.min.time())
            start_ts = int(start_dt.timestamp())

            if end_date:
                end_dt = datetime.combine(end_date, datetime.min.time())
                end_ts = int(end_dt.timestamp())
            else:
                end_ts = None

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
            
            st.success(f"Nouvelle métadonnée créée avec succès 🎉 (Metadata_ID = {new_metadata_id})")

        except ValueError as ve:
            st.error(str(ve))
        except Exception as e:
            conn.rollback()
            st.error("Erreur lors de la création de la métadonnée 😢\n\n" f"Détail : {e}")

    cur.close()
    conn.close()


def page_dashboard():
    apply_global_style()
    st.title("Tableau de bord datEAUbase")

    try:
        conn = get_connection()
        cur = conn.cursor()
    except Exception as e:
        st.error("Impossible de se connecter à la base de données 😢\n\n" f"Détail : {e}")
        return

    cur.execute("SELECT COUNT(*) FROM value")
    total_values = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM sampling_points")
    total_sampling_points = cur.fetchone()[0]

    now_unix = int(datetime.utcnow().timestamp())
    cur.execute(
        """
        SELECT COUNT(*)
        FROM metadata
        WHERE StartDate <= ?
        AND (EndDate IS NULL OR EndDate > ?)
        """,
        (now_unix, now_unix),
    )
    active_metadata = cur.fetchone()[0]

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Valeurs en base", total_values)
    with col2:
        st.metric("Points d'échantillonnage", total_sampling_points)
    with col3:
        st.metric("Métadonnées actives", active_metadata)

    st.markdown("---")

    st.subheader("Activité sur les 30 derniers jours")

    query_daily = """
        SELECT
            CAST(DATEADD(SECOND, v.[Timestamp], '19700101') AS date) AS jour,
            COUNT(*) AS nb_valeurs
        FROM value v
        WHERE DATEADD(SECOND, v.[Timestamp], '19700101')
        >= DATEADD(DAY, -30, GETUTCDATE())
        GROUP BY CAST(DATEADD(SECOND, v.[Timestamp], '19700101') AS date)
        ORDER BY jour
    """
    df_daily = pd.read_sql(query_daily, conn)

    if df_daily.empty:
        st.info("Aucune valeur trouvée dans les 30 derniers jours.")
    else:
        df_daily.set_index("jour", inplace=True)
        st.line_chart(df_daily["nb_valeurs"])

    st.subheader("Répartition par paramètre (30 derniers jours)")

    query_param = """
        SELECT
            m.Parameter_ID,
            COUNT(*) AS nb_valeurs
        FROM value v
        JOIN metadata m ON v.Metadata_ID = m.Metadata_ID
        WHERE DATEADD(SECOND, v.[Timestamp], '19700101')
        >= DATEADD(DAY, -30, GETUTCDATE())
        GROUP BY m.Parameter_ID
        ORDER BY nb_valeurs DESC
    """
    df_param = pd.read_sql(query_param, conn)
    conn.close()

    if df_param.empty:
        st.info("Aucune valeur trouvée pour les paramètres dans les 30 derniers jours.")
    else:
        df_param.set_index("Parameter_ID", inplace=True)
        st.bar_chart(df_param["nb_valeurs"])


def page_main():
    st.sidebar.write(f"Connecté en tant que : **{st.session_state.get('username', '')}**")
    if st.sidebar.button("Se déconnecter"):
        st.session_state.clear()
        st.rerun()

    page = st.sidebar.selectbox(
        "Navigation",
        ["Dashboard", "Liste des métadonnées", "Créer une métadonnée"],
    )

    if page == "Dashboard":
        page_dashboard()
    elif page == "Liste des métadonnées":
        page_metadata_list()
    elif page == "Créer une métadonnée":
        page_create_metadata()


def main():
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False

    if not st.session_state["authenticated"]:
        page_login()
    else:
        page_main()


if __name__ == "__main__":
    main()
