"""Page 3 — 🧹 AI Data Engineer (prétraitement IA)."""
from pathlib import Path
import json
import streamlit as st

from utils.session import (
    init_session,
    set_current_page,
    PAGE_PROJET,
    PAGE_SOURCES,
    PAGE_MODELISATION,
)
from utils.ui import render_page_header, render_sidebar, card

init_session()
set_current_page(__file__)
render_sidebar()
render_page_header("🧹 AI Data Engineer", "Analyse, qualité et plan de nettoyage des données")

s = st.session_state

if not s.project_path:
    st.warning("Aucun projet actif. Veuillez d'abord créer un projet.")
    if st.button("➡️ Aller au projet"):
        st.switch_page(PAGE_PROJET)
    st.stop()

if not s.data_sources:
    st.info("Aucune source chargée. Ajoutez des fichiers d'abord.")
    if st.button("➡️ Aller aux sources"):
        st.switch_page(PAGE_SOURCES)
    st.stop()

if st.button("🔍 Analyser les données", type="primary"):
    try:
        from agents.ai_data_engineer import AIDataEngineer
        import pandas as pd
        analysis_results = {}
        data_dir = Path(s.project_path) / "data"
        for fname in s.data_sources:
            fp = data_dir / fname
            if fp.suffix == ".csv":
                df = pd.read_csv(fp)
            elif fp.suffix == ".xlsx":
                df = pd.read_excel(fp)
            else:
                continue
            analysis_results[fname] = AIDataEngineer.analyze_dataframe(df, fname)

            # Phase 3 — Livrables d'ingénierie des données
            metadata = AIDataEngineer.build_metadata(df, fname)
            quality = AIDataEngineer.build_quality_report(df, fname)
            cleaning = AIDataEngineer.build_cleaning_plan(df, fname)
            base = Path(fname).stem
            s.fm.save_json(s.project_path, f"{base}_metadata.json", metadata)
            s.fm.save_json(s.project_path, f"{base}_quality_report.json", quality)
            s.fm.save_json(s.project_path, f"{base}_cleaning_plan.json", cleaning)

        s.analysis_results = analysis_results
        st.success("✅ Analyse terminée. Livrables générés : metadata / quality_report / cleaning_plan.")
    except Exception as e:
        st.error(f"Erreur d'analyse : {e}")

if s.analysis_results:
    st.divider()
    for fname, res in s.analysis_results.items():
        base = Path(fname).stem
        card(f"📄 {fname}", badge="ANALYSE")
        with st.expander("Aperçu de l'analyse"):
            st.json(res)

        c1, c2, c3 = st.columns(3)
        with c1:
            if st.button(f"📊 metadata", key=f"meta_{base}", use_container_width=True):
                data = json.loads((Path(s.project_path) / "data" / f"{base}_metadata.json").read_text(encoding="utf-8"))
                st.json(data)
        with c2:
            if st.button(f"🩺 qualité", key=f"qual_{base}", use_container_width=True):
                data = json.loads((Path(s.project_path) / "data" / f"{base}_quality_report.json").read_text(encoding="utf-8"))
                st.json(data)
        with c3:
            if st.button(f"🧼 nettoyage", key=f"clean_{base}", use_container_width=True):
                data = json.loads((Path(s.project_path) / "data" / f"{base}_cleaning_plan.json").read_text(encoding="utf-8"))
                st.json(data)

        if st.button(f"💡 Suggestions de schéma pour {fname}", key=f"sug_{base}"):
            with st.spinner("Génération par l'IA..."):
                try:
                    sug = AIDataEngineer.generate_schema_suggestions(res)
                    st.markdown(sug)
                except Exception as e:
                    st.error(f"Erreur IA : {e}")

    st.divider()
    if st.button("➡️ Continuer vers la Modélisation", type="primary"):
        st.switch_page(PAGE_MODELISATION)
