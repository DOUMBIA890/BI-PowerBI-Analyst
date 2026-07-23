"""UX/UI Designer Agent — Phase 6 : thème et disposition du rapport.

Objectif : générer les livrables de design consommables par le Power BI Builder :
- theme.json  : thème Power BI (couleurs, polices, visualStyles).
- layout.json : structure des pages et disposition des visuels
                 (type, x, y, width, height) — tel que décrit dans la vision.

Stratégie : catalogue de thèmes prédéfinis + génération de layout basée sur le
nombre de KPI / faits détectés. Suggestions IA optionnelles.
"""
import json
from core.ai_orchestrator import AIOrchestrator

orchestrator = AIOrchestrator()

THEMES = {
    "Executive": {
        "name": "Executive",
        "dataColors": ["#4F8CFF", "#22D3EE", "#3FB950", "#D29922", "#BC8CFF", "#F778BA"],
        "background": "#FFFFFF",
        "foreground": "#0F1419",
        "tableAccent": "#4F8CFF",
        "good": "#3FB950",
        "neutral": "#8B98A5",
        "bad": "#F85149",
        "fontFamily": "Segoe UI",
        "visualStyles": {
            "*": {"*": {"background": [{"show": True, "color": {"solid": {"color": "#F4F6FB"}}}]}}
        },
    },
    "Dark": {
        "name": "Dark",
        "dataColors": ["#4F8CFF", "#22D3EE", "#3FB950", "#D29922", "#BC8CFF", "#F778BA"],
        "background": "#0F1419",
        "foreground": "#E6EDF3",
        "tableAccent": "#22D3EE",
        "good": "#3FB950",
        "neutral": "#8B98A5",
        "bad": "#F85149",
        "fontFamily": "Segoe UI",
        "visualStyles": {
            "*": {"*": {"background": [{"show": True, "color": {"solid": {"color": "#1A2230"}}}]}}
        },
    },
    "Contoso": {
        "name": "Contoso",
        "dataColors": ["#01B8AA", "#374649", "#FD625E", "#F2C80F", "#5F6B6D", "#8AD4EB"],
        "background": "#FFFFFF",
        "foreground": "#374649",
        "tableAccent": "#01B8AA",
        "good": "#01B8AA",
        "neutral": "#8AD4EB",
        "bad": "#FD625E",
        "fontFamily": "Segoe UI",
    },
}


class UXDesigner:
    @staticmethod
    def build_theme(theme_name: str = "Executive") -> dict:
        """Retourne le theme.json pour un thème prédéfini."""
        return THEMES.get(theme_name, THEMES["Executive"])

    @staticmethod
    def build_layout(project_name: str, kpi_count: int = 4, fact_count: int = 1) -> dict:
        """Génère layout.json : pages + disposition des visuels.

        Page Executive type (selon la vision) :
          Ligne 1 : N KPI (cartes)
          Ligne 2 : évolution (LineChart)
          Ligne 3 : Top produits (BarChart) + répartition géo (Map/Donut)
        """
        # Ligne 1 — KPI cards
        kpi_cards = []
        card_w = 250
        gap = 20
        start_x = 30
        for i in range(max(kpi_count, 1)):
            kpi_cards.append({
                "type": "Card",
                "x": start_x + i * (card_w + gap),
                "y": 40,
                "width": card_w,
                "height": 120,
            })
        # Ligne 2 — évolution CA
        line_y = 200
        visuals = list(kpi_cards) + [
            {
                "type": "LineChart",
                "x": 30,
                "y": line_y,
                "width": 900,
                "height": 320,
                "title": "Évolution du CA",
            },
            {
                "type": "BarChart",
                "x": 30,
                "y": line_y + 360,
                "width": 450,
                "height": 320,
                "title": "Top Produits",
            },
            {
                "type": "DonutChart",
                "x": 510,
                "y": line_y + 360,
                "width": 420,
                "height": 320,
                "title": "Répartition géographique",
            },
        ]
        return {
            "project": project_name,
            "pages": [
                {
                    "name": "Executive",
                    "visuals": visuals,
                }
            ],
        }

    @staticmethod
    def generate_layout_suggestions(model: dict, kpi_catalog: dict) -> str:
        """Appel IA optionnel pour affiner la disposition / le choix des visuels."""
        prompt = f"""
Tu es un UX designer Power BI. Voici le modèle et les KPI disponibles :

MODELE:
{model}

KPI:
{kpi_catalog}

Propose une structure de pages pertinente (ex. Executive, Finance, Ventes)
avec, pour chaque page, la liste des visuels recommandés et leur rôle.
Réponds de manière structurée.
        """
        return orchestrator.generate(prompt, task_type="design")
