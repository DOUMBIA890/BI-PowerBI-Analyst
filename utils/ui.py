"""Helpers d'interface réutilisables — Design clair & moderne (style SaaS pro).

Palette "BI Architect Light" : fond très clair, accent indigo/violet, cartes
douces avec ombres portées, typographie soignée. Cohérent sur toutes les pages.
Chaque page appelle : render_page_header(...), render_sidebar(), card(...).
"""
import streamlit as st

# Palette centralisée (réutilisée dans le theme.json Power BI plus tard)
PALETTE = {
    "bg": "#f5f7fb",
    "surface": "#ffffff",
    "border": "#e4e8ef",
    "primary": "#4f46e5",
    "primary_soft": "#eef0ff",
    "accent": "#0ea5e9",
    "text": "#1e2430",
    "muted": "#6b7280",
    "success": "#16a34a",
    "warning": "#d97706",
    "shadow": "0 1px 3px rgba(16,24,40,.08), 0 1px 2px rgba(16,24,40,.06)",
}

PAGES = [
    ("🏠 Projet", "pages/1_🏠_Projet.py"),
    ("📂 Sources", "pages/2_📂_Sources.py"),
    ("🧹 Data Engineer", "pages/3_🧹_Data_Engineer.py"),
    ("📈 Modélisation", "pages/4_📈_Modelisation.py"),
    ("📊 KPI & DAX", "pages/5_📊_KPI_DAX.py"),
    ("🎨 Design", "pages/6_🎨_Design.py"),
    ("🚀 Power BI Builder", "pages/7_🚀_PowerBI_Builder.py"),
    ("⚙️ Paramètres", "pages/8_⚙️_Settings.py"),
    ("🔍 Auditor", "pages/9_🔍_Auditor.py"),
]


def inject_css():
    """Injecte le CSS global clair et moderne."""
    st.markdown(
        f"""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
        html, body, .stApp {{ font-family: 'Inter', -apple-system, sans-serif; }}
        .stApp {{
            background-color: {PALETTE['bg']};
            color: {PALETTE['text']};
        }}
        section[data-testid="stSidebar"] {{
            background-color: {PALETTE['surface']};
            border-right: 1px solid {PALETTE['border']};
        }}
        .bia-header {{
            padding: 1.3rem 1.6rem;
            background: linear-gradient(120deg, #4f46e5 0%, #0ea5e9 100%);
            border-radius: 16px;
            margin-bottom: 1.4rem;
            box-shadow: {PALETTE['shadow']};
        }}
        .bia-header h1 {{
            margin: 0; color: #fff; font-size: 1.6rem; font-weight: 700;
            letter-spacing: -0.01em;
        }}
        .bia-header .sub {{ color: rgba(255,255,255,.85); font-size: 0.92rem; margin-top: 0.3rem; }}
        .bia-card {{
            background-color: {PALETTE['surface']};
            border: 1px solid {PALETTE['border']};
            border-radius: 14px;
            padding: 1.2rem 1.4rem;
            margin-bottom: 1.1rem;
            box-shadow: {PALETTE['shadow']};
        }}
        .bia-card h3 {{ color: {PALETTE['text']}; margin-top: 0; font-weight: 600; }}
        .bia-badge {{
            display: inline-block;
            background: {PALETTE['primary']};
            color: #fff;
            border-radius: 999px;
            padding: 0.2rem 0.75rem;
            font-size: 0.72rem;
            font-weight: 600;
        }}
        .bia-step-dot {{ color: {PALETTE['primary']}; font-weight: 600; }}
        /* Champs */
        .stTextInput > div > div > input,
        .stTextArea > div > div > textarea,
        .stSelectbox > div > div {{
            background-color: #fff;
            color: {PALETTE['text']};
            border: 1px solid {PALETTE['border']};
            border-radius: 10px;
        }}
        /* Boutons */
        .stButton > button {{
            border-radius: 10px;
            font-weight: 600;
        }}
        /* Sidebar nav buttons */
        .stSidebar .stButton > button {{
            border: 1px solid {PALETTE['border']};
            background: #fff;
            color: {PALETTE['text']};
            justify-content: flex-start;
        }}
        .stSidebar .stButton > button:hover {{
            border-color: {PALETTE['primary']};
            color: {PALETTE['primary']};
        }}
        footer {{ visibility: hidden; }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_page_header(title: str, subtitle: str = ""):
    """En-tête standard pour chaque page."""
    inject_css()
    st.markdown(
        f"""
        <div class="bia-header">
            <h1>{title}</h1>
            <div class="sub">{subtitle}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar():
    """Barre latérale de navigation + état du projet."""
    s = st.session_state
    with st.sidebar:
        st.markdown("### 🤖 BI Architect AI")
        st.markdown('<hr style="border-color:#e4e8ef;">', unsafe_allow_html=True)
        st.markdown("**Navigation**")
        current = st.session_state.get("_current_page", "")
        for label, path in PAGES:
            if path == current:
                st.markdown(f'<span class="bia-badge">{label}</span>', unsafe_allow_html=True)
            else:
                if st.button(label, key=f"nav_{path}", use_container_width=True):
                    st.switch_page(path)
        st.markdown('<hr style="border-color:#e4e8ef;">', unsafe_allow_html=True)
        st.markdown("**Projet actif**")
        if s.get("project_name"):
            st.success(s["project_name"])
            st.caption(s["project_path"])
            n = len(s.get("data_sources", []))
            st.metric("Sources", n)
        else:
            st.info("Aucun projet")


def card(title: str, body: str = "", badge: str = ""):
    """Carte encadrée réutilisable."""
    badge_html = f'<span class="bia-badge">{badge}</span> ' if badge else ""
    st.markdown(
        f"""
        <div class="bia-card">
            <h3>{badge_html}{title}</h3>
            <div style="color:#1e2430;">{body}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def step_badge(step_label: str):
    """Petit marqueur d'étape dans un titre de page."""
    st.markdown(f'<span class="bia-step-dot">{step_label}</span>', unsafe_allow_html=True)
