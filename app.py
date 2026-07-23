"""BI Architect AI — Page d'accueil (racine Streamlit).

From Raw Data to Executive Dashboard.

Tableau de bord d'entrée + sélecteur de projet.
"""
from pathlib import Path
import streamlit as st

from utils.session import init_session, set_current_page, list_existing_projects, PAGE_PROJET
from utils.ui import render_page_header, render_sidebar, card

# L'accueil n'est pas une page de la barre latérale : on marque "" pour éviter
# un badge actif erroné.
init_session()
set_current_page("")
render_sidebar()
render_page_header("🤖 BI Architect AI", "From Raw Data to Executive Dashboard")

s = st.session_state

col1, col2 = st.columns([1, 1.2])

with col1:
    card("Votre projet", badge="STATUT")
    if s.project_path:
        st.success(f"**{s.project_name}**")
        st.caption(f"📁 {s.project_path}")
        n = len(s.get("data_sources", []))
        st.metric("Sources de données", n)
        if st.button("➡️ Ouvrir le projet", type="primary", use_container_width=True):
            st.switch_page(PAGE_PROJET)
    else:
        st.info("Aucun projet actif.")
        if st.button("➕ Créer / ouvrir un projet", type="primary", use_container_width=True):
            st.switch_page(PAGE_PROJET)

with col2:
    card("Roadmap — Phase 1", badge="PROGRESSION")
    rows = [
        ("1 · Projet", "🟢"),
        ("2 · Sources", "🟢"),
        ("3 · Prétraitement IA", "🟢"),
        ("4 · Modélisation", "🔜"),
        ("5 · KPI & DAX", "🔜"),
        ("6 · Design", "🔜"),
        ("7 · Power BI Builder", "🔜"),
        ("8 · Paramètres", "🟢"),
    ]
    for label, status in rows:
        st.markdown(f"`{status}`  {label}")

st.divider()
st.caption(
    "Vision : générer un projet Power BI (.pbip) complet à partir de données "
    "(CSV / Excel / PostgreSQL) — modèle sémantique TMDL, mesures DAX, "
    "KPI, design et documentation."
)
