"""État de session partagé entre toutes les pages Streamlit de BI Architect AI.

Objectif (Phase 1 - Étape 1.3) :
- Centraliser l'initialisation des gestionnaires (singletons).
- Exposer les fonctions d'étape du workflow réutilisables par les pages.
- Fournir des helpers de navigation entre pages.

Toute page commence par :
    from utils.session import init_session
    init_session()
"""
from pathlib import Path
import json
import pandas as pd

from core.project_manager import ProjectManager
from core.file_manager import FileManager
from core.database_manager import DatabaseManager
from core.workflow_engine import WorkflowEngine, WorkflowStep
from core.logger import logger

from agents.ai_data_engineer import AIDataEngineer
from agents.bi_architect import BIArchitect
from core.assistant import Assistant
from agents.bi_agent import BIAgent
from agents.ux_designer import UXDesigner
from agents.powerbi_builder import PowerBIBuilder



# Répertoire racine de l'app (où se trouve app.py)
APP_ROOT = Path(__file__).resolve().parent.parent

# Noms des pages natives Streamlit (doivent correspondre aux fichiers pages/*.py)
PAGE_PROJET = "pages/1_🏠_Projet.py"
PAGE_SOURCES = "pages/2_📂_Sources.py"
PAGE_DATA_ENGINEER = "pages/3_🧹_Data_Engineer.py"
PAGE_MODELISATION = "pages/4_📈_Modelisation.py"
PAGE_KPI_DAX = "pages/5_📊_KPI_DAX.py"
PAGE_DESIGN = "pages/6_🎨_Design.py"
PAGE_BUILDER = "pages/7_🚀_PowerBI_Builder.py"
PAGE_SETTINGS = "pages/8_⚙️_Settings.py"
PAGE_AUDITOR = "pages/9_🔍_Auditor.py"


def init_session():
    """Initialise les gestionnaires et l'état une seule fois par session."""
    if "pm" not in st_session():
        s = st_session()
        s.pm = ProjectManager()
        s.fm = FileManager()
        s.db = DatabaseManager()

    # État applicatif
    s = st_session()
    if "project_path" not in s:
        s.project_path = None
    if "project_name" not in s:
        s.project_name = None
    if "data_sources" not in s:
        s.data_sources = []
    if "analysis_results" not in s:
        s.analysis_results = {}
    if "workflow" not in s:
        s.workflow = None


def st_session():
    """Raccourci vers st.session_state (import lazy pour éviter import cyclique)."""
    import streamlit as st
    return st.session_state


# ==========================
# Fonctions d'étape du workflow (réutilisables par les pages)
# ==========================

def step_create_project(name: str, description: str = "") -> dict:
    """Étape 1 : création du projet (appelée par le workflow)."""
    s = st_session()
    path = s.pm.create_project(name, description)
    s.project_path = str(path)
    s.project_name = name
    return {"project_name": name, "project_path": str(path), "description": description}


def step_import_files(files) -> dict:
    """Étape 2 : import des fichiers dans data/ (lit project_path depuis session)."""
    s = st_session()
    saved = s.fm.add_files(files, s.project_path)
    s.data_sources = saved
    return {"data_sources": saved}


def step_analyze_data() -> dict:
    """Étape 3 : analyse + NETTOYAGE réel des fichiers présents dans data/."""
    s = st_session()
    data_dir = Path(s.project_path) / "data"
    results = {}
    cleaned_explanations = {}
    assistant = Assistant()
    for fname in s.data_sources:
        file_path = data_dir / fname
        if file_path.suffix.lower() not in [".csv", ".xlsx"]:
            continue
        df = pd.read_csv(file_path) if file_path.suffix == ".csv" else pd.read_excel(file_path)
        before = df.copy()

        # Détection des problèmes + plan de nettoyage
        quality_report = AIDataEngineer.build_quality_report(df, fname)
        cleaning_plan = AIDataEngineer.build_cleaning_plan(df, fname)

        # Application RÉELLE du nettoyage (nouveau)
        df_clean = AIDataEngineer.clean_data(df, cleaning_plan)
        df_clean.to_csv(file_path, index=False)  # écrase le brut par le nettoyé

        # Métadonnées + explication assistant
        metadata = AIDataEngineer.build_metadata(df_clean, fname)
        results[fname] = {
            "analysis": AIDataEngineer.analyze_dataframe(df_clean, fname),
            "quality_report": quality_report,
            "cleaning_plan": cleaning_plan,
            "metadata": metadata,
            "lignes_avant": len(before),
            "lignes_apres": len(df_clean),
        }
        # Assistant IA : explique ce qui a été nettoyé
        cleaned_explanations[fname] = assistant.explain(
            "cleaning",
            {
                "fichier": fname,
                "lignes_avant": len(before),
                "lignes_apres": len(df_clean),
                "problemes": quality_report.get("problemes", []),
            },
        )
    return {"analysis": results, "cleaning_explanations": cleaned_explanations}


def _save_json(project_path: str, name: str, data: dict):
    """Sauvegarde un livrable JSON dans metadata/ du projet."""
    meta_dir = Path(project_path) / "metadata"
    meta_dir.mkdir(parents=True, exist_ok=True)
    (meta_dir / name).write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def _load_sources_meta(project_path: str) -> dict:
    """Charge tous les *metadata.json de data/ pour le modèle et le builder."""
    data_dir = Path(project_path) / "data"
    sources_meta = {}
    if data_dir.exists():
        for f in data_dir.glob("*_metadata.json"):
            try:
                sources_meta[f.name] = json.loads(f.read_text(encoding="utf-8"))
            except Exception:
                continue
    return sources_meta


def _enrich_layout_fields(layout: dict, model: dict, sources_meta: dict) -> dict:
    """Ajoute des 'fields' (champs) à chaque visuel du layout pour que les
    graphiques se lient au modèle. Heuristique simple basée sur les tables/colonnes.
    """
    facts = model.get("facts", [])
    fact = facts[0] if facts else (list(sources_meta.keys())[0] if sources_meta else None)
    if not fact:
        return layout
    # Table de dimension pour l'axe catégorie (1re colonne non-id, non numérique)
    dim = None
    for t, meta in sources_meta.items():
        cols = meta.get("colonnes", [])
        if any(str(c["nom"]).lower() in ("date", "mois", "jour", "category") for c in cols):
            dim = t
            break
    axis_col = None
    if dim:
        for c in sources_meta[dim].get("colonnes", []):
            if str(c["nom"]).lower() in ("date", "mois", "jour", "category"):
                axis_col = c["nom"]
                break
    # 1re mesure DAX disponible (pour values)
    import agents.bi_agent as _ba
    dax = _ba.BIAgent.build_dax_measures(model, sources_meta)
    first_measure = dax["measures"][0]["nom"] if dax["measures"] else None

    for page in layout.get("pages", []):
        for v in page.get("visuals", []):
            if "fields" in v:
                continue
            fields = {}
            vtype = v.get("type", "Card")
            if vtype == "Card":
                if first_measure:
                    fields["values"] = [{"table": dax["measures"][0]["table"],
                                          "measure": first_measure}]
            else:
                if axis_col and dim:
                    fields["axis"] = {"table": dim, "column": axis_col}
                if first_measure:
                    fields["values"] = [{"table": dax["measures"][0]["table"],
                                          "measure": first_measure}]
                if vtype in ("DonutChart", "PieChart") and dim:
                    # légende = 1re colonne texte de la dim
                    for c in sources_meta[dim].get("colonnes", []):
                        if c["type"] == "object" and str(c["nom"]).lower() not in ("id",):
                            fields["legend"] = {"table": dim, "column": c["nom"]}
                            break
            if fields:
                v["fields"] = fields
    return layout


def step_build_model() -> dict:
    """Étape 4 : modèle sémantique (relations) à partir des metadata."""
    s = st_session()
    sources_meta = _load_sources_meta(s.project_path)
    model = BIArchitect.build_model(sources_meta, s.project_name or "Projet")
    _save_json(s.project_path, "model.json", model)
    return model


def step_build_dax() -> dict:
    """Étape 5 : mesures DAX + catalogue KPI."""
    s = st_session()
    sources_meta = _load_sources_meta(s.project_path)
    model = json.loads((Path(s.project_path) / "metadata" / "model.json").read_text(encoding="utf-8"))
    dax = BIAgent.build_dax_measures(model, sources_meta)
    kpi = BIAgent.build_kpi_catalog(model, dax)
    _save_json(s.project_path, "dax_measures.json", dax)
    _save_json(s.project_path, "kpi_catalog.json", kpi)
    return {"dax_measures": dax, "kpi_catalog": kpi}


def step_build_design() -> dict:
    """Étape 6 : thème + layout (avec champs auto-dérivés)."""
    s = st_session()
    sources_meta = _load_sources_meta(s.project_path)
    model = json.loads((Path(s.project_path) / "metadata" / "model.json").read_text(encoding="utf-8"))
    theme = UXDesigner.build_theme("Executive")
    layout = UXDesigner.build_layout(s.project_name or "Projet", kpi_count=4)
    layout = _enrich_layout_fields(layout, model, sources_meta)
    _save_json(s.project_path, "theme.json", theme)
    _save_json(s.project_path, "layout.json", layout)
    return {"theme": theme, "layout": layout}


def step_build_pbip() -> dict:
    """Étape 7 : génération du fichier .pbip complet."""
    s = st_session()
    sources_meta = _load_sources_meta(s.project_path)
    meta_dir = Path(s.project_path) / "metadata"

    def _load(name):
        p = meta_dir / name
        return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}

    out = PowerBIBuilder.build(
        project_path=s.project_path,
        project_name=s.project_name or "Projet",
        sources_meta=sources_meta,
        model=_load("model.json"),
        dax_measures=_load("dax_measures.json"),
        layout=_load("layout.json"),
        theme=_load("theme.json"),
    )
    return {"pbip_path": out}


def build_workflow_for(project_name: str):
    """Construit le WorkflowEngine complet pour un projet donné."""
    s = st_session()
    wf = WorkflowEngine(f"projects/{project_name}")
    wf.add_step(WorkflowStep("create_project", step_create_project))
    wf.add_step(WorkflowStep("import_files", step_import_files, depends_on=["create_project"]))
    wf.add_step(WorkflowStep("analyze_data", step_analyze_data, depends_on=["import_files"]))
    wf.add_step(WorkflowStep("build_model", step_build_model, depends_on=["analyze_data"]))
    wf.add_step(WorkflowStep("build_dax", step_build_dax, depends_on=["build_model"]))
    wf.add_step(WorkflowStep("build_design", step_build_design, depends_on=["build_dax"]))
    wf.add_step(WorkflowStep("build_pbip", step_build_pbip, depends_on=["build_design"]))
    s.workflow = wf
    return wf


def goto_next(page_current: str):
    """Renvoie la page suivante dans l'ordre défini (helper de navigation)."""
    order = [
        PAGE_PROJET,
        PAGE_SOURCES,
        PAGE_DATA_ENGINEER,
        PAGE_MODELISATION,
        PAGE_KPI_DAX,
        PAGE_DESIGN,
        PAGE_BUILDER,
        PAGE_SETTINGS,
    ]
    try:
        idx = order.index(page_current)
        return order[min(idx + 1, len(order) - 1)]
    except ValueError:
        return order[0]


def set_current_page(path: str):
    """Mémorise la page active pour la barre latérale (ui.render_sidebar)."""
    st_session()["_current_page"] = path


def list_existing_projects():
    """Retourne la liste des dossiers projets existants sous projects/."""
    root = Path("projects")
    if not root.exists():
        return []
    return sorted([p.name for p in root.iterdir() if p.is_dir()])
