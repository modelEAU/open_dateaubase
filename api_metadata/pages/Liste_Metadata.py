import pandas as pd
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

    st.title("🧾 Liste des métadonnées")
    st.caption("Recherche, filtres, et affichage lisible (avec noms).")

    # ---- Filters UI ----
    c1, c2, c3, c4 = st.columns([1, 1, 1, 1])

    with c1:
        limit = st.slider("Nombre de lignes", 50, 1000, 200, 50)
    with c2:
        active_only = st.checkbox("Actives seulement", value=False)
    with c3:
        equipment_id = st.text_input("Filtrer Equipment_ID", placeholder="ex: 1")
    with c4:
        parameter_id = st.text_input("Filtrer Parameter_ID", placeholder="ex: 2")

    search = st.text_input(
        "Recherche texte (équipement / paramètre / projet / point)",
        placeholder="ex: pH, débit, Roma, station, …",
    )

    # ---- Build SQL ----
    where = []
    params = []

    if active_only:
        where.append("m.StartDate <= DATEDIFF(SECOND, '19700101', GETUTCDATE()) AND (m.EndDate IS NULL OR m.EndDate > DATEDIFF(SECOND, '19700101', GETUTCDATE()))")

    if equipment_id.strip().isdigit():
        where.append("m.Equipment_ID = ?")
        params.append(int(equipment_id.strip()))

    if parameter_id.strip().isdigit():
        where.append("m.Parameter_ID = ?")
        params.append(int(parameter_id.strip()))

    if search.strip():
        s = f"%{search.strip()}%"
        where.append("""
            (
              e.Equipment_identifier LIKE ?
              OR p.Parameter LIKE ?
              OR pr.Project_name LIKE ?
              OR sp.Sampling_point LIKE ?
            )
        """)
        params.extend([s, s, s, s])

    where_sql = ("WHERE " + " AND ".join(where)) if where else ""

    query = f"""
        SELECT TOP {int(limit)}
            m.Metadata_ID,

            m.Equipment_ID,
            e.Equipment_identifier AS Equipment,

            m.Parameter_ID,
            p.Parameter AS Parameter,

            m.Unit_ID,
            u.Unit AS Unit,

            m.Purpose_ID,
            pu.Purpose AS Purpose,

            m.Project_ID,
            pr.Project_name AS Project,

            m.Sampling_point_ID,
            sp.Sampling_point AS Sampling_point,

            m.Procedure_ID,
            proc.Procedure_name AS Procedure,

            m.Contact_ID,
            c.First_name AS Contact,

            m.Condition_ID,
            wc.Weather_condition AS Weather_condition,

            m.StartDate,
            m.EndDate
        FROM metadata m
        LEFT JOIN equipment e ON e.Equipment_ID = m.Equipment_ID
        LEFT JOIN parameter p ON p.Parameter_ID = m.Parameter_ID
        LEFT JOIN unit u ON u.Unit_ID = m.Unit_ID
        LEFT JOIN purpose pu ON pu.Purpose_ID = m.Purpose_ID
        LEFT JOIN project pr ON pr.Project_ID = m.Project_ID
        LEFT JOIN sampling_points sp ON sp.Sampling_point_ID = m.Sampling_point_ID
        LEFT JOIN procedures proc ON proc.Procedure_ID = m.Procedure_ID
        LEFT JOIN contact c ON c.Contact_ID = m.Contact_ID
        LEFT JOIN weather_condition wc ON wc.Condition_ID = m.Condition_ID
        {where_sql}
        ORDER BY m.Metadata_ID DESC
    """

    # ---- Execute ----
    conn = get_connection()
    try:
        df = pd.read_sql(query, conn, params=params)
    finally:
        conn.close()

    if df.empty:
        st.info("Aucune métadonnée ne correspond aux filtres.")
        st.markdown("</div>", unsafe_allow_html=True)
        return

    # Convert unix timestamps
    for col in ["StartDate", "EndDate"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], unit="s", errors="coerce", utc=True)

    # Nice column ordering (names first)
    preferred = [
        "Metadata_ID",
        "Equipment", "Equipment_ID",
        "Parameter", "Parameter_ID",
        "Unit", "Unit_ID",
        "Purpose", "Purpose_ID",
        "Project", "Project_ID",
        "Sampling_point", "Sampling_point_ID",
        "Procedure", "Procedure_ID",
        "Contact", "Contact_ID",
        "Weather_condition", "Condition_ID",
        "StartDate", "EndDate",
    ]
    cols = [c for c in preferred if c in df.columns] + [c for c in df.columns if c not in preferred]
    df = df[cols]

    st.dataframe(df, use_container_width=True)

    st.markdown("</div>", unsafe_allow_html=True)

if __name__ == "__main__":
    main()
