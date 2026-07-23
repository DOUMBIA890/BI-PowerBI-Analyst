import pandas as pd
from core.ai_orchestrator import orchestrator

class AIDataEngineer:
    # Méthode existante (pour fichiers uploadés)
    @staticmethod
    def analyze_file(file) -> dict:
        filename = file.name.lower()
        if filename.endswith(".csv"):
            df = pd.read_csv(file)
        elif filename.endswith(".xlsx"):
            df = pd.read_excel(file)
        else:
            raise ValueError("Format non supporté")
        return AIDataEngineer._build_analysis(df, file.name)

    # Nouvelle méthode pour un DataFrame déjà chargé
    @staticmethod
    def analyze_dataframe(df: pd.DataFrame, filename: str) -> dict:
        return AIDataEngineer._build_analysis(df, filename)

    # Méthode privée commune pour éviter la duplication
    @staticmethod
    def _build_analysis(df: pd.DataFrame, filename: str) -> dict:
        return {
            "nom_fichier": filename,
            "nombre_lignes": len(df),
            "nombre_colonnes": len(df.columns),
            "colonnes": list(df.columns),
            "types_variables": df.dtypes.astype(str).to_dict(),
            "valeurs_manquantes": df.isnull().sum().to_dict(),
            "aperçu": df.head(5).to_dict()
        }

    # =========================================================
    # Phase 3 — Livrables d'ingénierie des données
    # Chaque méthode produit un JSON exploitable par les
    # agents suivants (modélisation, DAX, design...).
    # =========================================================

    @staticmethod
    def build_metadata(df: pd.DataFrame, filename: str) -> dict:
        """metadata.json : catalogue structuré des colonnes du fichier source."""
        columns = []
        for col in df.columns:
            series = df[col]
            non_null = series.dropna()
            sample = None
            if len(non_null) > 0:
                val = non_null.iloc[0]
                sample = str(val)[:60]
            columns.append({
                "nom": col,
                "type": str(series.dtype),
                "valeurs_uniques": int(series.nunique(dropna=True)),
                "taux_manquant": round(float(series.isnull().mean()) * 100, 2),
                "exemple": sample,
            })
        return {
            "nom_fichier": filename,
            "nombre_lignes": int(len(df)),
            "nombre_colonnes": int(len(df.columns)),
            "colonnes": columns,
        }

    @staticmethod
    def build_quality_report(df: pd.DataFrame, filename: str) -> dict:
        """quality_report.json : diagnostic de qualité (doublons, manquants, etc.)."""
        dup_rows = int(df.duplicated().sum())
        total_cells = int(df.size)
        missing_cells = int(df.isnull().sum().sum())
        issues = []
        for col in df.columns:
            series = df[col]
            miss = int(series.isnull().sum())
            if miss > 0:
                issues.append({
                    "colonne": col,
                    "type": "valeurs_manquantes",
                    "count": miss,
                    "pct": round(miss / len(df) * 100, 2),
                })
        if dup_rows > 0:
            issues.append({
                "colonne": "(lignes entières)",
                "type": "doublons",
                "count": dup_rows,
                "pct": round(dup_rows / len(df) * 100, 2),
            })
        # Détection simple de colonnes à fort taux de cardinalité (candidats clé/dim)
        candidate_keys = [
            col for col in df.columns
            if df[col].nunique(dropna=True) == len(df.dropna(subset=[col]))
            and df[col].isnull().sum() == 0
        ]
        score = 100.0
        if total_cells:
            score -= round(missing_cells / total_cells * 100, 2)
        return {
            "nom_fichier": filename,
            "score_qualite": max(0.0, score),
            "lignes_dupliquees": dup_rows,
            "cellules_manquantes": missing_cells,
            "problemes": issues,
            "candidats_cles": candidate_keys,
        }

    @staticmethod
    def build_cleaning_plan(df: pd.DataFrame, filename: str) -> dict:
        """cleaning_plan.json : plan d'action proposé (sans IA, règles déterministes)."""
        actions = []
        for col in df.columns:
            series = df[col]
            miss = int(series.isnull().sum())
            if miss > 0:
                pct = miss / len(df) * 100
                if pct > 50:
                    action = "supprimer_colonne"
                elif series.dtype == object:
                    action = "imputer_mode"
                else:
                    action = "imputer_mediane"
                actions.append({
                    "colonne": col,
                    "action": action,
                    "valeurs_manquantes": miss,
                })
        dup_rows = int(df.duplicated().sum())
        if dup_rows > 0:
            actions.append({
                "colonne": "(toutes)",
                "action": "supprimer_doublons",
                "valeurs_manquantes": dup_rows,
            })
        return {
            "nom_fichier": filename,
            "actions": actions,
            "resume": f"{len(actions)} action(s) proposée(s).",
        }

    @staticmethod
    def generate_schema_suggestions(analysis_result: dict) -> str:
        prompt = f"""
Tu es un ingénieur données expert Power BI. Voici l'analyse d'un fichier source :
{analysis_result}

Propose :
- Les dimensions et la table de faits à créer (schéma en étoile).
- Les colonnes à supprimer, renommer ou convertir.
- Les jointures éventuelles si plusieurs tables sont détectées.
Réponds de manière structurée.
        """
        return orchestrator.generate(prompt, task_type="preprocessing")

    # =========================================================
    # Application RÉELLE du nettoyage + assistant IA
    # =========================================================
    @staticmethod
    def clean_data(df: pd.DataFrame, cleaning_plan: dict) -> pd.DataFrame:
        """Applique réellement les actions du cleaning_plan au DataFrame.

        Gère : suppression doublons, imputation (mode/médiane), nettoyage des
        caractères spéciaux/espaces, et tentative de conversion des types
        (ex. '3 500 €' -> 3500).
        """
        df = df.copy()
        for action in cleaning_plan.get("actions", []):
            col = action.get("colonne")
            act = action.get("action")
            if col == "(toutes)" and act == "supprimer_doublons":
                df = df.drop_duplicates().reset_index(drop=True)
                continue
            if col not in df.columns:
                continue
            if act == "supprimer_colonne":
                df = df.drop(columns=[col])
            elif act == "imputer_mode":
                mode = df[col].mode(dropna=True)
                if len(mode):
                    df[col] = df[col].fillna(mode.iloc[0])
            elif act == "imputer_mediane":
                med = pd.to_numeric(df[col], errors="coerce").median()
                if pd.notna(med):
                    df[col] = pd.to_numeric(df[col], errors="coerce").fillna(med)
            # Nettoyage générique des chaînes
            if df[col].dtype == object:
                df[col] = (
                    df[col]
                    .astype(str)
                    .str.strip()
                    .str.replace(r"\s+", " ", regex=True)
                    .replace({"nan": None, "None": None})
                )
                # Conversion '3 500 €' -> 3500 si numérique après nettoyage
                cleaned = (
                    df[col]
                    .str.replace(r"[^\d,.\-]", "", regex=True)
                    .str.replace(",", ".")
                )
                numeric = pd.to_numeric(cleaned, errors="coerce")
                if numeric.notna().mean() > 0.8:  # majoritairement numérique
                    df[col] = numeric
        return df

    @staticmethod
    def explain_cleaning(df_before: pd.DataFrame, df_after: pd.DataFrame,
                         quality_report: dict) -> str:
        """Assistant IA : explique clairement ce qui a été détecté et corrigé."""
        try:
            pb = quality_report.get("problemes", [])
            pb_txt = "; ".join(
                f"{p['colonne']}: {p['type']} ({p['count']})" for p in pb
            ) or "aucun problème majeur"
            prompt = (
                f"Un fichier de données a été nettoyé automatiquement.\n"
                f"Problèmes détectés avant nettoyage : {pb_txt}.\n"
                f"Lignes avant : {len(df_before)}, après : {len(df_after)}.\n"
                f"Expliquez à un DÉBUTANT, en 3 phrases max, ce qui a été "
                f"corrigé et pourquoi c'est important pour son rapport Power BI."
            )
            return orchestrator.generate(prompt, task_type="preprocessing").strip()
        except Exception as exc:
            return f"(explication indisponible : {exc})"