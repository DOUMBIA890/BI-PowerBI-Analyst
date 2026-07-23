"""Page 5 — 📊 KPI & DAX (Business Intelligence Agent), Phase 5."""
from pathlib import Path
import json
import streamlit as st

from utils.session import init_session, set_current_page, PAGE_PROJET, PAGE_MODELISATION, PAGE_DESIGN
from utils.ui import render_page_header, render_sidebar, card

init_session()
set_current_page(__file__)
render_sidebar()
render_page_header("📊 KPI & DAX", "Mesures DAX, KPI et indicateurs métier (BI Agent)")

s = st.session_state
if not s.project_path:
    st.warning("Aucun projet actif.")
    if st.button("➡️ Aller au projet"):
        st.switch_page(PAGE_PROJET)
    st.stop()

# Charge le modèle généré à l'étape Modélisation
model_path = Path(s.project_path) / "metadata" / "model.json"
if not model_path.exists():
    st.warning("Modèle non trouvé. Générez-le d'abord à l'étape Modélisation.")
    if st.button("⬅️ Retour Modélisation"):
        st.switch_page(PAGE_MODELISATION)
    st.stop()

model = json.loads(model_path.read_text(encoding="utf-8"))

# Recharge les métadonnées sources pour générer les mesures
data_dir = Path(s.project_path) / "data"
sources_meta = {}
for fname in s.data_sources:
    base = Path(fname).stem
    mp = data_dir / f"{base}_metadata.json"
    if mp.exists():
        sources_meta[fname] = json.loads(mp.read_text(encoding="utf-8"))


def do_kpi():
    from agents.bi_agent import BIAgent
    dm = BIAgent.build_dax_measures(model, sources_meta)
    kp = BIAgent.build_kpi_catalog(model, dm)
    s.dax_measures = dm
    s.kpi_catalog = kp
    out_dir = Path(s.project_path) / "metadata"
    out_dir.mkdir(exist_ok=True)
    (out_dir / "dax_measures.json").write_text(
        json.dumps(dm, ensure_ascii=False, indent=2), encoding="utf-8")
    (out_dir / "kpi_catalog.json").write_text(
        json.dumps(kp, ensure_ascii=False, indent=2), encoding="utf-8")
    return dm, kp


if st.button("🧮 Générer mesures DAX & KPI", type="primary"):
    try:
        dm, kp = do_kpi()
        st.success(f"✅ {len(dm['measures'])} mesures et {len(kp['kpis'])} KPI générés "
                   "(metadata/dax_measures.json, metadata/kpi_catalog.json).")
    except Exception as e:
        st.error(f"Erreur : {e}")

if s.get("dax_measures"):
    dm = s.dax_measures
    kp = s.kpi_catalog

    card(f"Mesures DAX ({len(dm['measures'])})", badge="DAX")
    for m in dm["measures"]:
        st.code(f"{m['nom']} =\n{m['expression']}", language="text")

    st.divider()
    card(f"Catalogue KPI ({len(kp['kpis'])})", badge="KPI")
    if kp["kpis"]:
        for k in kp["kpis"]:
            st.markdown(f"- **{k['nom']}** — `{k['table']}` · format `{k['format']}`")
    else:
        st.info("Aucun KPI (mesures de type somme/comptage requises).")

    if st.button("💡 Suggestions de KPI métier (IA)"):
        from agents.bi_agent import BIAgent
        with st.spinner("Génération par l'IA..."):
            try:
                sug = BIAgent.generate_kpi_suggestions(model, dm)
                st.markdown(sug)
            except Exception as e:
                st.error(f"Erreur IA : {e}")

    if st.button("➡️ Continuer vers le Design", type="primary"):
        st.switch_page(PAGE_DESIGN)

if st.button("⬅️ Retour Modélisation"):
    st.switch_page(PAGE_MODELISATION)
