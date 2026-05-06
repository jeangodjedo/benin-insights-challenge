# pipeline/extract.py
"""
GDELT data extraction module from Google BigQuery.

ETL Pipeline Step 1 — Extract.

AUTHENTICATION:
    This module does NOT use any credential.json file.
    Authentication relies on Application Default Credentials (ADC).
    Each team member runs once:
        gcloud auth application-default login
    GCP_PROJECT_ID in config.py identifies the billing project.

TWO EXTRACTION MODES:
    - sample : 5,000 rows with LIMIT — for pipeline testing
    - full   : NO LIMIT — retrieves ALL Benin 2025 data

BENIN CITY NOISE FILTER:
    GDELT sometimes tags events from Benin City (Nigeria)
    with ActionGeo_CountryCode = 'BN'. The SQL query excludes
    these false positives by checking that the full location name
    does not contain 'nigeria', 'edo', or 'benin city'.

BUG-01 FIX:
    Actor filters now use COUNTRY_ACTOR_CODE = 'BEN' (CAMEO format)
    instead of COUNTRY_CODE = 'BN' (GDELT geographic format).
    The two systems are different — using 'BN' in actor columns
    returns zero results since 'BN' does not exist in CAMEO.

BIGQUERY QUOTA OPTIMIZATION:
    - SELECT on precise columns only (never SELECT *)
    - YEAR filter placed FIRST in WHERE clause
    - MonthYear filter to scope January-December 2025 precisely

MAJ-05 FIX:
    run_full_extraction() now only creates RAW_DIR.
    run_sample_extraction() only creates SAMPLES_DIR.
    Each function is responsible only for the directories it writes to.

REC-02:
    BigQuery calls use google.api_core.retry.Retry with a 300s deadline
    to handle transient failures (temporary quota, network timeout).

Author  : Team 7 — Bénin Insights Challenge 2026
Date    : May 2026
Version : 1.2
"""

import os
import pandas as pd
from google.cloud import bigquery
from google.api_core.retry import Retry

from .config import (
    GCP_PROJECT_ID,
    BQ_TABLE_FULL,
    COUNTRY_CODE,
    COUNTRY_ACTOR_CODE,
    START_YEAR,
    END_YEAR,
    START_MONTHYEAR,
    END_MONTHYEAR,
    COLUMNS,
    SAMPLE_LIMIT,
    RAW_FILE,
    SAMPLE_FILE,
    RAW_DIR,
    SAMPLES_DIR,
)
from .utils import logger, timer, create_directories, validate_dataframe


# ─────────────────────────────────────────────────────────────────
# BIGQUERY CLIENT INITIALIZATION
# ─────────────────────────────────────────────────────────────────

def get_bigquery_client() -> bigquery.Client:
    """
    Initialize and return an authenticated BigQuery client.

    Uses Application Default Credentials (ADC) — no JSON file required.
    Authentication is managed via:
        gcloud auth application-default login

    The project=GCP_PROJECT_ID parameter tells BigQuery which
    Google Cloud project to bill quota consumption against.

    Returns:
        bigquery.Client: BigQuery client ready to receive queries

    Raises:
        Exception: If ADC authentication fails. In that case,
                   run: gcloud auth application-default login
    """
    try:
        # project= refers to YOUR billing project
        # GDELT data remains on gdelt-bq (public project)
        client = bigquery.Client(project=GCP_PROJECT_ID)
        logger.info(f"[OK] BigQuery connection established - project: {GCP_PROJECT_ID}")
        return client
    except Exception as e:
        logger.error(f"[ERROR] BigQuery connection failed: {e}")
        logger.error("  Solution: gcloud auth application-default login")
        raise


# ─────────────────────────────────────────────────────────────────
# SQL QUERY CONSTRUCTION
# ─────────────────────────────────────────────────────────────────

def build_query(limit: int = None) -> str:
    """
    Build the optimized SQL query for Benin 2025 data extraction.

    WHERE clause filter order (critical for quota optimization):
        1. YEAR = 2025         -> BigQuery eliminates all partitions
                                  outside 2025 before scanning anything
        2. MonthYear BETWEEN   -> Scopes to January-December 2025
        3. Benin conditions    -> Multi-criteria filter with noise removal

    BUG-01 FIX — Actor filter uses CAMEO code 'BEN':
        Actor1CountryCode and Actor2CountryCode use the CAMEO
        3-letter format (e.g. 'BEN'), NOT the GDELT geographic
        2-letter format (e.g. 'BN'). Using 'BN' in actor columns
        returns zero results. COUNTRY_ACTOR_CODE = 'BEN' is now
        used for cases A and B of the filter.

    BENIN CITY NOISE FILTER:
        GDELT sometimes incorrectly tags events from Benin City
        (Nigeria, Edo State) with ActionGeo_CountryCode = 'BN'.
        Case C excludes locations whose full name contains
        'nigeria', 'edo', or 'benin city'.

    limit parameter:
        - sample mode: limit=5000 -> LIMIT clause is added
        - full mode  : limit=None -> NO LIMIT clause
                       -> all available data is retrieved

    Args:
        limit: Maximum number of rows (None = all data)

    Returns:
        str: SQL query ready to execute on BigQuery
    """
    columns_str  = ",\n        ".join(COLUMNS)
    limit_clause = f"\n    LIMIT {limit}" if limit is not None else ""
    limit_info   = f"{limit:,} rows" if limit is not None else "ALL DATA (no limit)"

    query = f"""
    -- ================================================================
    -- GDELT Pipeline - Benin Insights Challenge 2026
    -- Period  : January 2025 to December 2025 (full year)
    -- Country : {COUNTRY_CODE} (Benin - GDELT geographic code, differs from ISO BJ)
    -- Actors  : {COUNTRY_ACTOR_CODE} (Benin - CAMEO actor code)
    -- Project : {GCP_PROJECT_ID}
    -- Extract : {limit_info}
    -- Noise   : Benin City (Nigeria) exclusion active
    -- ================================================================

    SELECT
        {columns_str}

    FROM `{BQ_TABLE_FULL}`

    WHERE
        -- Filter 1 (priority): year
        -- BigQuery eliminates all partitions outside 2025 before scanning.
        -- This filter MUST always be first to save BigQuery quota.
        YEAR = {START_YEAR}

        -- Filter 2: precise months derived from START_YEAR and END_YEAR in config.py
        -- START_MONTHYEAR = {START_MONTHYEAR} (January {START_YEAR})
        -- END_MONTHYEAR   = {END_MONTHYEAR}   (December {END_YEAR})
        AND MonthYear BETWEEN {START_MONTHYEAR} AND {END_MONTHYEAR}

        -- Filter 3: Benin - multi-criteria with noise removal
        AND (
            -- Case A: Benin is the initiating actor (Actor1)
            -- BUG-01 FIX: uses CAMEO code 'BEN', not geographic code 'BN'
            (Actor1CountryCode = '{COUNTRY_ACTOR_CODE}')

            -- Case B: Benin is the receiving actor (Actor2)
            -- BUG-01 FIX: uses CAMEO code 'BEN', not geographic code 'BN'
            OR (Actor2CountryCode = '{COUNTRY_ACTOR_CODE}')

            -- Case C: The event takes place IN BENIN (geographic)
            -- Uses geographic code 'BN' — correct for ActionGeo columns
            -- Noise filter: excludes locations containing 'nigeria',
            -- 'edo' or 'benin city' to remove Benin City (Nigeria)
            -- false positives that GDELT sometimes tags as 'BN'.
            OR (
                ActionGeo_CountryCode = '{COUNTRY_CODE}'
                AND LOWER(ActionGeo_FullName) NOT LIKE '%nigeria%'
                AND LOWER(ActionGeo_FullName) NOT LIKE '%edo%'
                AND LOWER(ActionGeo_FullName) NOT LIKE '%benin city%'
            )
        )
    {limit_clause}
    """

    logger.info(f"[OK] SQL query built - extraction: {limit_info}")
    logger.info("[OK] Benin City (Nigeria) noise filter ACTIVE")
    return query


# ─────────────────────────────────────────────────────────────────
# BIGQUERY EXTRACTION
# ─────────────────────────────────────────────────────────────────

@timer
def extract_data(client: bigquery.Client, limit: int = None) -> pd.DataFrame:
    """
    Execute the BigQuery query and return data as a DataFrame.

    Internal steps:
        1. Build the SQL query via build_query()
        2. Submit the async job to BigQuery with retry support
        3. Block until execution completes
        4. Convert result to pandas DataFrame
        5. Validate the result is not empty

    REC-02: Uses google.api_core.retry.Retry with a 300s deadline
    to handle transient BigQuery failures (temporary quota, timeout).
    In full mode, a query that takes 5 minutes and fails without retry
    forces a complete restart. The retry handles this transparently.

    In full mode (limit=None), BigQuery may take several minutes
    depending on volume — this is expected, the process blocks.

    Args:
        client : BigQuery client initialized via get_bigquery_client()
        limit  : Maximum number of rows. None = all data

    Returns:
        pd.DataFrame: Raw GDELT data for Benin 2025

    Raises:
        ValueError: If the resulting DataFrame is empty
        Exception : If the BigQuery query fails after retries
    """
    mode_log = f"{limit:,} rows" if limit is not None else "ALL DATA"
    logger.info(f"[START] Extraction - Benin 2025 - {mode_log}")

    query = build_query(limit)

    try:
        logger.info("Submitting query to BigQuery...")

        # REC-02: Retry with exponential backoff, 300s deadline
        query_job = client.query(
            query,
            retry=Retry(deadline=300)
        )

        logger.info("Executing - please wait (full mode may take several minutes)...")
        df = query_job.to_dataframe()

        if not validate_dataframe(df, "raw GDELT data"):
            raise ValueError("Extraction returned an empty DataFrame.")

        logger.info(f"[OK] {len(df):,} events successfully extracted")
        return df

    except Exception as e:
        logger.error(f"[ERROR] Extraction failed: {e}")
        raise


# ─────────────────────────────────────────────────────────────────
# RAW DATA SAVE
# ─────────────────────────────────────────────────────────────────

@timer
def save_raw_data(df: pd.DataFrame, filepath) -> None:
    """
    Save raw data as CSV in data/raw/.

    The raw file is kept intact, without any transformation.
    This allows re-running only transform.py if needed,
    without repeating a costly BigQuery extraction.

    Args:
        df      : Raw DataFrame from BigQuery
        filepath: Full path of the output CSV file (str or Path)

    Raises:
        IOError: If writing the file fails
    """
    try:
        df.to_csv(filepath, index=False, encoding="utf-8")
        size_kb = round(os.path.getsize(filepath) / 1024, 1)
        logger.info(f"[OK] Raw data saved: {filepath} ({size_kb} KB)")
    except IOError as e:
        logger.error(f"[ERROR] File write failed: {e}")
        raise


# ─────────────────────────────────────────────────────────────────
# PUBLIC ENTRY POINTS
# ─────────────────────────────────────────────────────────────────

@timer
def run_sample_extraction() -> pd.DataFrame:
    """
    Run a reduced extraction (5,000 rows) for testing.

    Goal: validate that the pipeline works correctly
    (connection, query, data structure) without consuming
    significant BigQuery quota.

    MAJ-05: Only creates SAMPLES_DIR — the directory this function writes to.
    Does not create RAW_DIR (responsibility of run_full_extraction).

    Always run before run_full_extraction().

    Returns:
        pd.DataFrame: Sample of 5,000 Benin 2025 events
    """
    logger.info("=" * 55)
    logger.info("SAMPLE EXTRACTION (5,000 rows) - START")
    logger.info("=" * 55)

    # MAJ-05: Only create the directory this function writes to
    create_directories(SAMPLES_DIR)

    client = get_bigquery_client()
    df     = extract_data(client, limit=SAMPLE_LIMIT)
    save_raw_data(df, SAMPLE_FILE)

    logger.info("SAMPLE EXTRACTION - COMPLETED")
    logger.info("=" * 55)
    return df


@timer
def run_full_extraction() -> pd.DataFrame:
    """
    Run the complete extraction WITHOUT LIMIT on Benin 2025 data.

    Retrieves ALL GDELT events available for Benin between
    January and December 2025, with no LIMIT clause in SQL.

    MAJ-05: Only creates RAW_DIR — the directory this function writes to.
    Does not create SAMPLES_DIR (responsibility of run_sample_extraction).

    WARNING: Run only after validation in sample mode.
    WARNING: Execution may take several minutes on BigQuery.
    WARNING: Consumes more quota than sample mode.

    Returns:
        pd.DataFrame: All Benin 2025 events in GDELT
    """
    logger.info("=" * 55)
    logger.info("FULL EXTRACTION (NO LIMIT) - START")
    logger.info("=" * 55)

    # MAJ-05: Only create the directory this function writes to
    create_directories(RAW_DIR)

    client = get_bigquery_client()
    df     = extract_data(client, limit=None)
    save_raw_data(df, RAW_FILE)

    logger.info("FULL EXTRACTION - COMPLETED")
    logger.info("=" * 55)
    return df