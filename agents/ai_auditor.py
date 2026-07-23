"""AI Auditor — Phase 9 : audit et optimisation d'un projet Power BI existant.

Entrée : un dossier projet .pbip (généré par BI Architect AI ou externe).
Analyse : modèle sémantique (TMDL), report (definition.pbir), thème.
Sortie : audit_report.json avec scores par dimension + recommandations
         applicables + (option) suggestions IA.

Dimensions auditées :
- Modèle   : tables, colonnes, relations, mesures, clés manquantes.
- DAX      : mesures présentes, doublons, complexité.
- Design   : cohérence de la palette (theme.json), contraste.
- Performance : heuristiques (grandes tables, visuels multiples).
"""
from pathlib import Path
import json
import re
from core.ai_orchestrator import AIOrchestrator

orchestrator = AIOrchestrator()


class AIAuditor:
    # ------------------------------------------------------------------
    @staticmethod
    def _read_tmdl(path: Path) -> str:
        try:
            return path.read_text(encoding="utf-8")
        except Exception:
            return ""

    @staticmethod
    def _parse_model(tmdl_text: str) -> dict:
        tables = re.findall(r"table\s+'([^']+)'", tmdl_text)
        columns = re.findall(r"column\s+'([^']+)'", tmdl_text)
        measures = re.findall(r"measure\s+'([^']+)'", tmdl_text)
        relationships = re.findall(r"relationship\s+'([^']+)'", tmdl_text)
        return {
            "tables": tables,
            "columns": columns,
            "measures": measures,
            "relationships": relationships,
        }

    @staticmethod
    def _parse_report(pbir_text: str) -> dict:
        try:
            data = json.loads(pbir_text)
        except Exception:
            return {"pages": []}
        pages = data.get("report", {}).get("pages", [])
        n_visuals = sum(len(p.get("visualContainers", [])) for p in pages)
        return {"pages": [p.get("name") for p in pages], "n_visuals": n_visuals}

    @staticmethod
    def _audit_model(parsed: dict) -> dict:
        issues = []
        score = 100.0
        if not parsed["relationships"] and len(parsed["tables"]) > 1:
            issues.append("Aucune relation définie entre les tables (modèle plat).")
            score -= 25
        if len(parsed["measures"]) == 0:
            issues.append("Aucune mesure DAX : les calculs risquent d'être faits en surface.")
            score -= 15
        # Colonnes cachées recommandées pour les clés
        id_cols = [c for c in parsed["columns"] if c.lower().startswith("id")]
        if id_cols:
            issues.append(
                f"{len(id_cols)} colonne(s) de clé détectée(s) : "
                "idéalement masquées de la vue rapport."
            )
            score -= 5
        return {"score": max(0.0, score), "issues": issues}

    @staticmethod
    def _audit_dax(tmdl_text: str, parsed: dict) -> dict:
        issues = []
        score = 100.0
        # Détection de fonctions potentiellement lentes
        slow = ["CALCULATE", "FILTER", "EARLIER", "RELATEDTABLE"]
        found = [f for f in slow if f in tmdl_text]
        if found:
            issues.append(
                "Fonctions DAX potentiellement coûteuses détectées : " + ", ".join(found)
            )
            score -= 10 * len(found)
        if not parsed["measures"]:
            issues.append("Pas de mesure DAX à auditer.")
            score -= 20
        return {"score": max(0.0, score), "issues": issues}

    @staticmethod
    def _audit_design(theme: dict) -> dict:
        issues = []
        score = 100.0
        colors = theme.get("dataColors", [])
        if len(colors) < 2:
            issues.append("Palette de couleurs insuffisante.")
            score -= 30
        # Détection de doublons de couleurs
        if len(colors) != len(set(colors)):
            issues.append("Couleurs dupliquées dans la palette.")
            score -= 10
        if not theme.get("background") or not theme.get("foreground"):
            issues.append("Couleurs de fond/texte manquantes (lisibilité).")
            score -= 10
        return {"score": max(0.0, score), "issues": issues}

    @staticmethod
    def _audit_performance(parsed: dict, report: dict) -> dict:
        issues = []
        score = 100.0
        if report["n_visuals"] > 15:
            issues.append(
                f"{report['n_visuals']} visuels : risque de lenteur à l'ouverture."
            )
            score -= 10
        if len(parsed["tables"]) >= 1:
            issues.append(
                "Vérifiez les modes de stockage (Import vs DirectQuery) pour la performance."
            )
            score -= 5
        return {"score": max(0.0, score), "issues": issues}

    # ------------------------------------------------------------------
    @staticmethod
    def audit(pbip_path: str) -> dict:
        """Audite un projet .pbip complet. Renvoie audit_report.json."""
        root = Path(pbip_path)
        sm_dir = root / "semanticModel"
        report_dir = root / "report"
        theme_path = root / "theme.json"

        tmdl_text = AIAuditor._read_tmdl(sm_dir / "model.tmdl")
        parsed = AIAuditor._parse_model(tmdl_text)

        pbir_text = ""
        if (report_dir / "definition.pbir").exists():
            pbir_text = (report_dir / "definition.pbir").read_text(encoding="utf-8")
        report = AIAuditor._parse_report(pbir_text)

        theme = {}
        if theme_path.exists():
            try:
                theme = json.loads(theme_path.read_text(encoding="utf-8"))
            except Exception:
                theme = {}

        model_a = AIAuditor._audit_model(parsed)
        dax_a = AIAuditor._audit_dax(tmdl_text, parsed)
        design_a = AIAuditor._audit_design(theme)
        perf_a = AIAuditor._audit_performance(parsed, report)

        overall = round(
            (model_a["score"] + dax_a["score"] + design_a["score"] + perf_a["score"]) / 4, 1
        )

        return {
            "projet": root.name,
            "score_global": overall,
            "dimensions": {
                "modele": model_a,
                "dax": dax_a,
                "design": design_a,
                "performance": perf_a,
            },
            "resume": {
                "tables": len(parsed["tables"]),
                "colonnes": len(parsed["columns"]),
                "mesures_dax": len(parsed["measures"]),
                "relations": len(parsed["relationships"]),
                "pages": len(report["pages"]),
                "visuels": report["n_visuals"],
            },
        }

    @staticmethod
    def generate_optimization_suggestions(audit: dict) -> str:
        """Appel IA optionnel pour des recommandations d'optimisation."""
        prompt = f"""
Tu es un auditeur Power BI expert. Voici le rapport d'audit d'un projet :

{audit}

Propose un plan d'optimisation concret et priorisé (P0/P1/P2) :
- Corrections de modèle (relations, clés masquées, hiérarchies).
- Mesures DAX à ajouter / simplifier.
- Améliorations de design (palette, cohérence).
- Gains de performance.
Réponds de manière structurée et actionnable.
        """
        return orchestrator.generate(prompt, task_type="default")
