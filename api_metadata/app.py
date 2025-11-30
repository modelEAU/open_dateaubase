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


# -------------------------
# PAGE LISTE METADATA
# -------------------------

def page_metadata_list():
    st.title("Liste des métadonnées")

    st.write("Affichage des lignes de la table `metadata`.")

    conn = get_connection()
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
    df = pd.read_sql(query, conn)
    conn.close()

    st.dataframe(df, use_container_width=True)




def page_create_metadata():
    st.title("Créer une métadonnée")

    st.write("Remplissez le formulaire pour ajouter une ligne dans la table `metadata`.")

    conn = get_connection()
    cur = conn.cursor()

    # --- Charger les listes ---
    cur.execute("SELECT Equipment_ID, Equipment_identifier FROM equipment")
    equipments = cur.fetchall()

    cur.execute("SELECT Parameter_ID, Parameter FROM parameter")
    parameters = cur.fetchall()

    cur.execute("SELECT Unit_ID, Unit FROM unit")
    units = cur.fetchall()

    cur.execute("SELECT Purpose_ID, Purpose FROM purpose")
    purposes = cur.fetchall()

    cur.execute("SELECT Sampling_point_ID, Sampling_point FROM sampling_points")
    sampling_points = cur.fetchall()

    cur.execute("SELECT Project_ID, Project_name FROM project")
    projects = cur.fetchall()

    cur.execute("SELECT Procedure_ID, Procedure_name FROM procedures")
    procedures = cur.fetchall()

    cur.execute("SELECT Contact_ID, First_name FROM contact")
    contacts = cur.fetchall()

    cur.execute("SELECT Condition_ID, Weather_condition FROM weather_condition")
    conditions = cur.fetchall()


    equipment_choice = st.selectbox(
        "Équipement", equipments, format_func=lambda x: f"{x[0]} – {x[1]}"
    )
    equipment_id = equipment_choice[0]

    parameter_choice = st.selectbox(
        "Paramètre", parameters, format_func=lambda x: f"{x[0]} – {x[1]}"
    )
    parameter_id = parameter_choice[0]

    unit_choice = st.selectbox(
        "Unité", units, format_func=lambda x: f"{x[0]} – {x[1]}"
    )
    unit_id = unit_choice[0]

    purpose_choice = st.selectbox(
        "Purpose", purposes, format_func=lambda x: f"{x[0]} – {x[1]}"
    )
    purpose_id = purpose_choice[0]

    sampling_choice = st.selectbox(
        "Point d'échantillonnage", sampling_points, format_func=lambda x: f"{x[0]} – {x[1]}"
    )
    sampling_point_id = sampling_choice[0]

    project_choice = st.selectbox(
        "Projet", projects, format_func=lambda x: f"{x[0]} – {x[1]}"
    )
    project_id = project_choice[0]

    # Procédure (peut être vide)
    if procedures:
        procedure_choice = st.selectbox(
            "Procédure", procedures, format_func=lambda x: f"{x[0]} – {x[1]}"
        )
        procedure_id = procedure_choice[0]
    else:
        st.info("Aucune procédure définie dans la table `procedures`. La valeur sera laissée à NULL.")
        procedure_id = None

    # Contact (peut être vide)
    if contacts:
        contact_choice = st.selectbox(
            "Contact", contacts, format_func=lambda x: f"{x[0]} – {x[1]}"
        )
        contact_id = contact_choice[0]
    else:
        st.info("Aucun contact défini dans la table `contact`. La valeur sera laissée à NULL.")
        contact_id = None

    # Condition météo (peut aussi être vide)
    if conditions:
        condition_choice = st.selectbox(
            "Condition météo", conditions, format_func=lambda x: f"{x[0]} – {x[1]}"
        )
        condition_id = condition_choice[0]
    else:
        st.info("Aucune condition météo définie dans la table `weather_condition`. La valeur sera laissée à NULL.")
        condition_id = None

    start_date = st.date_input("Start Date")

    has_end = st.checkbox("Définir une date de fin ?")
    end_date = None
    if has_end:
        end_date = st.date_input("End Date")

    submit = st.button("Créer métadonnée")

    if submit:
        start_ts = int(start_date.strftime("%s"))
        end_ts = int(end_date.strftime("%s")) if end_date else None

        cur.execute(
            """
            INSERT INTO metadata
            (Parameter_ID, Unit_ID, Purpose_ID, Equipment_ID, Procedure_ID,
            Condition_ID, Sampling_point_ID, Contact_ID, Project_ID,
            StartDate, EndDate)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                parameter_id,
                unit_id,
                purpose_id,
                equipment_id,
                procedure_id,        # peut être None
                condition_id,        # peut être None
                sampling_point_id,
                contact_id,          # peut être None
                project_id,
                start_ts,
                end_ts,
            ),
        )

        conn.commit()
        st.success("Nouvelle métadonnée créée avec succès 🎉")

    cur.close()
    conn.close()



def page_dashboard():
    st.title("Tableau de bord datEAUbase")

    conn = get_connection()
    cur = conn.cursor()

    # ---- KPIs simples ----
    # Nombre total de valeurs
    cur.execute("SELECT COUNT(*) FROM value")
    total_values = cur.fetchone()[0]

    # Nombre de points d'échantillonnage
    cur.execute("SELECT COUNT(*) FROM sampling_points")
    total_sampling_points = cur.fetchone()[0]

    # Nombre de métadonnées actives (StartDate <= now < EndDate ou EndDate NULL)
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

    cur.close()

    # Affichage des trois KPIs
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
        WHERE DATEADD(SECOND, v.[Timestamp], '19700101') >= DATEADD(DAY, -30, GETUTCDATE())
        GROUP BY CAST(DATEADD(SECOND, v.[Timestamp], '19700101') AS date)
        ORDER BY jour
    """

    df_daily = pd.read_sql(query_daily, conn)

    if df_daily.empty:
        st.info("Aucune valeur trouvée dans les 30 derniers jours.")
    else:
        df_daily.set_index("jour", inplace=True)
        st.line_chart(df_daily["nb_valeurs"])

    # 2) Répartition par paramètre sur les 30 derniers jours
    st.subheader("Répartition par paramètre (30 derniers jours)")

    query_param = """
        SELECT
            m.Parameter_ID,
            COUNT(*) AS nb_valeurs
        FROM value v
        JOIN metadata m ON v.Metadata_ID = m.Metadata_ID
        WHERE DATEADD(SECOND, v.[Timestamp], '19700101') >= DATEADD(DAY, -30, GETUTCDATE())
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
    # Sidebar: user + navigation
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
