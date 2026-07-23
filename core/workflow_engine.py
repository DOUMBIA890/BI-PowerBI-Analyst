import json
from pathlib import Path
from datetime import datetime
from core.logger import logger  # sera créé juste après

class WorkflowStep:
    def __init__(self, name: str, func, depends_on=None):
        self.name = name
        self.func = func
        self.depends_on = depends_on or []
        self.output = None

class WorkflowEngine:
    def __init__(self, project_path: str):
        self.project_path = Path(project_path)
        self.state_file = self.project_path / "metadata" / "workflow_state.json"
        self.steps = {}
        self.results = {}
        self._assistant = None
        self._load_state()

    # Mappe un nom d'étape du workflow vers une phase "assistant" compréhensible
    STEP_TO_PHASE = {
        "create_project": "sources",
        "import_files": "sources",
        "analyze_data": "cleaning",
        "build_model": "modeling",
        "build_dax": "dax",
        "build_design": "design",
        "build_pbip": "build",
    }

    def add_step(self, step: WorkflowStep):
        self.steps[step.name] = step

    def run_step(self, step_name: str, *args, **kwargs):
        if step_name in self.results and self.results[step_name] is not None:
            return self.results[step_name]  # déjà exécuté, on reprend

        step = self.steps[step_name]
        # Exécute les dépendances d'abord
        for dep in step.depends_on:
            if dep not in self.results:
                self.run_step(dep)

        logger.info(f"Exécution de l'étape : {step_name}")
        result = step.func(*args, **kwargs)

        # Couche assistant : explique le livrable au nouveau venu (non bloquant)
        result = self._attach_explanation(step_name, result)

        self.results[step_name] = result
        self._save_state()
        return result

    def _attach_explanation(self, step_name: str, result):
        """Génère et stocke une explication pédagogique dans le résultat d'étape."""
        phase = self.STEP_TO_PHASE.get(step_name)
        if not phase:
            return result
        try:
            from core.assistant import Assistant
            if self._assistant is None:
                self._assistant = Assistant()
            explanation = self._assistant.explain(phase, result or {})
            if isinstance(result, dict):
                result = dict(result)
                result["_assistant_explanation"] = explanation
            else:
                result = {"value": result, "_assistant_explanation": explanation}
        except Exception as exc:
            logger.warning(f"Assistant indisponible pour {step_name} : {exc}")
            if isinstance(result, dict):
                result = dict(result)
                result["_assistant_explanation"] = f"(explication indisponible : {exc})"
        return result

    def _load_state(self):
        if self.state_file.exists():
            with open(self.state_file, "r") as f:
                self.results = json.load(f)

    def _save_state(self):
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.state_file, "w") as f:
            json.dump(self.results, f, indent=2, default=str)