"""Page 4 — 📈 Modélisation (BI Architect Agent), Phase 4."""
from pathlib import Path
import json
import streamlit as st

from utils.session import init_session, set_current_page, PAGE_PROJET, PAGE_DATA_ENGINEER, PAGE_KPI_DAX
from utils.ui import render_page_header, render_sidebar, card

init_session()
set_current_page(__file__)
render_sidebar()
render_page_header("📈 Modélisation", "Architecture du modèle sémantique (BI Architect Agent)")

s = st.session_state
if not s.project_path:
    st.warning("Aucun projet actif.")
    if st.button("➡️ Aller au projet"):
        st.switch_page(PAGE_PROJET)
    st.stop()

if not s.data_sources:
    st.info("Aucune source chargée. Ajoutez des fichiers d'abord.")
    if st.button("➡️ Aller aux sources"):
        st.switch_page(PAGE_DATA_ENGINEER)
    st.stop()

# Charge les métadonnées disponibles (générées à l'étape Data Engineer)
data_dir = Path(s.project_path) / "data"
sources_meta = {}
for fname in s.data_sources:
    base = Path(fname).stem
    meta_path = data_dir / f"{base}_metadata.json"
    if meta_path.exists():
        sources_meta[fname] = json.loads(meta_path.read_text(encoding="utf-8"))

# Si les métadonnées manquent, on les reconstruit à la volée
if not sources_meta:
    from agents.ai_data_engineer import AIDataEngineer
    import pandas as pd
    for fname in s.data_sources:
        fp = data_dir / fname
        if fp.suffix == ".csv":
            df = pd.read_csv(fp)
        elif fp.suffix == ".xlsx":
            df = pd.read_excel(fp)
        else:
            continue
        sources_meta[fname] = AIDataEngineer.build_metadata(df, fname)


def do_modeling():
    from agents.bi_architect import BIArchitect
    model = BIArchitect.build_model(sources_meta, s.project_name or "")
    s.model = model
    # Sauvegarde dans projects/<projet>/metadata/model.json
    out_dir = Path(s.project_path) / "metadata"
    out_dir.mkdir(exist_ok=True)
    (out_dir / "model.json").write_text(
        json.dumps(model, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return model


if st.button("🏗️ Générer le modèle en étoile", type="primary"):
    try:
        model = do_modeling()
        st.success("✅ Modèle généré et sauvegardé (metadata/model.json).")
    except Exception as e:
        st.error(f"Erreur de modélisation : {e}")
        model = None

if s.get("model"):
    model = s.model
    card("Tables de faits", badge="FACT")
    st.write(model.get("facts"))
    card("Dimensions", badge="DIM")
    st.write(model.get("dimensions"))
    card("Granularité", badge="PK")
    st.write(model.get("granularite"))
    card("Relations", badge="JOIN")
    if model.get("relationships"):
        for r in model["relationships"]:
            st.markdown(
                f"`{r['from_table']}.{r['from_column']}` → "
                f"`{r['to_table']}.{r['to_column']}` "
                f"({r['cardinality']})"
            )
    else:
        st.info("Aucune relation inférée automatiquement (à préciser).")

    if st.button("💡 Suggestions d'amélioration (IA)"):
        from agents.bi_architect import BIArchitect
        with st.spinner("Analyse par l'IA..."):
            try:
                sug = BIArchitect.generate_model_suggestions(model)
                st.markdown(sug)
            except Exception as e:
                st.error(f"Erreur IA : {e}")

    if st.button("➡️ Continuer vers KPI & DAX", type="primary"):
        st.switch_page(PAGE_KPI_DAX)

if st.button("⬅️ Retour Prétraitement IA"):
    st.switch_page(PAGE_DATA_ENGINEER)
