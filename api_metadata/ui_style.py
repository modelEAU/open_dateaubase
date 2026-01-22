import base64
import streamlit as st


def _img_base64(path: str) -> str:
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def apply_global_style(max_width_px: int = 1200):
    """
    - Fond blanc (pages)
    - Sidebar sombre + texte blanc
    - Inputs / selectbox sombres + texte blanc
    - Bouton principal vert (login)
    - Scroll fluide
    - Fix st.metric valeurs en noir
    """
    st.set_page_config(
        page_title="datEAUbase",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    st.markdown(
        f"""
        <style>
        html {{ scroll-behavior: smooth; }}

        body, .stApp {{
            background: #ffffff !important;
            color: #0f172a !important;
        }}

        /* titres / texte */
        h1, h2, h3, h4, h5, h6, p, label {{
            color: #0f172a !important;
        }}

        /* container */
        .block-container {{
            max-width: {max_width_px}px;
            padding: 1.25rem 1.5rem 3rem 1.5rem;
        }}

        section[data-testid="stSidebar"] {{
            background: linear-gradient(180deg, #1f2937, #0b1220);
        }}
        section[data-testid="stSidebar"] * {{
            color: #ffffff !important;
        }}

        /* bouton sidebar */
        section[data-testid="stSidebar"] .stButton button {{
            background: rgba(255,255,255,0.06) !important;
            border: 1px solid rgba(255,255,255,0.18) !important;
            color: #ffffff !important;
            border-radius: 12px;
        }}

        /* selectbox sidebar */
        section[data-testid="stSidebar"] div[data-baseweb="select"] > div {{
            background: rgba(0,0,0,0.25) !important;
            border: 1px solid rgba(255,255,255,0.18) !important;
            border-radius: 12px;
        }}
        section[data-testid="stSidebar"] div[data-baseweb="select"] * {{
            color: #ffffff !important;
        }}


        /* fond + bordure pour select */
        div[data-baseweb="select"] > div {{
            background: #1f2937 !important;
            border: 1px solid #374151 !important;
            border-radius: 12px !important;
        }}

        /* IMPORTANT: le texte du select */
        div[data-baseweb="select"] * {{
            color: #ffffff !important;
            fill: #ffffff !important;
        }}

        /* dropdown menu */
        ul[role="listbox"] {{
            background: #111827 !important;
        }}
        ul[role="listbox"] * {{
            color: #ffffff !important;
        }}

        /* inputs texte */
        .stTextInput input,
        .stTextArea textarea,
        div[data-baseweb="input"] input {{
            background: #1f2937 !important;
            color: #ffffff !important;
            caret-color: #ffffff !important;
            border: 1px solid #374151 !important;
            border-radius: 12px !important;
        }}

        .stTextInput input::placeholder {{
            color: #cbd5e1 !important;
            opacity: 1;
        }}

        /* date_input : baseweb input */
        div[data-baseweb="datepicker"] * {{
            color: #ffffff !important;
        }}
        div[data-baseweb="calendar"] * {{
            color: #ffffff !important;
        }}

        /* checkbox label (page blanche) */
        .stCheckbox label {{
            color: #0f172a !important;
        }}

      
        div[data-testid="stMetricValue"] {{
            color: #0f172a !important;
            opacity: 1 !important;
        }}

      
        div[data-testid="stDataFrame"] {{
            width: 100% !important;
        }}
        div[data-testid="stDataFrame"] * {{
            font-size: 12px;
        }}

     
        .stButton button {{
            border-radius: 12px;
            font-weight: 700;
            padding: 0.6rem 1.2rem;
        }}

        /* bouton "login" vert (classe spéciale) */
        .ui-btn-green button {{
            background: #16a34a !important;
            border: 1px solid #15803d !important;
            color: #ffffff !important;
        }}
        .ui-btn-green button:hover {{
            filter: brightness(0.95);
        }}


        .ui-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;

            padding: 22px 26px;
            margin: 16px 0 26px 0;

            background: #ffffff;
            border: 1px solid #e5e7eb;
            border-radius: 18px;
            box-shadow: 0 10px 28px rgba(0,0,0,0.08);
        }}

        .ui-logo-box {{
            height: 86px;
            display: flex;
            align-items: center;
        }}

        .ui-logo-box img {{
            max-height: 86px;
            max-width: 280px;
            object-fit: contain;
            display: block;
        }}

        .ui-login-card {{
            background: #ffffff;
            border: 1px solid #e5e7eb;
            border-radius: 18px;
            box-shadow: 0 12px 30px rgba(0,0,0,0.08);
            padding: 26px 28px;
        }}

        .ui-login-title {{
            font-size: 34px;
            font-weight: 900;
            text-align: center;
            margin: 6px 0 6px 0;
            color: #0f172a !important;
        }}

        .ui-login-sub {{
            text-align: center;
            color: #475569 !important;
            margin-bottom: 18px;
        }}

        /* champs login "normaux" (pas ultra larges) */
        .ui-login-wrap {{
            max-width: 520px;
            margin: 0 auto;
        }}

        </style>
        """,
        unsafe_allow_html=True,
    )


def render_header_logos(
    left_logo_path="pics/logo.webp",
    right_logo_path="pics/ulaval.webp",
):
    left = _img_base64(left_logo_path)
    right = _img_base64(right_logo_path)

    st.markdown(
        f"""
        <div class="ui-header">
            <div class="ui-logo-box">
                <img src="data:image/webp;base64,{left}" alt="Logo gauche">
            </div>
            <div class="ui-logo-box">
                <img src="data:image/webp;base64,{right}" alt="Logo droite">
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def open_login_form(max_width_px: int = 680):
    st.markdown(
        f"<div class='ui-login-card' style='max-width:{max_width_px}px; margin:0 auto;'>",
        unsafe_allow_html=True,
    )


def close_login_form():
    st.markdown("</div>", unsafe_allow_html=True)
