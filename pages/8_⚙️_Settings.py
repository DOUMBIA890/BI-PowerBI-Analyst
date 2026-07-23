"""Page 8 — ⚙️ Paramètres (config projet, fournisseurs IA, journal)."""
import json
from pathlib import Path
import streamlit as st

from utils.session import init_session, set_current_page, PAGE_PROJET
from utils.ui import render_page_header, render_sidebar, card

init_session()
set_current_page(__file__)
render_sidebar()
render_page_header("⚙️ Paramètres", "Configuration du projet, fournisseurs IA et journal")

s = st.session_state
if not s.project_path:
    st.warning("Aucun projet actif.")
    if st.button("➡️ Aller au projet"):
        st.switch_page(PAGE_PROJET)
    st.stop()

card("Projet actif")
st.json({
    "project_name": s.project_name,
    "project_path": s.project_path,
    "data_sources": s.data_sources,
})

st.divider()
card("Fournisseurs IA")
config_path = Path("config/settings.json")
if config_path.exists():
    try:
        with open(config_path, "r") as f:
            cfg = json.load(f)
        providers = cfg.get("ai_providers", {})
        masked = {}
        for name, pcfg in providers.items():
            pc = dict(pcfg)
            if pcfg.get("api_key"):
                key = pcfg["api_key"]
                pc["api_key"] = "***" + key[-4:]
            masked[name] = pc
        st.json(masked)
    except Exception as e:
        st.error(f"Impossible de lire la config : {e}")

st.divider()
card("Journal d'activité")
log_path = Path("logs/app.log")
if log_path.exists():
    try:
        lines = log_path.read_text(encoding="utf-8", errors="ignore").splitlines()[-50:]
        st.code("\n".join(lines), language="text")
    except Exception:
        st.info("Journal vide.")
else:
    st.info("Aucun journal pour l'instant.")

if st.button("⬅️ Retour Projet"):
    st.switch_page(PAGE_PROJET)
