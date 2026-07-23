"""BI Architect Agent — Phase 4 : modélisation du modèle sémantique Power BI.

Objectif : à partir des fichiers sources (métadonnées), proposer un schéma en
étoile : tables de faits, dimensions, relations et granularité, exporté sous
forme de model.json (consommable plus tard par le générateur TMDL).

Stratégie déterministe (heuristiques) + suggestion IA optionnelle :
- Une table contenant une colonne de type 'id' numérique ÉLEVÉ et plusieurs
  mesures (float/int) est candidate "fait".
- Les autres tables sont des "dimensions".
- Les relations sont inférées par similarité de noms de colonnes
  (ex. id_produit / produit_id).
"""
from pathlib import Path
import json
import pandas as pd
from core.ai_orchestrator import AIOrchestrator

orchestrator = AIOrchestrator()


class BIArchitect:
    @staticmethod
    def _table_stem(name: str) -> str:
        """Nom de table sans extension : 'Sales_lines.csv' -> 'Sales_lines'."""
        return Path(name).stem

    @staticmethod
    def _classify_tables(sources_meta: dict):
        """Renvoie (facts, dimensions) à partir des métadonnées.

        Approche déterministe et FIABLE pour peu de tables (n <= ~12) :
        on énumère TOUS les schémas possibles (chaque table = fait OU dim),
        on score chacun, et on garde le meilleur. Pas d'heuristique
        devinette — on choisit le schéma qui maximise les critères d'un
        schéma en étoile correct.

        Critères de score :
          +3  chaque FAIT a >=1 mesure d'agrégation (montant/qte/note/jours/nb)
          -5  un FAIT sans aucune mesure (clairement pas un fait)
          +2  chaque DIMENSION a une PK 'id' (entité) OU est la table Date
          -3  une DIMENSION sans PK (clairement pas une entité de référence)
          +1  la table Date est créée quand une colonne date existe
          -2  chaîne de relations inutile (un fait pointe vers une dim qui
               pointe elle-même vers une autre dim pour la même info)
        """
        from itertools import product

        names = list(sources_meta.keys())
        if not names:
            return [], []

        def cols_of(name):
            return sources_meta[name].get("colonnes", [])

        AGG_KW = ("montant", "quantite", "quantité", "nombre", "nb", "total",
                  "prix", "salaire", "note", "ca", "montant_total", "qte")

        def fk_cols(name):
            return [c["nom"] for c in cols_of(name)
                    if str(c["nom"]).lower().endswith("_id")]

        def measures(name):
            """Une MESURE DE FAIT n'existe que dans une table ÉVÉNEMENT
            (qui référence une autre table via une FK). Un attribut d'entité
            (ex. salaire_annuel d'un employé) n'est PAS une mesure de fait
            même s'il est numérique — on ne l'agrège pas sur un événement.
            """
            if not fk_cols(name):
                return []
            out = []
            for c in cols_of(name):
                cn = str(c["nom"]).lower()
                ct = str(c.get("type", "")).lower()
                if cn.endswith("_id") or cn == "id":
                    continue
                if ct in ("int64", "float64") or any(k in cn for k in AGG_KW):
                    out.append(c["nom"])
            return out

        def has_pk(name):
            return any(str(c["nom"]).lower() == "id" for c in cols_of(name))

        DATE_KW = ("date", "jour", "mois", "annee", "année", "time", "periode")
        def has_date(name):
            return any(
                (str(c.get("type", "")).lower() in ("datetime64", "date", "datetime"))
                or any(k in str(c["nom"]).lower() for k in DATE_KW)
                for c in cols_of(name)
            )

        # Noms d'entités du monde réel : ces tables décrivent des OBJETS
        # stables (une ligne = une chose), jamais un événement à agréger.
        ENTITY_KW = ("employe", "employee", "client", "produit", "product",
                     "departement", "department", "categorie", "category",
                     "fournisseur", "supplier", "region", "pays", "country",
                     "magasin", "store", "client")

        def is_entity_name(name):
            stem = BIArchitect._table_stem(name).lower()
            return any(k in stem for k in ENTITY_KW)

        def score(facts, dims):
            s = 0
            for f in facts:
                m = measures(f)
                s += 3 if m else -5
            for d in dims:
                if d == "Dates.csv":
                    s += 2
                elif has_pk(d) and is_entity_name(d):
                    # Vraie entité de référence (employé, produit...) : bonus.
                    s += 4
                elif has_pk(d):
                    s += 2
                else:
                    s -= 3
            # table Date présente si une date existe quelque part
            if any(has_date(n) for n in names):
                if "Dates.csv" in dims:
                    s += 1
                else:
                    s -= 1
            # pénalise une dim qui a des mesures (signe qu'elle devrait être fait)
            for d in dims:
                if d == "Dates.csv":
                    continue
                if measures(d):
                    s -= 2
            return s

        best = None
        best_score = float("-inf")
        # Contrainte forte : une table dont le nom est une ENTITÉ métier
        # connue (employé, produit, département...) est TOUJOURS une
        # dimension, même si elle a une FK et un champ numérique (salaire).
        # On l'exclut de l'énumération des faits. Le reste est énuméré
        # exhaustivement (2^k combinaisons) et tranché par le score.
        entity_tables = [n for n in names if is_entity_name(n)]
        event_tables = [n for n in names if n not in entity_tables]
        for combo in product([False, True], repeat=len(event_tables)):
            facts = [n for n, is_fact in zip(event_tables, combo) if is_fact]
            dims = list(entity_tables) + [n for n, is_fact in zip(event_tables, combo) if not is_fact]
            # La table Date n'existe pas dans les sources : on l'ajoute
            # comme dimension candidate si une date est présente.
            if any(has_date(n) for n in names) and "Dates.csv" not in dims:
                dims = dims + ["Dates.csv"]
            sc = score(facts, dims)
            if sc > best_score:
                best_score = sc
                best = (facts, dims)
        return best

    @staticmethod
    def _infer_relationships(facts, dims, sources_meta):
        """Infère les relations fait->dimension via les clés étrangères '<x>_id'.

        Pour chaque colonne '<x>_id' d'une table source, on relie à la table
        dimension dont le nom contient '<x>' et dont la clé primaire est 'id'.
        Évite les doublons et les relations auto-référencées.
        """
        relationships = []
        seen = set()
        # Tables candidates comme destination (clé primaire 'id')
        dim_by_keyword = {}
        for t in list(facts) + list(dims):
            stem = BIArchitect._table_stem(t).lower()
            dim_by_keyword[stem] = t

        def primary_key(name):
            for c in sources_meta[name].get("colonnes", []):
                if str(c["nom"]).lower() == "id":
                    return "id"
            return None

        all_tables = list(facts) + list(dims)
        for src in all_tables:
            # La table Date (Dates.csv) est virtuelle : pas dans sources_meta.
            if src not in sources_meta:
                continue
            for c in sources_meta[src].get("colonnes", []):
                fcol = str(c["nom"]).lower()
                if not fcol.endswith("_id"):
                    continue
                # 'product_id' -> mot-clé 'product'
                keyword = fcol[:-3]
                # Trouve la dimension dont le nom contient le mot-clé
                target = None
                for stem, tname in dim_by_keyword.items():
                    if keyword in stem.split("_"):
                        target = tname
                        break
                if target is None:
                    # correspondance partielle (ex. 'sale' dans 'sales')
                    for stem, tname in dim_by_keyword.items():
                        if keyword in stem or stem in keyword:
                            target = tname
                            break
                if target is None or target == src:
                    continue
                pk = primary_key(target)
                if pk is None:
                    continue
                key = (src, fcol, target, pk)
                if key in seen:
                    continue
                seen.add(key)
                relationships.append({
                    "from_table": src,
                    "from_column": c["nom"],
                    "to_table": target,
                    "to_column": pk,
                    "cardinality": "many-to-one",
                })
        return relationships

    @staticmethod
    def build_model(sources_meta: dict, project_name: str = "") -> dict:
        """Construit le model.json complet (schéma en étoile)."""
        facts, dims = BIArchitect._classify_tables(sources_meta)
        relationships = BIArchitect._infer_relationships(facts, dims, sources_meta)

        # Granularité par défaut = clé primaire détectée dans la table de fait
        granularite = {}
        for fact in facts:
            pk = None
            for c in sources_meta[fact]["colonnes"]:
                if str(c["nom"]).lower().startswith("id"):
                    pk = c["nom"]
                    break
            granularite[fact] = pk or "à déterminer"

        # Table Date dédiée : si une colonne de date existe dans un fait
        # (détectée par type OU par nom : date/jour/mois/année/time),
        # on ajoute une dimension 'Dates' et la relation fait->Dates.
        DATE_NAME_KEYWORDS = ("date", "jour", "mois", "annee", "année", "time", "periode")
        date_table = None
        date_fact_col = None
        for fact in facts:
            for c in sources_meta[fact]["colonnes"]:
                ctype = str(c.get("type", "")).lower()
                cname = str(c["nom"]).lower()
                is_date_type = ctype in ("datetime64", "date", "datetime")
                is_date_name = any(k in cname for k in DATE_NAME_KEYWORDS)
                if is_date_type or is_date_name:
                    date_table = "Dates.csv"
                    date_fact_col = c["nom"]
                    break
            if date_table:
                break

        if date_table and date_table not in dims:
            dims = dims + [date_table]
            relationships.append({
                "from_table": fact,
                "from_column": date_fact_col,
                "to_table": date_table,
                "to_column": "Date",
                "cardinality": "many-to-one",
            })

        model = {
            "project": project_name,
            "type": "star_schema",
            "facts": facts,
            "dimensions": dims,
            "granularite": granularite,
            "relationships": relationships,
        }
        if date_table:
            model["date_table"] = date_table
            model["date_columns"] = [date_fact_col]
        return model

    @staticmethod
    def generate_model_suggestions(model: dict) -> str:
        """Appel IA optionnel pour affiner / commenter le modèle proposé."""
        prompt = f"""
Tu es un architecte Power BI expert. Voici un modèle en étoile proposé
automatiquement à partir de sources de données :

{model}

Propose des améliorations :
- Relations manquantes ou ambiguës.
- Colonnes à masquer (ex. clés techniques).
- Hiérarchies pertinentes (ex. Date : Année > Mois > Jour).
- Mesures DAX de base à créer (Total Ventes, Nb Clients...).
Réponds de manière structurée et concise.
        """
        return orchestrator.generate(prompt, task_type="modeling")
