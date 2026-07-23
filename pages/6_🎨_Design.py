"""Page 6 — 🎨 Design (UX/UI Designer Agent), Phase 6."""
from pathlib import Path
import json
import streamlit as st

from utils.session import init_session, set_current_page, PAGE_PROJET, PAGE_KPI_DAX, PAGE_BUILDER
from utils.ui import render_page_header, render_sidebar, card

init_session()
set_current_page(__file__)
render_sidebar()
render_page_header("🎨 Design", "Thème, disposition et choix des visuels (UX/UI Designer)")

s = st.session_state
if not s.project_path:
    st.warning("Aucun projet actif.")
    if st.button("➡️ Aller au projet"):
        st.switch_page(PAGE_PROJET)
    st.stop()

# Compte les KPI pour dimensionner le layout
kpi_count = 4
kpi_path = Path(s.project_path) / "metadata" / "kpi_catalog.json"
if kpi_path.exists():
    kpi_count = max(1, len(json.loads(kpi_path.read_text(encoding="utf-8")).get("kpis", [])))

theme_choice = st.selectbox("Thème", ["Executive", "Dark", "Contoso"], index=0)


def do_design():
    from agents.ux_designer import UXDesigner, THEMES
    theme = UXDesigner.build_theme(theme_choice)
    layout = UXDesigner.build_layout(s.project_name or "", kpi_count=kpi_count)
    s.theme = theme
    s.layout = layout
    out_dir = Path(s.project_path) / "metadata"
    out_dir.mkdir(exist_ok=True)
    (out_dir / "theme.json").write_text(
        json.dumps(theme, ensure_ascii=False, indent=2), encoding="utf-8")
    (out_dir / "layout.json").write_text(
        json.dumps(layout, ensure_ascii=False, indent=2), encoding="utf-8")
    return theme, layout


if st.button("🎨 Générer le design", type="primary"):
    try:
        theme, layout = do_design()
        n_pages = len(layout["pages"])
        n_visuals = sum(len(p["visuals"]) for p in layout["pages"])
        st.success(f"✅ Thème '{theme['name']}' + {n_pages} page(s), {n_visuals} visuels "
                   "(metadata/theme.json, metadata/layout.json).")
    except Exception as e:
        st.error(f"Erreur : {e}")

if s.get("theme"):
    theme = s.theme
    card("Palette du thème", badge=theme["name"])
    cols = st.columns(len(theme["dataColors"]))
    for i, color in enumerate(theme["dataColors"]):
        with cols[i]:
            st.markdown(
                f'<div style="background:{color};height:48px;border-radius:8px;"></div>',
                unsafe_allow_html=True,
            )
            st.caption(color)

if s.get("layout"):
    layout = s.layout
    card("Disposition des pages", badge="LAYOUT")
    for page in layout["pages"]:
        st.markdown(f"**Page : {page['name']}** ({len(page['visuals'])} visuels)")
        with st.expander(f"Aperçu des visuels — {page['name']}"):
            st.json(page["visuals"])

    if st.button("💡 Suggestions de disposition (IA)"):
        from agents.ux_designer import UXDesigner
        model = {}
        mp = Path(s.project_path) / "metadata" / "model.json"
        kp = kpi_path.read_text(encoding="utf-8") if kpi_path.exists() else "{}"
        if mp.exists():
            model = json.loads(mp.read_text(encoding="utf-8"))
        with st.spinner("Génération par l'IA..."):
            try:
                sug = UXDesigner.generate_layout_suggestions(model, json.loads(kp))
                st.markdown(sug)
            except Exception as e:
                st.error(f"Erreur IA : {e}")

    if st.button("➡️ Continuer vers le Power BI Builder", type="primary"):
        st.switch_page(PAGE_BUILDER)

if st.button("⬅️ Retour KPI & DAX"):
    st.switch_page(PAGE_KPI_DAX)
