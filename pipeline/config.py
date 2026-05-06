# pipeline/config.py
"""
Central configuration for the GDELT pipeline.
Bénin Insights Challenge 2026 — iSHEERO × DataCamp Donates

This is the ONLY file that needs to be modified per environment.
All other modules import their parameters from here.

AUTHENTICATION (no JSON file required):
    Each team member runs ONCE in their terminal:
        gcloud auth application-default login
    This opens the browser for Google authentication.
    Credentials are then stored locally in a secure way.
    No credential.json file is needed.

ENVIRONMENT VARIABLES:
    Copy .env.example to .env and fill in your values:
        cp .env.example .env
    Never commit .env to version control.

CHANGING PROJECT:
    Set GCP_PROJECT_ID in your .env file.
    Example: GCP_PROJECT_ID=my-project-456789

Author  : Team 7 — Bénin Insights Challenge 2026
Date    : May 2026
Version : 1.2
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
# .env is gitignored — never committed to version control
load_dotenv()

# ─────────────────────────────────────────────────────────────────
# BASE PATHS — using pathlib for cross-platform compatibility
# ─────────────────────────────────────────────────────────────────
# MAJ-04: Use pathlib.Path instead of string concatenation
# to ensure correct behavior on Windows, macOS and Linux.

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR  = BASE_DIR / "data"
RAW_DIR   = DATA_DIR / "raw"

# Data output directories
PROCESSED_DIR = DATA_DIR / "processed"
SAMPLES_DIR   = DATA_DIR / "sample"


# ─────────────────────────────────────────────────────────────────
# GOOGLE CLOUD PROJECT — loaded from environment variable
# ─────────────────────────────────────────────────────────────────
# MAJ-01: GCP_PROJECT_ID must NOT be hardcoded in versioned code.
# It is loaded from the .env file via python-dotenv.
# Each team member sets their own project ID locally.

GCP_PROJECT_ID = os.getenv("GCP_PROJECT_ID")

if not GCP_PROJECT_ID:
    raise ValueError(
        "GCP_PROJECT_ID is not set. "
        "Create a .env file with: GCP_PROJECT_ID=your-project-id\n"
        "See .env.example for reference."
    )


# ─────────────────────────────────────────────────────────────────
# BIGQUERY PARAMETERS — do not modify
# ─────────────────────────────────────────────────────────────────
# GDELT is a public dataset hosted on the "gdelt-bq" project.
# Quota billing applies to YOUR project (GCP_PROJECT_ID),
# not to gdelt-bq. Free quota: 1 TB of queries per month.

BQ_PROJECT    = "gdelt-bq"
BQ_DATASET    = "gdeltv2"
BQ_TABLE      = "events"
BQ_TABLE_FULL = f"{BQ_PROJECT}.{BQ_DATASET}.{BQ_TABLE}"


# ─────────────────────────────────────────────────────────────────
# GEOGRAPHIC FILTER — BENIN
# ─────────────────────────────────────────────────────────────────
# WARNING: GDELT uses TWO different country code systems:
#
#   COUNTRY_CODE       = "BN"  (GDELT geographic format, 2 letters)
#     Used in: ActionGeo_CountryCode
#     Used for: filtering events that TAKE PLACE in Benin
#
#   COUNTRY_ACTOR_CODE = "BEN" (CAMEO format, 3 letters)
#     Used in: Actor1CountryCode, Actor2CountryCode
#     Used for: identifying Benin as an actor or target
#
# BUG-01 FIX: Using the wrong code in actor filters returns zero
# results. Both constants must be used in their correct context.

COUNTRY_CODE       = "BN"   # GDELT geographic code for Benin
COUNTRY_ACTOR_CODE = "BEN"  # CAMEO actor code for Benin
COUNTRY_NAME       = "Benin"

# Neighboring countries for regional benchmark (Question 5)
# Keys are GDELT geographic codes
NEIGHBOR_CODES = {
    "BN": "Bénin",
    "TO": "Togo",
    "NI": "Nigeria",
    "UV": "Burkina Faso",
}


# ─────────────────────────────────────────────────────────────────
# ANALYSIS PERIOD — JANUARY TO DECEMBER 2025
# ─────────────────────────────────────────────────────────────────
# The period is strictly framed on the year 2025 as required
# by the iSHEERO x DataCamp Donates challenge.
#
# The YEAR filter is always placed FIRST in the WHERE clause
# to allow BigQuery to eliminate partitions outside 2025
# before scanning, reducing quota consumption.
#
# MAJ-07: END_YEAR is now used in the SQL query (via END_MONTHYEAR)
# to make the period explicitly parametric. If the analysis period
# changes, only these constants need to be updated.

START_YEAR      = 2025
END_YEAR        = 2025        # Used in SQL via END_MONTHYEAR

START_MONTHYEAR = int(f"{START_YEAR}01")   # e.g. 202501 (January)
END_MONTHYEAR   = int(f"{END_YEAR}12")     # e.g. 202512 (December)


# ─────────────────────────────────────────────────────────────────
# COLUMNS TO EXTRACT FROM BIGQUERY
# ─────────────────────────────────────────────────────────────────
# Precise selection to save BigQuery quota.
# Each column is justified by its analytical question.
# SELECT * would consume 5 to 10x more quota unnecessarily.
#
# Q1 — Media coverage peaks  : SQLDATE, NumArticles, NumMentions, EventRootCode
# Q2 — Media tone over time  : AvgTone, GoldsteinScale, SQLDATE
# Q3 — Propagation delay     : SQLDATE, DATEADDED
# Q4 — Sources crisis vs normal: SOURCEURL, NumArticles, NumSources, AvgTone
# Q5 — Actor or bystander    : Actor1CountryCode, Actor2CountryCode, IsRootEvent

COLUMNS = [
    # -- Unique identifier -----------------------------------------
    "GLOBALEVENTID",    # Unique GDELT event ID — used for exact deduplication

    # -- Temporal --------------------------------------------------
    "SQLDATE",       # Event date in YYYYMMDD format          — Q1, Q2, Q3
    "DATEADDED",     # GDELT indexing date YYYYMMDDHHMMSS     — Q3 propagation delay
    "MonthYear",     # Condensed month-year e.g. 202504       — monthly aggregations
    "Year",          # Year alone                             — priority BigQuery filter

    # -- Actors — Q5 (actor or bystander) -------------------------
    "Actor1Name",           # Name of the initiating actor
    "Actor1Code",           # Compound code: country + type (e.g. BENGOV, BENCVL) — Q5 precision
    "Actor1CountryCode",    # CAMEO country code of actor 1 (3 letters, e.g. BEN)
    "Actor1Type1Code",      # Type of actor 1 (GOV, MIL, BUS, NGO...)
    "Actor2Name",           # Name of the receiving actor
    "Actor2Code",           # Compound code: country + type for actor 2 — Q5 precision
    "Actor2CountryCode",    # CAMEO country code of actor 2 (3 letters)
    "Actor2Type1Code",      # Type of actor 2
    "IsRootEvent",          # 1 = root event, 0 = derived event

    # -- Event classification — Q1 --------------------------------
    "EventCode",            # Precise CAMEO code (e.g. 0231)
    "EventBaseCode",        # Base code, less precise (e.g. 023)
    "EventRootCode",        # Root category among 20 types (e.g. 02)
    "QuadClass",            # 1=Verbal coop 2=Material coop 3=Verbal conflict 4=Material conflict

    # -- Intensity and sentiment — Q1, Q2 -------------------------
    "GoldsteinScale",   # National stability impact [-10, +10]   — Q2
    "AvgTone",          # Average media tone [-100, +100]         — Q2, Q4
    "NumMentions",      # Total number of media mentions          — Q1, Q3
    "NumSources",       # Number of distinct media sources        — Q4
    "NumArticles",      # Number of articles published            — Q1, Q3, Q4

    # -- Geography ------------------------------------------------
    "ActionGeo_FullName",       # Full name of the event location
    "ActionGeo_CountryCode",    # Country code of the location (GDELT 2-letter, e.g. BN)
    "ActionGeo_Type",           # Geographic precision: 1=country 2=region 3=city 4=precise
    "ActionGeo_ADM1Code",       # Administrative subdivision code (e.g. BN18=Littoral/Cotonou)
    "ActionGeo_Lat",            # Latitude for mapping
    "ActionGeo_Long",           # Longitude for mapping

    # -- Media source — Q4 ----------------------------------------
    "SOURCEURL",    # Full URL of the source article
]


# ─────────────────────────────────────────────────────────────────
# BENIN DEPARTMENT MAPPING — ActionGeo_ADM1Code -> French name
# ─────────────────────────────────────────────────────────────────
# Used in transform.py to add an event_department column.
# Enables intra-country geographic analysis and department-level maps.
# Source: GDELT FIPS10-4 geographic codes for Benin.

DEPT_LABELS = {
    "BN00": "National",
    "BN01": "Atakora",
    "BN02": "Atlantique",
    "BN03": "Borgou",
    "BN04": "Mono",
    "BN05": "Ouémé",
    "BN06": "Zou",
    "BN07": "Collines",
    "BN08": "Couffo",
    "BN09": "Donga",
    "BN10": "Littoral",   # Cotonou
    "BN11": "Plateau",
    "BN12": "Alibori",
    "BN13": "Atacora",
    "BN14": "Atlantique",
    "BN15": "Borgou",
    "BN16": "Collines",
    "BN17": "Couffo",
    "BN18": "Donga",
    "BN19": "Littoral",
    "BN20": "Mono",
    "BN21": "Ouémé",
    "BN22": "Plateau",
    "BN23": "Zou",
}

# Geographic precision type labels
GEO_TYPE_LABELS = {
    0: "Inconnu",
    1: "Pays",
    2: "Région administrative",
    3: "Ville",
    4: "Lieu précis",
    5: "Lieu précis",
}


# ─────────────────────────────────────────────────────────────────
# EXTRACTION LIMITS
# ─────────────────────────────────────────────────────────────────
# SAMPLE : used for testing — consumes minimal BigQuery quota.
# FULL   : no limit — retrieves ALL available data for Benin
#          for the period January-December 2025.

SAMPLE_LIMIT = 5_000   # Test sample (quota economy)
# No FULL_LIMIT — full mode retrieves all data without restriction


# ─────────────────────────────────────────────────────────────────
# OUTPUT FILE PATHS
# ─────────────────────────────────────────────────────────────────

RAW_FILE       = RAW_DIR       / "benin_gdelt_raw.csv"
PROCESSED_FILE = PROCESSED_DIR / "benin_gdelt_clean.csv"
PARQUET_FILE   = PROCESSED_DIR / "benin_gdelt_clean.parquet"
JSON_FILE      = PROCESSED_DIR / "benin_gdelt_clean.json"
QUALITY_REPORT = PROCESSED_DIR / "quality_report.json"
SAMPLE_FILE    = SAMPLES_DIR   / "benin_gdelt_sample.csv"


# ─────────────────────────────────────────────────────────────────
# PIPELINE VERSION
# ─────────────────────────────────────────────────────────────────
# MIN-01: Single source of truth for pipeline version.
# Imported by load.py for the quality report.

PIPELINE_VERSION = "1.3"


# ─────────────────────────────────────────────────────────────────
# LOGGING
# ─────────────────────────────────────────────────────────────────

LOG_LEVEL  = "INFO"
LOG_FORMAT = "%(asctime)s - %(levelname)s - %(message)s"