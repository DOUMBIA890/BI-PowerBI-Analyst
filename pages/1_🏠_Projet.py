"""Page 1 — 🏠 Projet (création + sélection de projet)."""
from pathlib import Path
import streamlit as st

from utils.session import (
    init_session,
    step_create_project,
    build_workflow_for,
    set_current_page,
    list_existing_projects,
    PAGE_SOURCES,
)
from utils.ui import render_page_header, render_sidebar, card

init_session()
set_current_page(__file__)
render_sidebar()
render_page_header("🏠 Projet", "Créez ou ouvrez un projet BI — From Raw Data to Executive Dashboard")

s = st.session_state

# ==========================
# Sélecteur de projets existants
# ==========================
existing = list_existing_projects()
if existing:
    with st.container():
        st.markdown("### Ouvrir un projet existant")
        choice = st.selectbox("Projets disponibles", existing)
        if st.button("Ouvrir le projet", type="secondary"):
            s.project_name = choice
            s.project_path = str(Path("projects") / choice)
            st.success(f"✅ Projet ouvert : {choice}")
            try:
                s.data_sources = list((Path(s.project_path) / "data").glob("*"))
                s.data_sources = [p.name for p in s.data_sources]
            except Exception:
                s.data_sources = []
        st.divider()

# ==========================
# Création d'un projet
# ==========================
card("Créer un nouveau projet")
with st.container():
    name = st.text_input("Nom du projet", value=s.project_name or "")
    description = st.text_area("Description", value="")

    if st.button("Créer le projet", type="primary"):
        if name:
            try:
                wf = build_workflow_for(name)
                result = wf.run_step("create_project", name=name, description=description)
                s.project_path = result["project_path"]
                s.project_name = result["project_name"]
                s.data_sources = []
                from core.logger import logger
                logger.info(f"Projet cree : {result['project_path']}")
                st.success(f"✅ Projet créé : {result['project_path']}")
            except Exception as e:
                st.error(f"Erreur : {e}")
        else:
            st.warning("Veuillez saisir un nom.")

# ==========================
# Projet actif
# ==========================
if s.project_path:
    st.divider()
    st.success(f"📁 Projet actif : **{s.project_name}**")
    st.caption(str(s.project_path))
    if st.button("➡️ Continuer vers les sources de données", type="primary"):
        st.switch_page(PAGE_SOURCES)
else:
    st.warning("Veuillez d'abord créer ou ouvrir un projet.")
