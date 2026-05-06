"""
GDELT data transformation and cleaning module.

ETL Pipeline Step 2 — Transform.

Transformations aligned with the 5 priority analytical questions:

    Q1 — When does the world talk about Benin?
         Added columns: event_date, event_month, event_quarter,
                        event_root_label

    Q2 — Is the global media tone positive, neutral or negative?
         Added columns: tone_category, stability_category

    Q3 — How many days to reach the media coverage peak?
         Added columns: propagation_delay_days

    Q4 — Are media sources during crises different from normal periods?
         Added columns: source_domain, is_crisis_period

    Q5 — Is Benin an actor or a bystander in international events?
         Added columns: benin_role, actor1_type_label,
                        actor2_type_label, quad_class_label

For full version history, see CHANGELOG.md at the project root.

Author  : Team 7 — Bénin Insights Challenge 2026
Date    : May 2026
Version : 1.3
"""

import re
import pandas as pd
import numpy as np
from .utils import logger, timer, validate_dataframe
from .config import COUNTRY_ACTOR_CODE, DEPT_LABELS, GEO_TYPE_LABELS


# ─────────────────────────────────────────────────────────────────
# GDELT TRANSLATION DICTIONARIES
# ─────────────────────────────────────────────────────────────────

# QuadClass -> French label
# QuadClass classifies each event into 4 main families
QUAD_CLASS_LABELS = {
    1: "Coopération verbale",
    2: "Coopération matérielle",
    3: "Conflit verbal",
    4: "Conflit matériel",
}

# EventRootCode -> French label
# GDELT classifies all events into 20 root categories.
# Keys are zero-padded strings on 2 characters ("01"..."20")
# as produced after conversion in enrich_data().
EVENT_ROOT_LABELS = {
    "01": "Déclaration publique",
    "02": "Appel / Demande",
    "03": "Expression d'intention",
    "04": "Consultation",
    "05": "Engagement / Soutien",
    "06": "Coopération",
    "07": "Aide matérielle",
    "08": "Diplomatie",
    "09": "Sanctions économiques",
    "10": "Demande",
    "11": "Désapprobation",
    "12": "Rejet",
    "13": "Menace",
    "14": "Protestation",
    "15": "Ultimatum",
    "16": "Violation droits humains",
    "17": "Assaut",
    "18": "Attentat / Explosion",
    "19": "Violence de masse",
    "20": "Force militaire",
}

# Actor Type -> French label
# Used for Q5 — identifying who talks about Benin
ACTOR_TYPE_LABELS = {
    "GOV": "Gouvernement",
    "MIL": "Militaire",
    "REB": "Rebelle / Insurgé",
    "OPP": "Opposition politique",
    "PTY": "Parti politique",
    "COP": "Police",
    "JUD": "Justice",
    "SPY": "Renseignement",
    "MED": "Médias",
    "EDU": "Éducation",
    "BUS": "Entreprise",
    "CRM": "Criminalité",
    "CVL": "Civil / Population",
    "REF": "Réfugié",
    "NGO": "ONG",
    "IGO": "Organisation internationale",
    "HLH": "Santé",
    "LEG": "Parlement / Législatif",
    "AGR": "Agriculture",
    "REL": "Religion",
    "LAB": "Syndicat / Travail",
    "ELI": "Élite politique",
    "UAF": "Forces armées non identifiées",
}


# ─────────────────────────────────────────────────────────────────
# STEP 1 — BASIC CLEANING
# ─────────────────────────────────────────────────────────────────

@timer
def clean_basic(df: pd.DataFrame) -> pd.DataFrame:
    """
    Basic cleaning: duplicates and missing critical rows.

    Operations:
    - Remove fully duplicated rows
    - Remove rows without date (SQLDATE) — unusable
    - Remove rows without source URL (SOURCEURL) — unverifiable
    - Reset index for clean sequential indexing

    Args:
        df: Raw DataFrame from extract.py

    Returns:
        pd.DataFrame: Cleaned DataFrame
    """
    n = len(df)
    logger.info(f"Basic cleaning - {n:,} rows in")

    # GLOBALEVENTID-based deduplication — exact and without data loss.
    # Generic drop_duplicates() on all columns risks removing distinct
    # events that happen to share many column values.
    if "GLOBALEVENTID" in df.columns:
        df = df.drop_duplicates(subset=["GLOBALEVENTID"])
    else:
        df = df.drop_duplicates()

    df = df.dropna(subset=["SQLDATE"])
    df = df.dropna(subset=["SOURCEURL"])
    df = df.reset_index(drop=True)

    logger.info(f"[OK] Basic cleaning done - {n - len(df):,} rows removed, {len(df):,} kept")
    return df


# ─────────────────────────────────────────────────────────────────
# STEP 2 — TYPE CONVERSION
# ─────────────────────────────────────────────────────────────────

@timer
def convert_types(df: pd.DataFrame) -> pd.DataFrame:
    """
    Convert each column to its appropriate Python/pandas type.

    Conversions performed:
    - SQLDATE (int YYYYMMDD)          -> pandas datetime
    - DATEADDED (int YYYYMMDDHHMMSS)  -> pandas datetime (for Q3)
    - GoldsteinScale, AvgTone, coords -> float
    - NumArticles, NumMentions, etc.  -> int
    - EventRootCode                   -> left as-is here, converted
                                         in enrich_data() with a more
                                         reliable int->str->zfill(2) logic

    Note v1.3: EventRootCode is NOT converted to str.zfill(2) here
    because BigQuery returns a native int64 (e.g. 4, 19) which pandas
    converts to "4" not "04" with a simple astype(str).
    The correct conversion is done in enrich_data() just before
    mapping to EVENT_ROOT_LABELS.

    Args:
        df: DataFrame after basic cleaning

    Returns:
        pd.DataFrame: DataFrame with correct types
    """
    logger.info("Type conversion...")

    # Date conversion: GDELT SQLDATE format YYYYMMDD -> datetime
    df["SQLDATE"] = pd.to_datetime(
        df["SQLDATE"].astype(str).str[:8],
        format="%Y%m%d",
        errors="coerce"   # Invalid dates become NaT
    )

    # DATEADDED format GDELT YYYYMMDDHHMMSS -> datetime (Q3)
    # Fix: preserve all 14 characters to retain hour/minute/second precision.
    # The previous str[:8] truncated to date-only, making all events
    # indexed on the same day appear to have identical propagation delays.
    if "DATEADDED" in df.columns:
        df["DATEADDED"] = pd.to_datetime(
            df["DATEADDED"].astype(str).str[:14],
            format="%Y%m%d%H%M%S",
            errors="coerce"
        )

    # Continuous numeric columns
    for col in ["GoldsteinScale", "AvgTone", "ActionGeo_Lat", "ActionGeo_Long"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Integer numeric columns
    for col in ["NumArticles", "NumMentions", "NumSources", "IsRootEvent", "QuadClass"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)

    logger.info("[OK] Types converted")
    return df


# ─────────────────────────────────────────────────────────────────
# STEP 3 — ENRICHMENT (Q1 -> Q5)
# ─────────────────────────────────────────────────────────────────

@timer
def enrich_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add derived columns aligned with the 5 analytical questions.

    Q1 - event_date, event_month, event_quarter, event_root_label
    Q2 - tone_category, stability_category
    Q3 - propagation_delay_days
    Q4 - source_domain, is_crisis_period
    Q5 - benin_role, actor1_type_label, actor2_type_label, quad_class_label

    Args:
        df: DataFrame after type conversion

    Returns:
        pd.DataFrame: Enriched DataFrame with all derived columns
    """
    logger.info("Data enrichment (Q1 -> Q5)...")

    # -- Q1: Temporal columns and event type ----------------------
    df["event_date"]    = df["SQLDATE"].dt.strftime("%Y-%m-%d")
    df["event_month"]   = df["SQLDATE"].dt.month
    df["event_quarter"] = df["SQLDATE"].dt.to_period("Q").astype(str)

    # v1.3 BUG-03 FIX: Removed dead code (lines 249-256 of previous version).
    # The previous version had two blocks computing event_root_label.
    # The first block (via .dropna() chain) produced a result that was
    # never assigned to df["event_root_label"] — it was dead code.
    # Only the correct block below (via apply lambda) is kept.
    #
    # v1.2 FIX: EventRootCode arrives from BigQuery as int64 (e.g. 4, 19).
    # A simple astype(str) gives "4" not "04".
    # Solution: convert via float() -> int() -> str() -> zfill(2)
    # to guarantee "04", "19", etc. regardless of the input type.
    df["event_root_label"] = (
        df["EventRootCode"]
        .apply(lambda x: str(int(float(x))).zfill(2) if pd.notna(x) else None)
        .map(EVENT_ROOT_LABELS)
        .fillna("Autre")
    )

    # Intra-Benin geographic breakdown — enabled by ActionGeo_ADM1Code
    # Maps FIPS10-4 subdivision codes to French department names.
    # Enables department-level analysis and choropleth maps.
    if "ActionGeo_ADM1Code" in df.columns:
        df["event_department"] = (
            df["ActionGeo_ADM1Code"]
            .map(DEPT_LABELS)
            .fillna("Bénin (général)")
        )
    else:
        df["event_department"] = "Bénin (général)"

    # Geographic precision level — enables filtering by location quality
    # 1=country-level only, 3=city, 4=precise point
    if "ActionGeo_Type" in df.columns:
        df["action_geo_precision"] = (
            df["ActionGeo_Type"]
            .map(GEO_TYPE_LABELS)
            .fillna("Inconnu")
        )
    else:
        df["action_geo_precision"] = "Inconnu"

    logger.info("  Q1 [OK]")

    # -- Q2: Tone and stability categories ------------------------
    # AvgTone: [-100, +100] — thresholds calibrated on GDELT Africa
    def tone_cat(v: float) -> str:
        """Categorize the media tone of a GDELT event."""
        if pd.isna(v):  return "Inconnu"
        return "Positif" if v > 2 else ("Négatif" if v < -2 else "Neutre")

    # GoldsteinScale: [-10, +10] — national stability impact
    def stability_cat(v: float) -> str:
        """Categorize the national stability impact of an event."""
        if pd.isna(v):  return "Inconnu"
        return "Stabilisant" if v > 3 else ("Déstabilisant" if v < -3 else "Neutre")

    df["tone_category"]      = df["AvgTone"].apply(tone_cat)
    df["stability_category"] = df["GoldsteinScale"].apply(stability_cat)
    logger.info("  Q2 [OK]")

    # -- Q3: Media propagation delay ------------------------------
    # Measures the number of days between:
    #   - SQLDATE   : date the event occurred
    #   - DATEADDED : date GDELT indexed the event
    # Delay of 0 = immediate coverage
    # Delay > 7   = late coverage
    if "DATEADDED" in df.columns:
        df["propagation_delay_days"] = (
            (df["DATEADDED"] - df["SQLDATE"])
            .dt.days
            .clip(lower=0)  # Ignore negative values (data errors)
        )
    else:
        df["propagation_delay_days"] = np.nan
        logger.warning("[WARN] DATEADDED column absent, propagation_delay_days = NaN")
    logger.info("  Q3 [OK]")

    # -- Q4: Source domain and crisis period detection ------------
    def extract_domain(url: str) -> str:
        """
        Extract domain name from a GDELT source URL.
        Example: "https://www.rfi.fr/fr/afrique/..." -> "rfi.fr"
        """
        if pd.isna(url) or url == "":
            return "unknown"
        try:
            domain = re.sub(r"https?://(www\.)?", "", str(url))
            return domain.split("/")[0].lower()
        except Exception:
            return "unknown"

    df["source_domain"] = df["SOURCEURL"].apply(extract_domain)

    # Crisis period: very negative tone OR very destabilizing event
    # Thresholds are adjustable based on exploratory analysis results
    df["is_crisis_period"] = (
        (df["AvgTone"] < -5.0) | (df["GoldsteinScale"] < -5.0)
    )
    logger.info("  Q4 [OK]")

    # -- Q5: Benin's role — Actor, Bystander, Mixed or Context -----
    #
    # MAJ-06 FIX: Replaced df.apply(func, axis=1) with vectorized
    # pandas operations. apply(axis=1) runs a Python loop on each row,
    # which is significantly slower on large DataFrames (full mode).
    # Vectorized operations use numpy under the hood — much faster.
    #
    # Logic:
    # - "Acteur"     : Benin is Actor1 (initiator of the event)
    # - "Spectateur" : Benin is Actor2 (target/object of the event)
    # - "Mixte"      : Benin is both (internal Beninese event)
    # - "Contexte"   : Benin is neither actor nor target but the event
    #                  takes place on its territory

    # Normalize actor country codes: NaN -> "", strip whitespace, uppercase
    # This avoids NaN being converted to string "nan" which never matches "BEN"
    a1 = df["Actor1CountryCode"].fillna("").str.strip().str.upper()
    a2 = df["Actor2CountryCode"].fillna("").str.strip().str.upper()
    bn = COUNTRY_ACTOR_CODE.strip().upper()  # "BEN"

    # Start with default value
    df["benin_role"] = "Contexte"

    # Apply in order: Acteur, Spectateur, then Mixte (overrides previous)
    df.loc[a1 == bn, "benin_role"] = "Acteur"
    df.loc[a2 == bn, "benin_role"] = "Spectateur"
    df.loc[(a1 == bn) & (a2 == bn), "benin_role"] = "Mixte"  # Override both

    # Translate actor type codes to French labels
    df["actor1_type_label"] = (
        df["Actor1Type1Code"]
        .map(ACTOR_TYPE_LABELS)
        .fillna("Non identifié")
    )
    df["actor2_type_label"] = (
        df["Actor2Type1Code"]
        .map(ACTOR_TYPE_LABELS)
        .fillna("Non identifié")
    )

    # Translate QuadClass to French label
    df["quad_class_label"] = (
        df["QuadClass"]
        .map(QUAD_CLASS_LABELS)
        .fillna("Inconnu")
    )
    logger.info("  Q5 [OK]")

    logger.info("[OK] Enrichment completed")
    return df


# ─────────────────────────────────────────────────────────────────
# STEP 4 — FINAL FILTERING
# ─────────────────────────────────────────────────────────────────

@timer
def filter_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Final quality filtering of the data.

    Filters applied:
    - Remove rows with invalid dates (NaT after conversion)
    - Remove GPS coordinates outside valid geographic bounds
      (latitude outside [-90, 90] or longitude outside [-180, 180])

    Args:
        df: Enriched DataFrame

    Returns:
        pd.DataFrame: Clean, validated DataFrame ready for the team
    """
    n = len(df)
    logger.info(f"Final filtering - {n:,} rows in")

    # Remove invalid dates generated during type conversion
    df = df.dropna(subset=["SQLDATE"])
    logger.info(f"  After invalid date filter : {len(df):,} rows")

    # Remove aberrant GPS coordinates
    if "ActionGeo_Lat" in df.columns:
        df = df[
            df["ActionGeo_Lat"].isna() |
            df["ActionGeo_Lat"].between(-90, 90)
        ]
    if "ActionGeo_Long" in df.columns:
        df = df[
            df["ActionGeo_Long"].isna() |
            df["ActionGeo_Long"].between(-180, 180)
        ]
    logger.info(f"  After GPS coordinate filter: {len(df):,} rows")

    logger.info(f"[OK] Final filtering done - {n - len(df):,} rows removed")
    return df


# ─────────────────────────────────────────────────────────────────
# MAIN ORCHESTRATION FUNCTION
# ─────────────────────────────────────────────────────────────────

@timer
def run_transform(df: pd.DataFrame) -> pd.DataFrame:
    """
    Orchestrate all 4 transformation steps in order.

    Full pipeline:
        1. clean_basic()   - duplicate and critical row removal
        2. convert_types() - data type conversion
        3. enrich_data()   - derived column addition Q1 -> Q5
        4. filter_data()   - final quality filtering

    Args:
        df: Raw DataFrame from extract.py

    Returns:
        pd.DataFrame: Clean, enriched data ready for the team

    Raises:
        ValueError: If the input DataFrame is invalid or empty
    """
    logger.info("=" * 55)
    logger.info("TRANSFORM - START")
    logger.info("=" * 55)

    if not validate_dataframe(df, "raw data"):
        raise ValueError("Invalid input DataFrame - transformation cancelled.")

    df = clean_basic(df)
    df = convert_types(df)
    df = enrich_data(df)
    df = filter_data(df)

    validate_dataframe(df, "final transformed data")

    logger.info("=" * 55)
    logger.info("TRANSFORM - COMPLETED")
    logger.info("=" * 55)
    return df