"""
Transformed data saving module.

ETL Pipeline Step 3 — Load.

Produces 3 formats adapted to each team member's needs:
    CSV     -> Data Analyst  (Tableau, Power BI, Excel)
    Parquet -> ML Engineer   (scikit-learn, HuggingFace)
    JSON    -> Data Scientist (notebooks, FastAPI)

Also generates a JSON quality report summarizing data by question.

Changes in v1.1:
    MAJ-05: run_load() now only creates PROCESSED_DIR.
            Does not create RAW_DIR (responsibility of extract.py).
    MAJ-08: Added try/except blocks with contextual error messages
            in all save functions.
    MIN-01: pipeline_version loaded from config.PIPELINE_VERSION
            (single source of truth).
    MIN-02: save_to_json() now handles timezone-aware datetime columns
            (datetime64[ns, UTC]) in addition to naive datetime64[ns].
    MIN-06: Removed emojis from log messages for ASCII compatibility.

Author  : Team 7 — Bénin Insights Challenge 2026
Date    : May 2026
Version : 1.2
"""

import os
import json
import pandas as pd
from datetime import datetime

from .config import (
    PROCESSED_DIR,
    SAMPLES_DIR,
    RAW_DIR,
    PROCESSED_FILE,
    PARQUET_FILE,
    JSON_FILE,
    QUALITY_REPORT,
    PIPELINE_VERSION,
)
from .utils import logger, timer, create_directories, validate_dataframe


# ─────────────────────────────────────────────────────────────────
# CSV SAVE
# ─────────────────────────────────────────────────────────────────

@timer
def save_to_csv(df: pd.DataFrame, filepath) -> None:
    """
    Save DataFrame as UTF-8 encoded CSV.

    Universal format — compatible with Excel, Tableau, Power BI,
    R, and any other tool used by the team.

    MAJ-08: Wrapped in try/except with contextual error message
    specifying the format and target path.

    Args:
        df      : Clean pandas DataFrame
        filepath: Output CSV file path (str or Path)

    Raises:
        IOError: If writing the CSV file fails
    """
    try:
        df.to_csv(filepath, index=False, encoding="utf-8")
        size_kb = round(os.path.getsize(filepath) / 1024, 1)
        logger.info(f"[OK] CSV saved: {filepath} ({size_kb} KB, {len(df):,} rows)")
    except Exception as e:
        logger.error(f"[ERROR] Failed to save CSV at {filepath}: {e}")
        raise


# ─────────────────────────────────────────────────────────────────
# PARQUET SAVE
# ─────────────────────────────────────────────────────────────────

@timer
def save_to_parquet(df: pd.DataFrame, filepath) -> None:
    """
    Save DataFrame as compressed Parquet (snappy).

    Advantages for the ML Engineer:
    - 5 to 10x more compact than CSV
    - Preserves data types (datetime, bool, float)
    - 10x faster loading in pandas
    - Compatible with scikit-learn, HuggingFace, Spark

    Requires pyarrow (included in requirements.txt).

    MAJ-08: Wrapped in try/except with contextual error message.

    Args:
        df      : Clean pandas DataFrame
        filepath: Output Parquet file path (str or Path)

    Raises:
        Exception: If writing the Parquet file fails
    """
    try:
        df.to_parquet(filepath, index=False, compression="snappy")
        size_kb = round(os.path.getsize(filepath) / 1024, 1)
        logger.info(f"[OK] Parquet saved: {filepath} ({size_kb} KB)")
    except Exception as e:
        logger.error(f"[ERROR] Failed to save Parquet at {filepath}: {e}")
        raise


# ─────────────────────────────────────────────────────────────────
# JSON SAVE
# ─────────────────────────────────────────────────────────────────

@timer
def save_to_json(df: pd.DataFrame, filepath) -> None:
    """
    Save DataFrame as records-oriented JSON.

    Useful for:
    - Jupyter notebooks of the Data Scientist
    - FastAPI / Flask API feeding
    - JavaScript visualizations (Plotly, D3.js)

    MIN-02 FIX: Handles both naive datetime64[ns] and
    timezone-aware datetime64[ns, UTC] columns.
    BigQuery may return timezone-aware columns depending on client
    configuration. Without this fix, to_json() raises a TypeError
    on timezone-aware columns.

    MAJ-08: Wrapped in try/except with contextual error message.

    Args:
        df      : Clean pandas DataFrame
        filepath: Output JSON file path (str or Path)

    Raises:
        Exception: If writing the JSON file fails
    """
    try:
        df_copy = df.copy()

        # MIN-02: Handle both naive and timezone-aware datetime columns
        # select_dtypes with "datetimetz" captures datetime64[ns, UTC]
        # "datetime64[ns]" captures naive datetimes
        datetime_cols = df_copy.select_dtypes(
            include=["datetime64[ns]", "datetimetz"]
        ).columns

        for col in datetime_cols:
            df_copy[col] = df_copy[col].dt.strftime("%Y-%m-%dT%H:%M:%S")

        df_copy.to_json(filepath, orient="records", force_ascii=False, indent=2)
        size_kb = round(os.path.getsize(filepath) / 1024, 1)
        logger.info(f"[OK] JSON saved: {filepath} ({size_kb} KB)")
    except Exception as e:
        logger.error(f"[ERROR] Failed to save JSON at {filepath}: {e}")
        raise


# ─────────────────────────────────────────────────────────────────
# QUALITY REPORT
# ─────────────────────────────────────────────────────────────────

@timer
def generate_quality_report(df: pd.DataFrame) -> dict:
    """
    Generate a JSON quality report structured by analytical question.

    Content:
    - Volume and period covered
    - Missing values per column
    - Q1 to Q5 specific metrics

    The report is shared with the whole team to quickly understand
    the available data without opening the CSV.

    MIN-01 FIX: pipeline_version is now loaded from config.PIPELINE_VERSION
    (single source of truth) instead of being hardcoded as "1.0".

    Args:
        df: Final clean DataFrame

    Returns:
        dict: Quality report as a structured dictionary
    """
    logger.info("Generating quality report...")

    report = {
        "generated_at"    : datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "pipeline_version": PIPELINE_VERSION,
        "challenge"       : "Bénin Insights Challenge 2026 — iSHEERO x DataCamp Donates",
        "period"          : "January 2025 -> December 2025",

        "volume": {
            "total_rows"   : len(df),
            "total_columns": len(df.columns),
            "columns"      : list(df.columns),
        },

        "period_covered": {
            "date_min": str(df["SQLDATE"].min())[:10] if "SQLDATE" in df.columns else "N/A",
            "date_max": str(df["SQLDATE"].max())[:10] if "SQLDATE" in df.columns else "N/A",
        },

        "missing_values_pct": {
            col: round(df[col].isna().sum() / len(df) * 100, 1)
            for col in df.columns if df[col].isna().sum() > 0
        },

        "q1_coverage_peaks": {
            "total_articles"   : int(df["NumArticles"].sum()) if "NumArticles" in df.columns else 0,
            "top_5_event_types": (
                df["event_root_label"].value_counts().head(5).to_dict()
                if "event_root_label" in df.columns else {}
            ),
        },

        "q2_media_tone": {
            "distribution": (
                df["tone_category"].value_counts().to_dict()
                if "tone_category" in df.columns else {}
            ),
            "avg_tone"    : round(df["AvgTone"].mean(), 3) if "AvgTone" in df.columns else None,
            "avg_goldstein": round(df["GoldsteinScale"].mean(), 3) if "GoldsteinScale" in df.columns else None,
            "stability"   : (
                df["stability_category"].value_counts().to_dict()
                if "stability_category" in df.columns else {}
            ),
        },

        "q3_propagation": {
            "avg_delay_days"   : round(df["propagation_delay_days"].mean(), 1) if "propagation_delay_days" in df.columns else None,
            "median_delay_days": round(df["propagation_delay_days"].median(), 1) if "propagation_delay_days" in df.columns else None,
        },

        "q4_sources": {
            "unique_domains"     : int(df["source_domain"].nunique()) if "source_domain" in df.columns else 0,
            "top_10_domains"     : (
                df["source_domain"].value_counts().head(10).to_dict()
                if "source_domain" in df.columns else {}
            ),
            "crisis_events_count": int(df["is_crisis_period"].sum()) if "is_crisis_period" in df.columns else 0,
        },

        "q5_benin_role": {
            "distribution"    : (
                df["benin_role"].value_counts().to_dict()
                if "benin_role" in df.columns else {}
            ),
            "top_actor1_types": (
                df["actor1_type_label"].value_counts().head(5).to_dict()
                if "actor1_type_label" in df.columns else {}
            ),
        },
    }

    try:
        with open(QUALITY_REPORT, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        logger.info(f"[OK] Quality report saved: {QUALITY_REPORT}")
    except Exception as e:
        logger.error(f"[ERROR] Failed to save quality report at {QUALITY_REPORT}: {e}")
        raise

    return report


# ─────────────────────────────────────────────────────────────────
# MAIN FUNCTION
# ─────────────────────────────────────────────────────────────────

@timer
def run_load(df: pd.DataFrame) -> None:
    """
    Orchestrate all saves and the quality report.

    Files produced in data/clean/:
        benin_gdelt_clean.csv        -> Data Analyst
        benin_gdelt_clean.parquet    -> ML Engineer
        benin_gdelt_clean.json       -> Data Scientist
        quality_report.json          -> entire team

    MAJ-05 FIX: Only creates PROCESSED_DIR (data/clean/).
    Does not create RAW_DIR — that is extract.py's responsibility.

    Args:
        df: Clean DataFrame from transform.py

    Raises:
        ValueError: If the input DataFrame is invalid
    """
    logger.info("=" * 55)
    logger.info("LOAD - START")
    logger.info("=" * 55)

    if not validate_dataframe(df, "data to save"):
        raise ValueError("Invalid DataFrame - load cancelled.")

    # MAJ-05: Only create the directory this step writes to
    create_directories(PROCESSED_DIR)

    save_to_csv(df, PROCESSED_FILE)
    save_to_parquet(df, PARQUET_FILE)
    save_to_json(df, JSON_FILE)
    generate_quality_report(df)

    logger.info("=" * 55)
    logger.info("LOAD - COMPLETED")
    logger.info(f"  CSV     : {PROCESSED_FILE}")
    logger.info(f"  Parquet : {PARQUET_FILE}")
    logger.info(f"  JSON    : {JSON_FILE}")
    logger.info(f"  Report  : {QUALITY_REPORT}")
    logger.info("=" * 55)