"""Agent conseiller interactif (Advisor).

Rôle : après génération du modèle, propose des améliorations (suggestions de
l'IA) à l'utilisateur, les EXPLIQUE en langage clair, DEMANDE validation, et
n'APPLIQUE que celles qui sont acceptées. C'est le cœur de l'assistant BI :
il conseille, il ne décide pas à la place du débutant.

Flux :
  1. suggest(model, dax_measures) -> liste de Suggestion (id, titre, explication, impact)
  2. L'UI affiche chaque suggestion + boutons Oui/Non
  3. apply_accepted(project_path, accepted_ids) -> modifie les livrables + régénère le .pbip
"""

import json
from pathlib import Path

# Catalogue d'améliorations possibles, chacune avec explication + impact.
# `detect(model, dax)` retourne True si l'amélioration est applicable et pas déjà faite.
# `apply(model, dax, sources_meta)` applique l'amélioration en place.
IMPROVEMENTS = []


def _improvement(detect_fn, apply_fn):
    IMPROVEMENTS.append({"detect": detect_fn, "apply": apply_fn})


def _has_date_col(model, sources_meta):
    """Détecte une colonne date (type ou nom) dans une table de fait."""
    DATE_KW = ("date", "jour", "mois", "annee", "année", "time")
    for fact in model.get("facts", []):
        meta = sources_meta.get(f"{Path(fact).stem}_metadata.json") or \
               sources_meta.get(fact)
        if not meta:
            continue
        for c in meta.get("colonnes", []):
            ct = str(c.get("type", "")).lower()
            cn = str(c["nom"]).lower()
            if ct in ("datetime64", "date", "datetime") or any(k in cn for k in DATE_KW):
                return True
    return False


def _date_already(model):
    return model.get("date_table") is not None


def _apply_date(model, dax, sources_meta):
    if _date_already(model):
        return
    # Trouve la 1re colonne date d'un fait
    DATE_KW = ("date", "jour", "mois", "annee", "année", "time")
    fact_col = None
    fact_table = None
    for fact in model.get("facts", []):
        meta = sources_meta.get(f"{Path(fact).stem}_metadata.json") or sources_meta.get(fact)
        if not meta:
            continue
        for c in meta.get("colonnes", []):
            ct = str(c.get("type", "")).lower()
            cn = str(c["nom"]).lower()
            if ct in ("datetime64", "date", "datetime") or any(k in cn for k in DATE_KW):
                fact_col, fact_table = c["nom"], fact
                break
        if fact_col:
            break
    if not fact_col:
        return
    dims = list(model.get("dimensions", []))
    if "Dates.csv" not in dims:
        dims.append("Dates.csv")
    model["dimensions"] = dims
    model["date_table"] = "Dates.csv"
    model["date_columns"] = [fact_col]
    rel = model.get("relationships", [])
    rel.append({
        "from_table": fact_table, "from_column": fact_col,
        "to_table": "Dates.csv", "to_column": "Date",
        "cardinality": "many-to-one",
    })
    model["relationships"] = rel


def _hidden_ok(model, sources_meta):
    """True si toutes les clés id/*_id sont déjà masquées (on ne peut pas le voir
    depuis model.json seul ; on suppose applicable par défaut)."""
    return False  # toujours proposable


def _apply_hidden(model, dax, sources_meta):
    # Le masquage est géré à l'export (powerbi_builder._tmdl_tables) ; ici on
    # marque la intention dans model.json pour traçabilité.
    model.setdefault("options", {})["hide_technical_keys"] = True


def _measures_ok(model, dax):
    measures = dax.get("measures", [])
    return any("DISTINCTCOUNT" in m.get("expression", "") for m in measures)


def _apply_measures(model, dax, sources_meta):
    # Les mesures de base sont générées par BIAgent.build_dax_measures ; on
    # s'assure que l'option est activée dans model.json.
    model.setdefault("options", {})["base_measures"] = True


# Enregistrement des améliorations
_improvement(_has_date_col_and_not_done := (lambda m, s: _has_date_col(m, s) and not _date_already(m)),
             _apply_date)
_improvement(lambda m, s: _hidden_ok(m, s), _apply_hidden)
_improvement(lambda m, d: _has_date_col(m, d) and not _measures_ok(m, d), _apply_measures)


class Advisor:
    """Génère et applique les suggestions de façon interactive."""

    def suggest(self, model: dict, dax_measures: dict, sources_meta: dict) -> list:
        """Retourne la liste des suggestions applicables, avec explication."""
        suggestions = []
        # (id, titre, explication, impact) pour chaque amélioration détectée
        infos = [
            ("date_table",
             "Ajouter une table Date dédiée",
             "Vos données contiennent des dates. Une table Date centralise le temps "
             "et permet des analyses par année / mois / jour sans effort.",
             "Crée 'Dates.csv' + une relation vers vos faits + hiérarchie Temps."),
            ("hide_keys",
             "Masquer les colonnes techniques (id, *_id)",
             "Les clés like 'id' ou 'employe_id' servent à relier les tables mais "
             "encombrent l'interface du débutant. Les masquer évite les erreurs.",
             "Ces colonnes deviennent invisibles dans le champ du rapport."),
            ("base_measures",
             "Créer les mesures DAX de base",
             "Des mesures toutes prêtes (Total, Moyenne, Nb entités) évitent d'écrire "
             "du DAX à la main pour les calculs les plus courants.",
             "Ajoute SUM/AVERAGE/DISTINCTCOUNT sur vos colonnes pertinentes."),
        ]
        for i, (fn_detect, fn_apply) in enumerate(IMPROVEMENTS):
            try:
                if fn_detect(model, sources_meta):
                    sid, title, expl, impact = infos[i]
                    suggestions.append({
                        "id": sid, "title": title,
                        "explanation": expl, "impact": impact,
                    })
            except Exception:
                continue
        return suggestions

    def apply_accepted(self, project_path: str, accepted_ids: list,
                      model: dict, dax_measures: dict, sources_meta: dict) -> dict:
        """Applique uniquement les améliorations dont l'id est dans accepted_ids.

        Modifie model.json / dax_measures.json puis régénère le .pbip.
        Retourne un résumé des actions effectuées.
        """
        id_to_idx = {"date_table": 0, "hide_keys": 1, "base_measures": 2}
        applied = []
        for sid in accepted_ids:
            idx = id_to_idx.get(sid)
            if idx is None:
                continue
            fn_apply = IMPROVEMENTS[idx]["apply"]
            try:
                fn_apply(model, dax_measures, sources_meta)
                applied.append(sid)
            except Exception as exc:
                applied.append(f"{sid}:ERREUR:{exc}")

        # Sauvegarde des livrables
        meta_dir = Path(project_path) / "metadata"
        meta_dir.mkdir(parents=True, exist_ok=True)
        (meta_dir / "model.json").write_text(
            json.dumps(model, ensure_ascii=False, indent=2), encoding="utf-8")
        (meta_dir / "dax_measures.json").write_text(
            json.dumps(dax_measures, ensure_ascii=False, indent=2), encoding="utf-8")

        # Régénération du .pbip
        from agents.powerbi_builder import PowerBIBuilder
        from utils.session import _load_sources_meta
        sm = _load_sources_meta(project_path)
        layout = json.loads((meta_dir / "layout.json").read_text(encoding="utf-8")) if (meta_dir / "layout.json").exists() else {}
        theme = json.loads((meta_dir / "theme.json").read_text(encoding="utf-8")) if (meta_dir / "theme.json").exists() else {}
        pbip = PowerBIBuilder.build(
            project_path=project_path,
            project_name=model.get("project", "Projet"),
            sources_meta=sm,
            model=model,
            dax_measures=dax_measures,
            layout=layout,
            theme=theme,
        )
        return {"applied": applied, "pbip_path": pbip}
