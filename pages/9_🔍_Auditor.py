"""Page 9 — 🔍 AI Auditor (audit & optimisation d'un .pbip existant), Phase 9."""
from pathlib import Path
import json
import streamlit as st

from utils.session import init_session, set_current_page, PAGE_PROJET, PAGE_SETTINGS
from utils.ui import render_page_header, render_sidebar, card

init_session()
set_current_page(__file__)
render_sidebar()
render_page_header("🔍 AI Auditor", "Audit et optimisation d'un projet Power BI existant")

s = st.session_state

uploaded = st.file_uploader(
    "Déposez un dossier projet .pbip (ou sélectionnez un projet généré)",
    accept_multiple_files=False,
    type=[],  # on accepte un fichier (zippé ou définition.pbip)
)
# Propose aussi les .pbip déjà générés dans le projet courant
existing_pbip = []
if s.get("project_path"):
    existing_pbip = [str(p) for p in Path(s.project_path).glob("*.pbip")]
    existing_pbip += [str(p) for p in Path(s.project_path).glob("*/definition.pbip")]

target = None
if existing_pbip:
    card("Projets .pbip disponibles")
    choice = st.selectbox("Choisir un projet à auditer", existing_pbip)
    if st.button("Auditer ce projet", type="primary"):
        target = choice

if uploaded is not None:
    # L'upload peut être un fichier unique ; on suppose un dossier déjà sur disque
    st.info("Astuce : uploadez plutôt le dossier complet via votre explorateur, "
            "ou auditez un projet déjà généré ci-dessus.")
    st.stop()

if target:
    from agents.ai_auditor import AIAuditor
    try:
        audit = AIAuditor.audit(target)
        s.audit = audit
        st.success(f"✅ Audit terminé — score global : {audit['score_global']}/100")
    except Exception as e:
        st.error(f"Erreur d'audit : {e}")
        audit = None

if s.get("audit"):
    audit = s.audit
    card(f"Score global : {audit['score_global']}/100", badge="AUDIT")
    st.metric("Score global", audit["score_global"])

    dims = audit["dimensions"]
    cols = st.columns(4)
    with cols[0]:
        st.metric("Modèle", dims["modele"]["score"])
    with cols[1]:
        st.metric("DAX", dims["dax"]["score"])
    with cols[2]:
        st.metric("Design", dims["design"]["score"])
    with cols[3]:
        st.metric("Performance", dims["performance"]["score"])

    card("Résumé du projet", badge="RESUME")
    st.json(audit["resume"])

    for name, key in [("Modèle", "modele"), ("DAX", "dax"),
                      ("Design", "design"), ("Performance", "performance")]:
        if dims[key]["issues"]:
            st.markdown(f"**{name}** — points d'amélioration :")
            for iss in dims[key]["issues"]:
                st.markdown(f"- ⚠️ {iss}")

    if st.button("💡 Plan d'optimisation (IA)"):
        with st.spinner("Génération par l'IA..."):
            try:
                sug = AIAuditor.generate_optimization_suggestions(audit)
                st.markdown(sug)
            except Exception as e:
                st.error(f"Erreur IA : {e}")

    # Sauvegarde du rapport d'audit
    if s.get("project_path"):
        out_dir = Path(s.project_path) / "metadata"
        out_dir.mkdir(exist_ok=True)
        save = st.button("💾 Sauvegarder audit_report.json")
        if save:
            (out_dir / "audit_report.json").write_text(
                json.dumps(audit, ensure_ascii=False, indent=2), encoding="utf-8")
            st.info("audit_report.json sauvegardé dans metadata/.")

if st.button("⬅️ Retour Paramètres"):
    st.switch_page(PAGE_SETTINGS)
