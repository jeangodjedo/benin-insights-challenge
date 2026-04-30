"""
Module d'extraction des données GDELT depuis Google BigQuery.

Étape 1 du pipeline ETL — Extract.

AUTHENTIFICATION :
    Ce module n'utilise AUCUN fichier credential.json.
    L'authentification repose sur Application Default Credentials (ADC).
    Chaque membre exécute une seule fois :
        gcloud auth application-default login
    Le GCP_PROJECT_ID dans config.py identifie le projet de facturation.

DEUX MODES D'EXTRACTION :
    - sample : 5 000 lignes avec LIMIT — pour tester le pipeline
    - full   : SANS LIMIT — récupère TOUTES les données du Bénin 2025

CORRECTION DU BRUIT BENIN CITY :
    La requête SQL contient désormais un filtre anti-bruit pour
    exclure les événements localisés à Benin City (Nigeria) qui
    sont parfois tagués 'BN' par erreur dans GDELT.

OPTIMISATION QUOTA BIGQUERY :
    - SELECT sur colonnes précises (jamais SELECT *)
    - Filtre YEAR posé EN PREMIER dans le WHERE
    - Filtre MonthYear pour cerner janvier–décembre 2025 exactement

Auteur  : Équipe Bénin Insights Challenge 2026
Date    : Avril 2026
Version : 1.1 — Correction du bruit Benin City (Nigeria)
"""

import os
import pandas as pd
from google.cloud import bigquery

from config import (
    GCP_PROJECT_ID,
    BQ_TABLE_FULL,
    COUNTRY_CODE,
    START_YEAR,
    START_MONTHYEAR,
    END_MONTHYEAR,
    COLUMNS,
    SAMPLE_LIMIT,
    RAW_FILE,
    SAMPLE_FILE,
    RAW_DIR,
    SAMPLES_DIR,
)
from utils import logger, timer, create_directories, validate_dataframe


# ─────────────────────────────────────────────────────────────────
# INITIALISATION DU CLIENT BIGQUERY
# ─────────────────────────────────────────────────────────────────

def get_bigquery_client() -> bigquery.Client:
    """
    Initialise et retourne un client BigQuery authentifié.

    Utilise Application Default Credentials (ADC) — aucun fichier
    JSON requis. L'authentification est gérée par la commande :
        gcloud auth application-default login

    Le paramètre project=GCP_PROJECT_ID indique à BigQuery sur quel
    projet Google Cloud imputer la consommation de quota.

    Returns:
        bigquery.Client: Client BigQuery prêt à recevoir des requêtes

    Raises:
        Exception: Si l'authentification ADC échoue. Dans ce cas,
                   exécutez : gcloud auth application-default login
    """
    try:
        # project= = VOTRE projet (facturation quota)
        # Les données GDELT restent sur gdelt-bq (projet public)
        client = bigquery.Client(project=GCP_PROJECT_ID)
        logger.info(f"Connexion BigQuery — projet : {GCP_PROJECT_ID}")
        return client
    except Exception as e:
        logger.error(f"Échec connexion BigQuery : {e}")
        logger.error("   Solution : gcloud auth application-default login")
        raise


# ─────────────────────────────────────────────────────────────────
# CONSTRUCTION DE LA REQUÊTE SQL (CORRIGÉE)
# ─────────────────────────────────────────────────────────────────

def build_query(limit: int = None) -> str:
    """
    Construit la requête SQL optimisée pour le Bénin 2025.

    Ordre des filtres WHERE (critique pour l'optimisation quota) :
        1. YEAR = 2025         → BigQuery élimine toutes les partitions
                                  hors 2025 avant de scanner quoi que ce soit
        2. MonthYear BETWEEN   → Affine sur janvier–décembre 2025
        3. Conditions Bénin    → Filtre multi-critères avec anti-bruit

    FILTRE ANTI-BRUIT BENIN CITY (Nigeria) :
        GDELT tague parfois des événements de Benin City (Nigeria)
        avec ActionGeo_CountryCode = 'BN'. Pour exclure ces faux
        positifs, on vérifie que :
        - Si l'événement est localisé au Bénin (ActionGeo_CountryCode = 'BN'),
          le nom complet du lieu NE contient PAS :
            • "nigeria"
            • "edo" (état nigérian dont la capitale est Benin City)
            • "benin city"

    Le paramètre limit est optionnel :
        - En mode sample : limit=5000 → clause LIMIT ajoutée
        - En mode full   : limit=None → AUCUNE clause LIMIT
                           → toutes les données sont récupérées

    Args:
        limit: Nombre max de lignes (None = toutes les données)

    Returns:
        str: Requête SQL prête à exécuter sur BigQuery
    """
    columns_str = ",\n        ".join(COLUMNS)

    limit_clause = f"\n    LIMIT {limit}" if limit is not None else ""
    limit_info   = f"{limit:,} lignes" if limit is not None else "TOUTES LES DONNÉES (sans limite)"

    query = f"""
    -- ================================================================
    -- Pipeline GDELT — Bénin Insights Challenge 2026
    -- Période    : Janvier 2025 → Décembre 2025 (année complète)
    -- Pays       : {COUNTRY_CODE} (Bénin — code GDELT, différent du code ISO BJ)
    -- Projet     : {GCP_PROJECT_ID}
    -- Extraction : {limit_info}
    -- Anti-bruit : Exclusion de Benin City (Nigeria)
    -- ================================================================

    SELECT
        {columns_str}

    FROM `{BQ_TABLE_FULL}`

    WHERE
        -- FILTRE 1 (prioritaire) : année
        -- BigQuery supprime toutes les partitions hors 2025 avant de scanner.
        -- Ce filtre DOIT toujours être en premier pour économiser le quota.
        YEAR = {START_YEAR}

        -- FILTRE 2 : mois précis — janvier (202501) à décembre (202512)
        AND MonthYear BETWEEN {START_MONTHYEAR} AND {END_MONTHYEAR}

        -- FILTRE 3 : Bénin — multi-critères avec anti-bruit Benin City
        AND (
            -- Cas A : Le Bénin est l'acteur principal (initiateur)
            -- On vérifie le code pays pour éviter les homonymes
            (Actor1CountryCode = '{COUNTRY_CODE}')

            -- Cas B : Le Bénin est l'acteur secondaire (destinataire)
            OR (Actor2CountryCode = '{COUNTRY_CODE}')

            -- Cas C : L'événement se déroule AU BÉNIN
            -- ⚠️  Anti-bruit : on exclut les lieux qui contiennent
            --     "nigeria", "edo" ou "benin city" dans leur nom complet.
            --     Cela filtre les événements de Benin City (Nigeria)
            --     qui sont parfois tagués 'BN' par erreur dans GDELT.
            OR (
                ActionGeo_CountryCode = '{COUNTRY_CODE}'
                AND LOWER(ActionGeo_FullName) NOT LIKE '%nigeria%'
                AND LOWER(ActionGeo_FullName) NOT LIKE '%edo%'
                AND LOWER(ActionGeo_FullName) NOT LIKE '%benin city%'
            )
        )
    {limit_clause}
    """

    logger.info(f"Requête construite — extraction : {limit_info}")
    logger.info("Filtre anti-bruit Benin City (Nigeria) ACTIF")
    return query


# ─────────────────────────────────────────────────────────────────
# EXTRACTION DEPUIS BIGQUERY
# ─────────────────────────────────────────────────────────────────

@timer
def extract_data(client: bigquery.Client, limit: int = None) -> pd.DataFrame:
    """
    Exécute la requête BigQuery et retourne les données en DataFrame.

    Processus interne :
        1. Construction de la requête SQL via build_query()
        2. Soumission du job asynchrone à BigQuery
        3. Attente bloquante de la fin d'exécution
        4. Conversion du résultat en DataFrame pandas
        5. Validation que le DataFrame n'est pas vide

    En mode full (limit=None), BigQuery peut prendre plusieurs
    minutes selon le volume — c'est normal, le processus est bloquant.

    Args:
        client : Client BigQuery initialisé via get_bigquery_client()
        limit  : Nombre max de lignes. None = toutes les données

    Returns:
        pd.DataFrame: Données brutes GDELT pour le Bénin 2025

    Raises:
        ValueError: Si le DataFrame résultant est vide
        Exception : Si la requête BigQuery échoue
    """
    mode_log = f"{limit:,} lignes" if limit is not None else "TOUTES LES DONNÉES"
    logger.info(f"Début extraction — Bénin 2025 — {mode_log}")

    query = build_query(limit)

    try:
        logger.info("Soumission de la requête à BigQuery...")
        query_job = client.query(query)

        logger.info("Exécution en cours — patience si mode full...")
        df = query_job.to_dataframe()

        if not validate_dataframe(df, "données brutes GDELT"):
            raise ValueError("L'extraction a retourné un DataFrame vide.")

        logger.info(f" {len(df):,} événements extraits")
        return df

    except Exception as e:
        logger.error(f" Erreur extraction : {e}")
        raise


# ─────────────────────────────────────────────────────────────────
# SAUVEGARDE DES DONNÉES BRUTES
# ─────────────────────────────────────────────────────────────────

@timer
def save_raw_data(df: pd.DataFrame, filepath: str) -> None:
    """
    Sauvegarde les données brutes en CSV dans data/raw/.

    Le fichier brut est conservé intact, sans aucune transformation.
    Cela permet de relancer uniquement transform.py si nécessaire,
    sans refaire une extraction BigQuery coûteuse en quota.

    Args:
        df      : DataFrame brut issu de BigQuery
        filepath: Chemin complet du fichier CSV de sortie

    Raises:
        IOError: Si l'écriture du fichier échoue
    """
    try:
        df.to_csv(filepath, index=False, encoding="utf-8")
        size_kb = round(os.path.getsize(filepath) / 1024, 1)
        logger.info(f"✅ Données brutes sauvegardées : {filepath} ({size_kb} KB)")
    except IOError as e:
        logger.error(f"❌ Erreur écriture fichier : {e}")
        raise


# ─────────────────────────────────────────────────────────────────
# POINTS D'ENTRÉE PUBLICS
# ─────────────────────────────────────────────────────────────────

@timer
def run_sample_extraction() -> pd.DataFrame:
    """
    Lance une extraction réduite à 5 000 lignes pour les tests.

    Objectif : valider que le pipeline fonctionne correctement
    (connexion, requête, structure des données) sans consommer
    de quota BigQuery significatif.

    À utiliser systématiquement avant run_full_extraction().

    Returns:
        pd.DataFrame: Échantillon de 5 000 événements du Bénin 2025
    """
    logger.info("=" * 55)
    logger.info("EXTRACTION ÉCHANTILLON (5 000 lignes) — DÉMARRAGE")
    logger.info("=" * 55)

    create_directories(RAW_DIR, SAMPLES_DIR)
    client = get_bigquery_client()

    df = extract_data(client, limit=SAMPLE_LIMIT)
    save_raw_data(df, SAMPLE_FILE)

    logger.info("EXTRACTION ÉCHANTILLON — TERMINÉE")
    logger.info("=" * 55)
    return df


@timer
def run_full_extraction() -> pd.DataFrame:
    """
    Lance l'extraction complète SANS LIMITE sur les données du Bénin 2025.

    Cette fonction récupère TOUS les événements GDELT disponibles
    pour le Bénin entre janvier et décembre 2025, sans aucune
    clause LIMIT dans la requête SQL.

    ⚠️  À utiliser uniquement après validation en mode sample.
    ⚠️  L'exécution peut prendre plusieurs minutes sur BigQuery.
    ⚠️  Consomme plus de quota que le mode sample.

    Returns:
        pd.DataFrame: Tous les événements du Bénin 2025 dans GDELT
    """
    logger.info("=" * 55)
    logger.info("EXTRACTION COMPLÈTE (SANS LIMITE) — DÉMARRAGE")
    logger.info("=" * 55)

    create_directories(RAW_DIR, SAMPLES_DIR)
    client = get_bigquery_client()

    df = extract_data(client, limit=None)
    save_raw_data(df, RAW_FILE)

    logger.info("EXTRACTION COMPLÈTE — TERMINÉE")
    logger.info("=" * 55)
    return df