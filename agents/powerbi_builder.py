"""Power BI Builder — Phase 7 : assemblage du projet .pbip complet.

Génère une structure de projet Power BI ouvrable dans Power BI Desktop
(Format "Power BI Project", .pbip) à partir des livrables produits par les
étapes précédentes (model.json, dax_measures.json, kpi_catalog.json,
theme.json, layout.json).

Structure produite (sous projects/<projet>/<Projet>.pbip/) :

  <Projet>.pbip                 # racine (référence report/ + semanticModel/)
  semanticModel/
      definition.pbism         # métadonnées du modèle sémantique
      model.tmdl               # TMDL : tables, colonnes, mesures
      relationships.tmdl       # TMDL : relations (optionnel, fusionné dans model.tmdl)
  report/
      report.json              # Report JSON (pages, sections, visuels)
  definition/
      definition.pbir         # pointe vers report/report.json
  theme.json                   # thème Power BI (copié depuis metadata/)
"""
from pathlib import Path
import json
import shutil


class PowerBIBuilder:
    # ------------------------------------------------------------------
    # Helpers TMDL
    # ------------------------------------------------------------------
    @staticmethod
    def _table_name_from_meta(fname: str) -> str:
        """Dérive le nom de table sémantique à partir d'un nom de fichier metadata.

        'Sales_metadata.json' -> 'Sales.csv'  (la convention du modèle).
        """
        stem = Path(fname).stem
        if stem.endswith("_metadata"):
            stem = stem[: -len("_metadata")]
        return f"{stem}.csv"

    @staticmethod
    def _tmdl_type(ctype: str) -> str:
        c = (ctype or "string").lower()
        if c in ("object", "string", "str", "category", "datetime64", "bool", "boolean"):
            return "string"
        if c in ("int64", "int32", "int", "int16", "int8"):
            return "int64"
        return "double"

    @staticmethod
    def _tmdl_tables(sources_meta: dict, project_path: str = "") -> str:
        """Génère les tables TMDL avec colonnes + partition pointant vers le CSV source.

        Chaque table porte le nom '<Source>.csv' (ex. 'Sales.csv') et déclare une
        partition CSV pour que Power BI charge réellement les données.
        """
        blocks = []
        for fname, meta in sources_meta.items():
            table_name = PowerBIBuilder._table_name_from_meta(fname)
            lines = [f"table '{table_name}'", "{"]
            for col in meta.get("colonnes", []):
                ctype = col.get("type", "string")
                col_name = col["nom"]
                # Les clés techniques (id, *_id) sont masquées à l'utilisateur
                is_hidden = col_name.lower() == "id" or col_name.lower().endswith("_id")
                lines.append(f"    column '{col_name}'")
                lines.append("    {")
                lines.append(f"        dataType: {PowerBIBuilder._tmdl_type(ctype)}")
                if is_hidden:
                    lines.append("        isHidden: true")
                lines.append("    }")
            # Partition CSV (chemin relatif vers les données sources)
            src = meta.get("nom_fichier", f"{table_name}")
            lines.append("    partition 'Partition'")
            lines.append("    {")
            lines.append("        source = csv")
            lines.append("        {")
            lines.append(f"            Path: ../data/{src}")
            lines.append("        }")
            lines.append("    }")
            lines.append("}")
            blocks.append("\n".join(lines))
        return "\n\n".join(blocks)

    @staticmethod
    def _tmdl_date_table() -> str:
        """Génère une table Date calculée (CALENDAR) avec hiérarchie Temps.

        Déclarée comme partition 'calculated' (DAX). Fournit les colonnes
        Date, Année, Mois, Jour et la hiérarchie Année > Mois > Jour.
        """
        return (
            "table 'Dates.csv'\n"
            "{\n"
            "    column 'Date'\n"
            "    {\n"
            "        dataType: dateTime\n"
            "        isUnique: true\n"
            "        summarizeBy: none\n"
            "    }\n"
            "    column 'Année'\n"
            "    {\n"
            "        dataType: int64\n"
            "        isHidden: true\n"
            "        summarizeBy: none\n"
            "        expression: 'YEAR([Date])'\n"
            "    }\n"
            "    column 'Mois'\n"
            "    {\n"
            "        dataType: int64\n"
            "        isHidden: true\n"
            "        summarizeBy: none\n"
            "        expression: 'MONTH([Date])'\n"
            "    }\n"
            "    column 'Jour'\n"
            "    {\n"
            "        dataType: int64\n"
            "        isHidden: true\n"
            "        summarizeBy: none\n"
            "        expression: 'DAY([Date])'\n"
            "    }\n"
            "    column 'MoisNom'\n"
            "    {\n"
            "        dataType: string\n"
            "        summarizeBy: none\n"
            "        expression: 'FORMAT([Date], \\\"MMMM\\\")'\n"
            "    }\n"
            "    hierarchy 'Temps'\n"
            "    {\n"
            "        levels: [\n"
            "            'Année',\n"
            "            'Mois',\n"
            "            'Jour'\n"
            "        ]\n"
            "    }\n"
            "    partition 'Partition'\n"
            "    {\n"
            "        source = calculated\n"
            "        {\n"
            "            expression: 'CALENDAR(DATE(2015, 1, 1), DATE(2035, 12, 31))'\n"
            "        }\n"
            "    }\n"
            "}"
        )

    @staticmethod
    def _tmdl_measures(dax_measures: dict, sources_meta: dict) -> str:
        """Émet les mesures DAX **fusionnées** dans les tables déjà déclarées.

        Retourne une chaîne de blocs `table 'X.csv' { measure ... }` pour chaque
        table qui possède au moins une mesure (les colonnes sont déclarées séparément
        par _tmdl_tables, fusionnées ensuite par TMDL).
        """
        by_table = {}
        for m in dax_measures.get("measures", []):
            by_table.setdefault(m["table"], []).append(m)
        blocks = []
        for table, measures in by_table.items():
            lines = [f"table '{table}'", "{"]
            for m in measures:
                lines.append(f"    measure '{m['nom']}'")
                lines.append("    {")
                lines.append(f"        expression: {m['expression']}")
                lines.append(f"        formatString: \"{m['format']}\"")
                lines.append("    }")
            lines.append("}")
            blocks.append("\n".join(lines))
        return "\n\n".join(blocks)

    @staticmethod
    def _tmdl_relationships(model: dict) -> str:
        rels = model.get("relationships") or []
        # Filtre les relations invalides (colonnes vides ou concaténées)
        valid = []
        for r in rels:
            if not r:
                continue
            fc, tc = r.get("from_column"), r.get("to_column")
            if not fc or not tc:
                continue
            if ";" in str(fc) or ";" in str(tc):
                continue
            valid.append(r)
        blocks = ["model", "{"]
        for r in valid:
            # Les noms de table dans model.json sont '*_metadata.json' ; on
            # dérive le nom de table TMDL ('*.csv') pour rester cohérent avec
            # _tmdl_tables (sinon Power BI ne trouve pas la table référencée).
            ft = PowerBIBuilder._table_name_from_meta(r["from_table"])
            tt = PowerBIBuilder._table_name_from_meta(r["to_table"])
            name = f"{ft}_{r['from_column']}"
            blocks.append(f"    relationship '{name}'")
            blocks.append("    {")
            blocks.append(f"        fromColumn: '{ft}'[{r['from_column']}]")
            blocks.append(f"        toColumn: '{tt}'[{r['to_column']}]")
            blocks.append(f"        cardinality: {r.get('cardinality', 'many-to-one')}")
            blocks.append("    }")
        blocks.append("}")
        return "\n".join(blocks)

    # ------------------------------------------------------------------
    # Helpers Report JSON
    # ------------------------------------------------------------------
    @staticmethod
    def _report_definition(theme_name: str) -> dict:
        """Contenu de report/definition.pbir (référence au modèle sémantique)."""
        return {
            "version": "1.0",
            "datasetReference": {
                "byPath": "./../semanticModel/definition.pbism",
            },
        }

    # Mapping des types "simples" du layout vers les visualType Power BI.
    VISUAL_TYPES = {
        "Card": "card",
        "LineChart": "lineChart",
        "BarChart": "barChart",
        "ColumnChart": "columnChart",
        "DonutChart": "donutChart",
        "PieChart": "pieChart",
        "Table": "tableEx",
        "Matrix": "matrix",
        "KPI": "kpi",
        "AreaChart": "areaChart",
        "Map": "map",
        "Slicer": "slicer",
    }

    @classmethod
    def _visual_type(cls, vtype: str) -> str:
        return cls.VISUAL_TYPES.get(vtype, "card")

    @classmethod
    def _build_query(cls, fields: dict) -> dict:
        """Construit le bloc `query` (Selects) à partir des champs du visuel.

        `fields` peut contenir :
          - "values" : liste de {table, column} ou {table, measure}
          - "axis"   : {table, column}
          - "legend" : {table, column}
        """
        selects = []
        # Axis (catégorie / axe X)
        axis = fields.get("axis")
        if axis:
            selects.append({
                "NamedField": {
                    "QueryExpression": {
                        "SourceRef": {"Entity": axis["table"]}
                    },
                    "Property": axis["column"],
                }
            })
        # Legend
        legend = fields.get("legend")
        if legend:
            selects.append({
                "NamedField": {
                    "QueryExpression": {
                        "SourceRef": {"Entity": legend["table"]}
                    },
                    "Property": legend["column"],
                }
            })
        # Values (mesures / colonnes agrégées)
        for val in fields.get("values", []):
            if "measure" in val:
                # Référence à une mesure DAX du modèle
                selects.append({
                    "Measure": {
                        "Expression": {
                            "SourceRef": {"Entity": val["table"]}
                        },
                        "Property": val["measure"],
                    }
                })
            else:
                selects.append({
                    "NamedField": {
                        "QueryExpression": {
                            "SourceRef": {"Entity": val["table"]}
                        },
                        "Property": val["column"],
                    }
                })
        if not selects:
            return {}
        return {
            "commands": [
                {
                    "query": {
                        "Source": {
                            "Type": 1,
                            "Expression": {
                                "Model": {
                                    "SourceRef": {"Model": {}}
                                }
                            },
                        },
                        "Selects": selects,
                    }
                }
            ],
            "binding": {
                "Primary": {"_kind": 0, "Visual": {}}
            },
        }

    @classmethod
    def _projections(cls, vtype: str, fields: dict) -> dict:
        """Construit le mapping dataRoles -> projections (Index des Selects)."""
        proj = {}
        idx = 0
        if fields.get("axis"):
            proj["Category"] = [{"queryRef": idx}]
            idx += 1
        if fields.get("legend"):
            proj["Legend"] = [{"queryRef": idx}]
            idx += 1
        n_values = len(fields.get("values", []))
        if n_values:
            role = "Values" if vtype in ("LineChart", "BarChart", "ColumnChart",
                                         "AreaChart", "DonutChart", "PieChart") else "Values"
            proj[role] = [{"queryRef": i} for i in range(idx, idx + n_values)]
            idx += n_values
        return proj

    @classmethod
    def _page_json(cls, page: dict, theme_name: str) -> dict:
        """Contenu d'un fichier report/pages/<Page>.json (un par page).

        Émet un visualContainer conforme au format .pbip avec un bloc
        `visual` (visualType + projections + objects) et un `query`
        référençant les champs réels du modèle sémantique.
        """
        containers = []
        for i, v in enumerate(page.get("visuals", [])):
            vtype = v.get("type", "Card")
            pbi_type = cls._visual_type(vtype)
            fields = v.get("fields", {})
            query = cls._build_query(fields)
            projections = cls._projections(vtype, fields)

            visual_block = {
                "visualType": pbi_type,
                "projections": projections,
            }
            # Titre du visuel (objects/title)
            title = v.get("title", "")
            if title:
                visual_block["objects"] = {
                    "title": [
                        {
                            "properties": {
                                "text": {
                                    "expr": {
                                        "Literal": {
                                            "Value": f"'{title}'"
                                        }
                                    }
                                },
                                "show": {"expr": {"Literal": {"Value": "true"}}},
                            }
                        }
                    ]
                }

            container = {
                "name": f"Visual{i+1}",
                "type": "visual",
                "x": v.get("x", 0),
                "y": v.get("y", 0),
                "width": v.get("width", 200),
                "height": v.get("height", 100),
                "visual": visual_block,
            }
            if query:
                container["query"] = query
            containers.append(container)

        return {
            "version": "1.0",
            "page": {
                "name": page.get("name", "Page1"),
                "displayName": page.get("name", "Page1"),
                "visualContainers": containers,
            },
        }

    # ------------------------------------------------------------------
    # Assemblage complet
    # ------------------------------------------------------------------
    @staticmethod
    def build(
        project_path: str,
        project_name: str,
        sources_meta: dict,
        model: dict,
        dax_measures: dict,
        layout: dict,
        theme: dict,
    ) -> Path:
        """Génère le .pbip complet. Renvoie le chemin du dossier .pbip."""
        pbip_name = project_name.replace(" ", "")
        pbip_dir = Path(project_path) / f"{pbip_name}.pbip"
        # Nettoyage si déjà existant
        if pbip_dir.exists():
            shutil.rmtree(pbip_dir)
        pbip_dir.mkdir(parents=True, exist_ok=True)
        sm_dir = pbip_dir / "semanticModel"
        sm_dir.mkdir(exist_ok=True)
        report_dir = pbip_dir / "report"
        report_dir.mkdir(exist_ok=True)

        # 1. Racine definition.pbip (format officiel Power BI Project)
        (pbip_dir / "definition.pbip").write_text(
            json.dumps({
                "version": "1.0",
                "settings": {
                    "datasetMode": "DirectLake",
                },
                "report": "./report",
                "semanticModel": "./semanticModel",
            }, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        # 2. semanticModel
        (sm_dir / "definition.pbism").write_text(
            json.dumps({
                "version": "1.0",
                "model": {"culture": "fr-FR", "source": "./model.tmdl"},
            }, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        model_tmdl = (
            "model\n"
            "{\n"
            f"    culture: fr-FR\n"
            "}\n\n"
            + PowerBIBuilder._tmdl_tables(sources_meta, project_path)
            + ("\n\n" + PowerBIBuilder._tmdl_date_table() if model.get("date_table") else "")
            + ("\n\n" if dax_measures.get("measures") else "")
            + PowerBIBuilder._tmdl_measures(dax_measures, sources_meta)
        )
        rels = PowerBIBuilder._tmdl_relationships(model)
        model_tmdl += "\n\n" + rels
        (sm_dir / "model.tmdl").write_text(model_tmdl, encoding="utf-8")
        (sm_dir / "relationships.tmdl").write_text(rels, encoding="utf-8")

        # 3. report (definition.pbir = référence au modèle + pages/*.json)
        (report_dir / "definition.pbir").write_text(
            json.dumps(
                PowerBIBuilder._report_definition(theme.get("name", "Executive")),
                ensure_ascii=False, indent=2,
            ),
            encoding="utf-8",
        )
        pages_dir = report_dir / "pages"
        pages_dir.mkdir(exist_ok=True)
        page_refs = []
        for p in layout.get("pages", []):
            page_name = p.get("name", "Page1")
            (pages_dir / f"{page_name}.json").write_text(
                json.dumps(
                    PowerBIBuilder._page_json(p, theme.get("name", "Executive")),
                    ensure_ascii=False, indent=2,
                ),
                encoding="utf-8",
            )
            page_refs.append({
                "name": page_name,
                "displayName": p.get("displayName", page_name),
                "visualContainers": [
                    {"name": vc.get("name", f"Visual{j+1}")}
                    for j, vc in enumerate(p.get("visuals", []))
                ],
            })

        # 3b. report/report.json à la racine — référence les pages du rapport
        (report_dir / "report.json").write_text(
            json.dumps({
                "version": "1.0",
                "settings": {"gridSize": 32},
                "pages": page_refs,
            }, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        # 4. theme.json
        (pbip_dir / "theme.json").write_text(
            json.dumps(theme, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        return pbip_dir
