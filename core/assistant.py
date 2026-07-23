"""Couche "assistant" : explique au nouveau venu ce que fait le pipeline.

Objectif produit : un assistant BI pour Power BI qui facilite la tâche aux
nouveaux arrivants. La génération de fichiers (.pbip, DAX, modèle) ne suffit
pas — il faut *accompagner* : dire POURQUOI un choix a été fait, en langage
clair, sans jargon.

Ce module utilise l'AIOrchestrator (routing "expert_powerbi") pour produire
des explications pédagogiques à chaque phase du workflow.
"""

import json

from core.ai_orchestrator import AIOrchestrator

# Phase -> libellé compréhensible par un débutant
PHASE_LABELS = {
    "sources": "Import des données",
    "cleaning": "Nettoyage des données",
    "modeling": "Modèle de données (relations)",
    "dax": "Mesures (calculs DAX)",
    "design": "Mise en forme du rapport",
    "build": "Génération du fichier Power BI",
    "audit": "Vérification finale",
}

_ASSISTANT_SYSTEM = (
    "Tu es un mentor Power BI bienveillant qui explique à un DÉBUTANT ce qui "
    "vient de se passer dans son projet. Tu ne refais pas le travail technique : "
    "tu EXPLIQUES le résultat de façon simple, claire, et rassurante.\n"
    "Règles :\n"
    "- 3 à 5 phrases maximum.\n"
    "- Vocabulaire grand public (évite le jargon, ou explique-le entre parenthèses).\n"
    "- Mets en avant LE choix principal et POURQUOI il aide l'utilisateur.\n"
    "- Termine par un conseil pratique ou une prochaine étape."
)


class Assistant:
    """Génère des explications pédagogiques pour chaque livrable du pipeline."""

    def __init__(self):
        self._orchestrator = AIOrchestrator()

    def explain(self, phase: str, payload: dict) -> str:
        """Retourne une explication claire du livrable `payload` pour `phase`.

        `payload` contient les infos techniques (ex. tables, relations, mesures).
        """
        label = PHASE_LABELS.get(phase, phase)
        prompt = (
            f"Phase : {label}.\n"
            f"Livrable produit (données techniques) :\n"
            f"{self._summarize(payload)}\n\n"
            "Explique à un débutant ce que ce livrable représente et pourquoi "
            "c'est utile pour son tableau de bord Power BI."
        )
        try:
            return self._orchestrator.generate(
                prompt, task_type="expert_powerbi"
            ).strip()
        except Exception as exc:  # jamais bloquant : l'assistant n'arrête pas le pipeline
            return (
                f"[{label}] (explication indisponible : {exc})"
            )

    @staticmethod
    def _summarize(payload: dict) -> str:
        """Réduit le payload technique à l'essentiel pour le prompt."""
        try:
            return json.dumps(payload, ensure_ascii=False, indent=2)[:1500]
        except Exception:
            return str(payload)[:1500]

    def greeting(self) -> str:
        """Message d'accueil du nouvel utilisateur."""
        return (
            "Bonjour ! Je suis votre assistant BI. Donnez-moi vos données, "
            "et je construis un tableau de bord Power BI prêt à l'emploi. "
            "À chaque étape, je vous explique ce que je fais en langage simple."
        )
