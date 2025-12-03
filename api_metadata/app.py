import os
from datetime import datetime

import streamlit as st
import pandas as pd

from db import get_connection


USERS = {
    "admin": os.getenv("UI_ADMIN_PASSWORD", "admin123"),
    "user": os.getenv("UI_USER_PASSWORD", "user123"),
}


def check_credentials(username: str, password: str) -> bool:
    return username in USERS and USERS[username] == password


def page_login():
    st.title("datEAUbase – Connexion")

    username = st.text_input("Nom d’utilisateur")
    password = st.text_input("Mot de passe", type="password")
    login_btn = st.button("Se connecter")

    if login_btn:
        if check_credentials(username, password):
            st.session_state["authenticated"] = True
            st.session_state["username"] = username
            st.success("Connexion réussie ✅")
            st.rerun()
        else:
            st.error("Identifiants invalides ❌")


def page_metadata_list():
    st.title("Liste des métadonnées")
    st.write("Affichage des lignes de la table `metadata`.")

    try:
        conn = get_connection()
    except Exception as e:
        st.error(f"Impossible de se connecter à la base de données 😢\n\nDétail : {e}")
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
        st.error(f"Erreur lors de la lecture de la table `metadata` 😢\n\nDétail : {e}")
        return

    conn.close()

    if df.empty:
        st.info("La table `metadata` est vide pour l’instant.")
    else:
        st.dataframe(df, use_container_width=True)


def page_create_metadata():
    st.title("Créer une métadonnée")

    st.write(
        "Formulaire libre : entre les valeurs ci-dessous. "
        "Si un élément (équipement, paramètre, etc.) n'existe pas encore, "
        "il sera automatiquement créé dans la base."
    )

    conn = get_connection()
    cur = conn.cursor()

 
    col1, col2 = st.columns(2)

    with col1:
        equipment_name = st.text_input("Equipment_id")
        parameter_name = st.text_input("Parameter_id")
        unit_name = st.text_input("Unit_id")
        purpose_name = st.text_input("Purpose_id")
        project_name = st.text_input("Project_id")

    with col2:
        sampling_point_name = st.text_input("Sampling_point_id")
        procedure_name = st.text_input("Procedure_id")
        contact_name = st.text_input("Contact_id")
        condition_name = st.text_input("Condition_id")

    start_date = st.date_input("Start Date")
    has_end = st.checkbox("Définir une date de fin ?")
    end_date = st.date_input("End Date") if has_end else None

    submit = st.button("Créer métadonnée")

    if submit:

        required = {
            "Nom de l'équipement": equipment_name,
            "Nom du paramètre": parameter_name,
            "Unité": unit_name,
            "Purpose / objectif": purpose_name,
            "Nom du projet": project_name,
            "Point d'échantillonnage": sampling_point_name,
            "Procédure": procedure_name,
            "Contact": contact_name,
            "Condition météo": condition_name,
        }

        for label, value in required.items():
            if not value.strip():
                st.error(f"{label} est obligatoire.")
                cur.close()
                conn.close()
                st.stop()

        def get_or_create_id(table, id_col, name_col, name_value):
            query_select = f"SELECT {id_col} FROM {table} WHERE {name_col} = ?"
            cur.execute(query_select, name_value)
            row = cur.fetchone()
            if row:
                return row[0]

            query_max = f"SELECT ISNULL(MAX({id_col}), 0) FROM {table}"
            cur.execute(query_max)
            max_id = cur.fetchone()[0]
            new_id = max_id + 1

            query_insert = f"INSERT INTO {table} ({id_col}, {name_col}) VALUES (?, ?)"
            cur.execute(query_insert, new_id, name_value)
            return new_id

        equipment_id = get_or_create_id(
            "equipment", "Equipment_ID", "Equipment_identifier", equipment_name
        )

        parameter_id = get_or_create_id(
            "parameter", "Parameter_ID", "Parameter", parameter_name
        )

        unit_id = get_or_create_id("unit", "Unit_ID", "Unit", unit_name)

        purpose_id = get_or_create_id("purpose", "Purpose_ID", "Purpose", purpose_name)

        project_id = get_or_create_id(
            "project", "Project_ID", "Project_name", project_name
        )

        sampling_point_id = get_or_create_id(
            "sampling_points", "Sampling_point_ID", "Sampling_point", sampling_point_name
        )

        procedure_id = get_or_create_id(
            "procedures", "Procedure_ID", "Procedure_name", procedure_name
        )

        contact_id = get_or_create_id(
            "contact", "Contact_ID", "First_name", contact_name
        )

        condition_id = get_or_create_id(
            "weather_condition", "Condition_ID", "Weather_condition", condition_name
        )

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
        st.success(
            f"Nouvelle métadonnée créée avec succès 🎉 (Metadata_ID = {new_metadata_id})"
        )

    cur.close()
    conn.close()

def page_dashboard():
    st.title("Tableau de bord datEAUbase")

    conn = get_connection()
    cur = conn.cursor()

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

    # KPIs
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Valeurs en base", total_values)
    with col2:
        st.metric("Points d'échantillonnage", total_sampling_points)
    with col3:
        st.metric("Métadonnées actives", active_metadata)

    st.markdown("---")

    # ---- Graphes sur les 30 derniers jours ----
    st.subheader("Activité sur les 30 derniers jours")

    # 1) Nombre de valeurs par jour
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

    # 2) Répartition par paramètre
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
    st.sidebar.write(
        f"Connecté en tant que : **{st.session_state.get('username', '')}**"
    )
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
