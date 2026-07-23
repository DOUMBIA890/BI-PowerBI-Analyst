"""Page 2 — 📂 Sources de données (CSV / Excel / PostgreSQL)."""
from pathlib import Path
import streamlit as st

from utils.session import (
    init_session,
    set_current_page,
    PAGE_PROJET,
    PAGE_DATA_ENGINEER,
)
from utils.ui import render_page_header, render_sidebar, card

init_session()
set_current_page(__file__)
render_sidebar()
render_page_header("📂 Sources de données", "Connectez CSV, Excel ou PostgreSQL")

s = st.session_state

if not s.project_path:
    st.warning("Aucun projet actif. Veuillez d'abord créer un projet.")
    if st.button("➡️ Aller au projet"):
        st.switch_page(PAGE_PROJET)
    st.stop()

source = st.radio("Choisir une source", ["📁 CSV / Excel", "🐘 PostgreSQL"], horizontal=True)

if source == "📁 CSV / Excel":
    card("Importer des fichiers")
    files = st.file_uploader(
        "Ajouter vos fichiers",
        type=["csv", "xlsx"],
        accept_multiple_files=True,
    )
    if files:
        if st.button("Importer", type="primary"):
            try:
                saved = s.fm.add_files(files, s.project_path)
                s.data_sources = saved
                if s.workflow:
                    s.workflow.run_step("import_files", files=files)
                st.success(f"✅ {len(saved)} fichier(s) ajouté(s) :")
                for fname in saved:
                    st.write("•", fname)
            except Exception as e:
                st.error(f"Erreur lors de l'import : {e}")
        if st.button("➡️ Analyser ces données (Prétraitement IA)"):
            st.switch_page(PAGE_DATA_ENGINEER)

else:
    card("Connexion PostgreSQL")
    host = st.text_input("Host", "localhost")
    port = st.text_input("Port", "5432")
    database = st.text_input("Base")
    user = st.text_input("Utilisateur")
    password = st.text_input("Mot de passe", type="password")
    if st.button("Connexion", type="primary"):
        try:
            engine = s.db.connect_postgresql(host, port, database, user, password)
            tables = s.db.get_tables(engine)
            st.success(f"✅ Connecté ! Tables : {', '.join(tables)}")
            s.data_sources = tables
            if st.button("➡️ Analyser ces données (Prétraitement IA)"):
                st.switch_page(PAGE_DATA_ENGINEER)
        except Exception as e:
            st.error(f"Erreur de connexion : {e}")
