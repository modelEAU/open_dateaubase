from datetime import datetime
import pandas as pd
import streamlit as st

from api_metadata.utils.auth_guard import require_login
from api_metadata.ui_style import apply_global_style, render_header_logos
from api_metadata.db import get_connection

LOGIN_PAGE = "api_metadata/pages/login.py"

def main():
    # 🔐 Auth gate
    require_login()

    apply_global_style()

    # Mark page as authenticated (for CSS)
    st.markdown("<div class='authenticated'>", unsafe_allow_html=True)

    # Sidebar logout
    if st.sidebar.button("Se déconnecter"):
        st.session_state.clear()
        st.switch_page(LOGIN_PAGE)

    render_header_logos()

    st.title("📊 Tableau de bord datEAUbase")
    st.caption(f"Connecté : {st.session_state.get('username','')}")

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

    c1, c2, c3 = st.columns(3)
    c1.metric("Valeurs en base", total_values)
    c2.metric("Points d’échantillonnage", total_sampling_points)
    c3.metric("Métadonnées actives", active_metadata)

    st.markdown("---")
    st.subheader("📈 Activité (30 derniers jours)")

    df_daily = pd.read_sql(
        """
        SELECT
            CAST(DATEADD(SECOND, v.[Timestamp], '19700101') AS date) AS jour,
            COUNT(*) AS nb_valeurs
        FROM value v
        WHERE DATEADD(SECOND, v.[Timestamp], '19700101')
          >= DATEADD(DAY, -30, GETUTCDATE())
        GROUP BY CAST(DATEADD(SECOND, v.[Timestamp], '19700101') AS date)
        ORDER BY jour
        """,
        conn,
    )

    if df_daily.empty:
        st.info("Aucune valeur trouvée dans les 30 derniers jours.")
    else:
        df_daily.set_index("jour", inplace=True)
        st.line_chart(df_daily["nb_valeurs"])

    st.subheader("🏷️ Répartition par paramètre (30 jours)")

    df_param = pd.read_sql(
        """
        SELECT
            m.Parameter_ID,
            COUNT(*) AS nb_valeurs
        FROM value v
        JOIN metadata m ON v.Metadata_ID = m.Metadata_ID
        WHERE DATEADD(SECOND, v.[Timestamp], '19700101')
        >= DATEADD(DAY, -30, GETUTCDATE())
        GROUP BY m.Parameter_ID
        ORDER BY nb_valeurs DESC
        """,
        conn,
    )

    conn.close()

    if df_param.empty:
        st.info("Aucune valeur trouvée.")
    else:
        df_param.set_index("Parameter_ID", inplace=True)
        st.bar_chart(df_param["nb_valeurs"])

    # Close authenticated wrapper
    st.markdown("</div>", unsafe_allow_html=True)

if __name__ == "__main__":
    main()
