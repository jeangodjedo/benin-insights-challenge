# pipeline/load.py
"""
Module de sauvegarde des données transformées.

Étape 3 du pipeline ETL — Load.

Produit 3 formats adaptés à chaque membre de l'équipe :
    CSV     → Data Analyst  (Tableau, Power BI, Excel)
    Parquet → ML Engineer   (scikit-learn, HuggingFace)
    JSON    → Data Scientist (notebooks, API FastAPI)

+ rapport de qualité JSON résumant les données par question.

Auteur  : Équipe Bénin Insights Challenge 2026
Date    : Avril 2026
Version : 1.0
"""

import os
import json
import pandas as pd
from datetime import datetime

from .config import (
    PROCESSED_DIR, SAMPLES_DIR, RAW_DIR,
    PROCESSED_FILE, PARQUET_FILE, JSON_FILE, QUALITY_REPORT,
)
from . import __version__
from .utils import logger, timer, create_directories, validate_dataframe


@timer
def save_to_csv(df: pd.DataFrame, filepath: str) -> None:
    """
    Save to CSV UTF-8.
    Universal format for Data Analyst (Excel, Tableau, Power BI).
    """
    try:
        df.to_csv(filepath, index=False, encoding="utf-8")
        size_kb = round(os.path.getsize(filepath) / 1024, 1)
        logger.info(f"[OK] CSV saved: {filepath} ({size_kb} KB, {len(df):,} rows)")
    except Exception as e:
        logger.error(f"[ERROR] Failed to save CSV to {filepath}: {e}")
        raise


@timer
def save_to_parquet(df: pd.DataFrame, filepath: str) -> None:
    """
    Save to Parquet compressed (snappy).
    5-10x more compact than CSV, types preserved — ideal for ML Engineer.
    Requires pyarrow (included in requirements.txt).
    """
    try:
        df.to_parquet(filepath, index=False, compression="snappy")
        size_kb = round(os.path.getsize(filepath) / 1024, 1)
        logger.info(f"[OK] Parquet saved: {filepath} ({size_kb} KB)")
    except Exception as e:
        logger.error(f"[ERROR] Failed to save Parquet to {filepath}: {e}")
        raise


@timer
def save_to_json(df: pd.DataFrame, filepath: str) -> None:
    """
    Save to JSON oriented records.
    Useful for Jupyter notebooks and FastAPI of Data Scientist.
    Datetime columns are converted to string before serialization.
    """
    try:
        df_copy = df.copy()
        for col in df_copy.select_dtypes(include=["datetimetz", "datetime64[ns]"]).columns:
            df_copy[col] = df_copy[col].dt.strftime("%Y-%m-%dT%H:%M:%S")
        df_copy.to_json(filepath, orient="records", force_ascii=False, indent=2)
        size_kb = round(os.path.getsize(filepath) / 1024, 1)
        logger.info(f"[OK] JSON saved: {filepath} ({size_kb} KB)")
    except Exception as e:
        logger.error(f"[ERROR] Failed to save JSON to {filepath}: {e}")
        raise


@timer
def generate_quality_report(df: pd.DataFrame) -> dict:
    """
    Génère un rapport de qualité JSON structuré par question.

    Contenu :
    - Volume et période couverte
    - Valeurs manquantes par colonne
    - Métriques spécifiques Q1 → Q5

    Le rapport est partagé avec toute l'équipe pour comprendre
    rapidement les données sans ouvrir le CSV.

    Args:
        df: DataFrame final
    Returns:
        dict: Rapport de qualité
    """
    logger.info("Génération du rapport de qualité...")

    report = {
        "generated_at"    : datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "pipeline_version": __version__,
        "challenge"       : "Bénin Insights Challenge 2026",
        "periode"         : "Janvier 2025 → Décembre 2025",

        "volume": {
            "total_rows"   : len(df),
            "total_columns": len(df.columns),
            "columns"      : list(df.columns),
        },

        "period": {
            "date_min": str(df["SQLDATE"].min())[:10] if "SQLDATE" in df.columns else "N/A",
            "date_max": str(df["SQLDATE"].max())[:10] if "SQLDATE" in df.columns else "N/A",
        },

        "missing_values_pct": {
            col: round(df[col].isna().sum() / len(df) * 100, 1)
            for col in df.columns if df[col].isna().sum() > 0
        },

        "q1_pics_couverture": {
            "total_articles"        : int(df["NumArticles"].sum()) if "NumArticles" in df.columns else 0,
            "top_5_event_types"     : df["event_root_label"].value_counts().head(5).to_dict() if "event_root_label" in df.columns else {},
        },

        "q2_ton_mediatique": {
            "distribution"          : df["tone_category"].value_counts().to_dict() if "tone_category" in df.columns else {},
            "avg_tone"              : round(df["AvgTone"].mean(), 3) if "AvgTone" in df.columns else None,
            "avg_goldstein"         : round(df["GoldsteinScale"].mean(), 3) if "GoldsteinScale" in df.columns else None,
            "stability_distribution": df["stability_category"].value_counts().to_dict() if "stability_category" in df.columns else {},
        },

        "q3_propagation": {
            "avg_delay_days"    : round(df["propagation_delay_days"].mean(), 1) if "propagation_delay_days" in df.columns else None,
            "median_delay_days" : round(df["propagation_delay_days"].median(), 1) if "propagation_delay_days" in df.columns else None,
        },

        "q4_sources": {
            "unique_domains"     : int(df["source_domain"].nunique()) if "source_domain" in df.columns else 0,
            "top_10_domains"     : df["source_domain"].value_counts().head(10).to_dict() if "source_domain" in df.columns else {},
            "crisis_events_count": int(df["is_crisis_period"].sum()) if "is_crisis_period" in df.columns else 0,
        },

        "q5_role_benin": {
            "distribution"      : df["benin_role"].value_counts().to_dict() if "benin_role" in df.columns else {},
            "top_actor1_types"  : df["actor1_type_label"].value_counts().head(5).to_dict() if "actor1_type_label" in df.columns else {},
        },
    }

    with open(QUALITY_REPORT, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    logger.info(f"[OK] Quality report: {QUALITY_REPORT}")
    return report


@timer
def run_load(df: pd.DataFrame) -> None:
    """
    Orchestre toutes les sauvegardes.

    Fichiers produits :
        data/processed/benin_gdelt_clean.csv
        data/processed/benin_gdelt_clean.parquet
        data/processed/benin_gdelt_clean.json
        data/processed/quality_report.json

    Args:
        df: DataFrame propre issu de transform.py
    """
    logger.info("=" * 55)
    logger.info("CHARGEMENT — DÉMARRAGE")
    logger.info("=" * 55)

    if not validate_dataframe(df, "données à sauvegarder"):
        raise ValueError("DataFrame invalide — chargement annulé.")

    create_directories(PROCESSED_DIR)

    save_to_csv(df, PROCESSED_FILE)
    save_to_parquet(df, PARQUET_FILE)
    save_to_json(df, JSON_FILE)
    generate_quality_report(df)

    logger.info("=" * 55)
    logger.info("CHARGEMENT — TERMINÉ")
    logger.info("=" * 55)