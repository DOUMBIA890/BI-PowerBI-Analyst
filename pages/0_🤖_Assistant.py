"""Page 0 — 🤖 Assistant BI (parcours simplifié pour les nouveaux venus).

Parcours en 3 étapes, sans jargon :
  1. Collez vos données
  2. Décrivez votre besoin en langage clair
  3. Lancez la génération -> le pipeline complet tourne (modèle, DAX, design,
     export .pbip) et l'assistant explique chaque étape en langage simple.

Les 9 pages détaillées restent accessibles via la barre latérale (mode expert).
"""

from pathlib import Path

import streamlit as st

from utils.session import (
    init_session,
    build_workflow_for,
    set_current_page,
    step_create_project,
    step_analyze_data,
    _load_sources_meta,
)
from utils.ui import render_page_header, render_sidebar, card
from core.assistant import Assistant
from core.advisor import Advisor

init_session()
set_current_page(__file__)
render_sidebar()

assistant = Assistant()

render_page_header(
    "🤖 Assistant BI",
    "Votre copilote Power BI : données brutes → tableau de bord, expliqué simplement.",
)

st.markdown(f"> {assistant.greeting()}")

s = st.session_state


def _show_explanation(step_name: str, result: dict):
    """Affiche l'explication pédagogique produite par l'assistant pour une étape."""
    expl = (result or {}).get("_assistant_explanation") if isinstance(result, dict) else None
    if expl:
        st.info(f"🤖 {expl}")


def _load_json(path):
    import json
    from pathlib import Path
    p = Path(path)
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def _show_advisor(project_path: str):
    """Affiche les suggestions de l'assistant et demande validation avant application."""
    import json
    from pathlib import Path

    meta = Path(project_path) / "metadata"
    model = _load_json(meta / "model.json")
    dax = _load_json(meta / "dax_measures.json")
    sources_meta = _load_sources_meta(project_path)

    advisor = Advisor()
    suggestions = advisor.suggest(model, dax, sources_meta)
    if not suggestions:
        return

    st.divider()
    card("💡 Conseils de l'assistant")
    st.caption(
        "L'assistant a détecté des améliorations possibles. Pour chacune, "
        "décidez si vous voulez l'appliquer — rien n'est fait sans votre accord."
    )

    choices = {}
    for sug in suggestions:
        with st.container(border=True):
            st.markdown(f"**{sug['title']}**")
            st.markdown(f"_{sug['explanation']}_")
            st.caption(f"Impact : {sug['impact']}")
            choices[sug["id"]] = st.radio(
                "Appliquer ?", ("Oui", "Non"), key=f"adv_{sug['id']}", horizontal=True
            )

    if st.button("✅ Appliquer mes choix", type="primary", key="btn_apply_adv"):
        accepted = [sid for sid, val in choices.items() if val == "Oui"]
        if not accepted:
            st.info("Aucune amélioration sélectionnée.")
            return
        with st.spinner("Application des améliorations choisies..."):
            # Recharger les livrables frais (ils ont pu être modifiés)
            model = _load_json(meta / "model.json")
            dax = _load_json(meta / "dax_measures.json")
            sources_meta = _load_sources_meta(project_path)
            summary = advisor.apply_accepted(
                project_path, accepted, model, dax, sources_meta
            )
        st.success("✅ Améliorations appliquées.")
        st.json(summary)


# ==========================
# Étape 1 — Données
# ==========================
st.divider()
card("Étape 1 · Vos données")
st.caption("Importez un ou plusieurs fichiers (CSV, Excel).")

project_name = st.text_input("Nom du projet", value=s.project_name or "MonProjet")
uploaded = st.file_uploader(
    "Glissez vos fichiers ici",
    type=["csv", "xlsx", "xls"],
    accept_multiple_files=True,
)

if st.button("Importer et préparer", type="primary", key="btn_import"):
    if not project_name:
        st.warning("Donnez un nom de projet.")
    elif not uploaded:
        st.warning("Ajoutez au moins un fichier.")
    else:
        s.project_name = project_name
        # Étape 1 + 2 : création projet + import fichiers
        step_create_project(project_name)
        data_dir = Path(s.project_path) / "data"
        data_dir.mkdir(parents=True, exist_ok=True)
        saved = []
        for f in uploaded:
            dest = data_dir / f.name
            dest.write_bytes(f.getbuffer())
            saved.append(f.name)
        s.data_sources = saved
        st.success(f"✅ {len(saved)} fichier(s) importé(s).")
        _show_explanation(
            "import_files",
            {"data_sources": saved, "project": project_name},
        )

        # Nettoyage AUTO + explication IA du traitement
        with st.spinner("Nettoyage automatique des données en cours..."):
            clean_res = step_analyze_data()
        cleaning_expl = (clean_res or {}).get("cleaning_explanations", {})
        for fname, expl in cleaning_expl.items():
            st.info(f"🤖 {fname} — {expl}")

# ==========================
# Étape 2 — Besoin métier
# ==========================
st.divider()
card("Étape 2 · Votre besoin")
st.caption("Décrivez ce que vous voulez comprendre — pas besoin de savoir faire du DAX.")
need = st.text_area(
    "Exemple : « Je veux voir l'évolution de mon chiffre d'affaires par mois "
    "et mes meilleurs produits. »",
    value="",
    height=100,
)
if need and st.button("Comprendre mon besoin", type="primary", key="btn_need"):
    with st.spinner("Traduction de votre besoin en indicateurs..."):
        expl = assistant.explain("dax", {"besoin_utilisateur": need})
    st.info(f"🤖 {expl}")

# ==========================
# Étape 3 — Génération du rapport
# ==========================
st.divider()
card("Étape 3 · Votre rapport")
st.caption("Lance la génération complète du tableau de bord Power BI.")

if st.button("🚀 Générer mon tableau de bord", type="primary", key="btn_generate"):
    if not s.project_path or not s.data_sources:
        st.warning("Commencez par importer vos données (Étape 1).")
    else:
        wf = build_workflow_for(s.project_name)
        steps = ["analyze_data", "build_model", "build_dax", "build_design", "build_pbip"]
        pbip_result = None
        try:
            for step in steps:
                with st.spinner(f"Étape en cours : {step}..."):
                    res = wf.run_step(step)
                # Explication pédagogique de l'étape (injectée par le workflow)
                if isinstance(res, dict) and "_assistant_explanation" in res:
                    st.info(f"🤖 {res['_assistant_explanation']}")
                if step == "build_pbip":
                    pbip_result = res
            st.balloons()
            pbip_path = (pbip_result or {}).get("pbip_path", "")
            st.success("✅ Tableau de bord généré !")
            if pbip_path:
                st.markdown(f"📂 Fichier généré : `{pbip_path}`")
                st.markdown(
                    "Ouvrez-le dans **Power BI Desktop** pour visualiser votre rapport."
                )

            # ---- Conseils de l'assistant (validation interactive) ----
            _show_advisor(s.project_path)
        except Exception as e:
            st.error(f"Erreur lors de la génération : {e}")

# ==========================
# Accès experts
# ==========================
st.divider()
with st.expander("🔧 Mode expert — piloter chaque étape moi-même"):
    st.markdown(
        "Les pages détaillées (Projet, Sources, Data Engineer, Modélisation, "
        "KPI & DAX, Design, Power BI Builder, Auditor) restent disponibles "
        "dans la barre latérale."
    )
