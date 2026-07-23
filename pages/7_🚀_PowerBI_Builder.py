"""Page 7 — 🚀 Power BI Builder (génération .pbip), Phase 7."""
from pathlib import Path
import json
import streamlit as st

from utils.session import init_session, set_current_page, PAGE_PROJET, PAGE_DESIGN, PAGE_SETTINGS
from utils.ui import render_page_header, render_sidebar, card

init_session()
set_current_page(__file__)
render_sidebar()
render_page_header("🚀 Power BI Builder", "Génération du projet .pbip complet")

s = st.session_state
if not s.project_path:
    st.warning("Aucun projet actif.")
    if st.button("➡️ Aller au projet"):
        st.switch_page(PAGE_PROJET)
    st.stop()

meta_dir = Path(s.project_path) / "metadata"


def _load(name):
    p = meta_dir / name
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


missing = [n for n in ("model.json", "dax_measures.json", "kpi_catalog.json",
                       "theme.json", "layout.json") if not (meta_dir / n).exists()]
if missing:
    st.warning("Livrables manquants : " + ", ".join(missing) +
               ". Complétez les étapes précédentes.")
    if st.button("⬅️ Retour Design"):
        st.switch_page(PAGE_DESIGN)
    st.stop()

# Recharge les métadonnées sources pour le TMDL
data_dir = Path(s.project_path) / "data"
sources_meta = {}
for fname in s.data_sources:
    base = Path(fname).stem
    mp = data_dir / f"{base}_metadata.json"
    if mp.exists():
        sources_meta[fname] = json.loads(mp.read_text(encoding="utf-8"))

model = _load("model.json")
dax = _load("dax_measures.json")
kpi = _load("kpi_catalog.json")
theme = _load("theme.json")
layout = _load("layout.json")


if st.button("🏗️ Générer le projet .pbip", type="primary"):
    try:
        from agents.powerbi_builder import PowerBIBuilder
        out = PowerBIBuilder.build(
            s.project_path, s.project_name or "Projet",
            sources_meta, model, dax, layout, theme,
        )
        s.pbip_path = str(out)
        st.success(f"✅ Projet généré : {out}")
    except Exception as e:
        st.error(f"Erreur de génération : {e}")

if s.get("pbip_path"):
    out = Path(s.pbip_path)
    card("Livrable généré", badge=".pbip")
    st.markdown(f"📁 `{out}`")
    # Affiche l'arborescence
    tree = []
    for p in sorted(out.rglob("*")):
        depth = len(p.relative_to(out).parts) - 1
        tree.append("    " * depth + ("📄 " if p.is_file() else "📂 ") + p.name)
    st.code("\n".join(tree), language="text")

    with st.expander("Aperçu model.tmdl"):
        tmdl = (out / "semanticModel" / "model.tmdl").read_text(encoding="utf-8")
        st.code(tmdl, language="text")

    with st.expander("Aperçu report (definition.pbir)"):
        rj = (out / "report" / "definition.pbir").read_text(encoding="utf-8")
        st.json(json.loads(rj))

    with st.expander("Aperçu d'une page (pages/*.json)"):
        page_files = sorted((out / "report" / "pages").glob("*.json"))
        if page_files:
            st.json(json.loads(page_files[0].read_text(encoding="utf-8")))

    st.info("Ouvrez le dossier du projet `.pbip` (ou le fichier `definition.pbip`) "
            "directement dans Power BI Desktop (mode 'Power BI Project').")

if st.button("⬅️ Retour Design"):
    st.switch_page(PAGE_DESIGN)
