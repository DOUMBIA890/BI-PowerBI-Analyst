"""Business Intelligence Agent — Phase 5 : KPI & mesures DAX.

Objectif : à partir du model.json (schéma en étoile), générer :
- kpi_catalog.json : catalogue métier des indicateurs (objectif, format, sens).
- dax_measures.json : mesures DAX concrètes (expression, table, format).

Stratégie : heuristiques déterministes pour les mesures de base (Total, Nb,
Moyenne) + suggestions IA optionnelles pour les KPI métier.
"""
from pathlib import Path
import json
from core.ai_orchestrator import AIOrchestrator

orchestrator = AIOrchestrator()


class BIAgent:
    @staticmethod
    def _measures_for_fact(fact_table: str, meta: dict) -> list:
        """Génère les mesures DAX de base pour une table de fait.

        Dérive des mesures sémantiques depuis les colonnes réelles :
        - SUM sur les colonnes quantitatives (montant, prix, jours, durée...)
        - AVERAGE sur les colonnes de note/score
        - DISTINCTCOUNT sur la clé 'id' (comptage d'entités uniques)
        - COUNTROWS en complément
        """
        cols = meta.get("colonnes", []) if meta else []
        measures = []
        numeric = [c for c in cols if c["type"] in ("int64", "float64")
                   and not str(c["nom"]).lower().endswith("_id")]

        # Mots-clés sémantiques
        avg_keywords = ("note", "score", "rating", "taux", "average", "moyenne")
        sum_keywords = ("montant", "prix", "price", "total", "jour", "duree",
                        "duration", "quantite", "amount", "ca", "salaire")

        for c in numeric:
            cname = c["nom"].lower()
            label = c["nom"].title().replace("_", " ")
            is_avg = any(k in cname for k in avg_keywords)
            is_sum = any(k in cname for k in sum_keywords)

            if is_avg:
                measures.append({
                    "nom": f"{label} Moyenne",
                    "table": fact_table,
                    "expression": f"AVERAGE('{fact_table}'[{c['nom']}])",
                    "format": "#,##0.00",
                    "type": "moyenne",
                })
            if is_sum:
                measures.append({
                    "nom": f"Total {label}",
                    "table": fact_table,
                    "expression": f"SUM('{fact_table}'[{c['nom']}])",
                    "format": "#,##0.00",
                    "type": "somme",
                })

        # Comptage d'entités uniques via la clé 'id' (si présente)
        id_col = next((c["nom"] for c in cols if c["nom"].lower() == "id"), None)
        if id_col:
            measures.append({
                "nom": "Nb Entités",
                "table": fact_table,
                "expression": f"DISTINCTCOUNT('{fact_table}'[{id_col}])",
                "format": "#,##0",
                "type": "comptage_unique",
            })
        # Comptage de lignes (transactions)
        measures.append({
            "nom": "Nb Lignes",
            "table": fact_table,
            "expression": f"COUNTROWS('{fact_table}')",
            "format": "#,##0",
            "type": "comptage",
        })
        return measures

    @staticmethod
    def build_dax_measures(model: dict, sources_meta: dict) -> dict:
        """Construit dax_measures.json pour toutes les tables de faits."""
        all_measures = []
        for fact in model.get("facts", []):
            meta = sources_meta.get(fact, {})
            all_measures.extend(BIAgent._measures_for_fact(fact, meta))
        return {
            "project": model.get("project", ""),
            "measures": all_measures,
        }

    @staticmethod
    def build_kpi_catalog(model: dict, dax_measures: dict) -> dict:
        """Construit kpi_catalog.json à partir des mesures générées."""
        kpis = []
        for m in dax_measures.get("measures", []):
            if m["type"] in ("somme", "comptage"):
                kpis.append({
                    "nom": m["nom"],
                    "mesure_dax": m["nom"],
                    "table": m["table"],
                    "format": m["format"],
                    "objectif": None,
                    "sens": "plus est mieux" if m["type"] != "comptage" else "contexte",
                    "description": f"Indicateur agrégé : {m['nom']}.",
                })
        return {
            "project": model.get("project", ""),
            "kpis": kpis,
        }

    @staticmethod
    def generate_kpi_suggestions(model: dict, measures: dict) -> str:
        """Appel IA optionnel pour proposer des KPI métier avancés."""
        prompt = f"""
Tu es un consultant BI. Voici un modèle en étoile et des mesures DAX de base :

MODELE:
{model}

MESURES:
{measures}

Propose 5 à 8 KPI métier pertinents (ex. Taux de remise moyen, Panier moyen,
Répartition par catégorie) avec la mesure DAX associée et le format d'affichage.
Réponds de manière structurée (une ligne par KPI).
        """
        return orchestrator.generate(prompt, task_type="kpi")
