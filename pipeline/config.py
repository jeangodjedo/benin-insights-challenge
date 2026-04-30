# pipeline/config.py
"""
Configuration centrale du pipeline GDELT — Bénin Insights Challenge 2026
iSHEERO × DataCamp Donates

Ce fichier est le SEUL fichier à modifier selon votre environnement.
Tous les autres modules importent leurs paramètres depuis ici.

AUTHENTIFICATION (sans fichier JSON) :
    Chaque membre exécute UNE SEULE FOIS dans son terminal :
        gcloud auth application-default login
    Cette commande ouvre le navigateur pour la connexion Google.
    Les credentials sont ensuite stockés localement de façon sécurisée.
    Aucun fichier credential.json n'est nécessaire.

CHANGER DE PROJET :
    Modifiez uniquement GCP_PROJECT_ID ci-dessous.
    Exemple : GCP_PROJECT_ID = "mon-projet-456789"

Auteur  : Équipe Bénin Insights Challenge 2026
Date    : Avril 2026
Version : 1.1
"""

# ─────────────────────────────────────────────────────────────────
# ⚠️  SEULE VALEUR À MODIFIER SELON VOTRE PROJET GOOGLE CLOUD
# ─────────────────────────────────────────────────────────────────
# Votre Project ID est visible sur console.cloud.google.com
# en haut à gauche dans la barre de navigation.
# Format habituel : "nom-projet-123456"

GCP_PROJECT_ID = "pipelin-event"   # ← REMPLACEZ PAR VOTRE PROJECT ID


# ─────────────────────────────────────────────────────────────────
# PARAMÈTRES BIGQUERY — NE PAS MODIFIER
# ─────────────────────────────────────────────────────────────────
# GDELT est un dataset public hébergé sur le projet "gdelt-bq".
# La facturation du quota s'applique sur VOTRE projet (GCP_PROJECT_ID),
# pas sur gdelt-bq. Le quota gratuit est de 1 TB de requêtes par mois.

BQ_PROJECT    = "gdelt-bq"
BQ_DATASET    = "gdeltv2"
BQ_TABLE      = "events"
BQ_TABLE_FULL = f"{BQ_PROJECT}.{BQ_DATASET}.{BQ_TABLE}"


# ─────────────────────────────────────────────────────────────────
# FILTRE GÉOGRAPHIQUE — BÉNIN
# ─────────────────────────────────────────────────────────────────
# ⚠️  ATTENTION : le code GDELT du Bénin est 'BN'
# Ce code est DIFFÉRENT du code ISO standard qui est 'BJ'.
# Utiliser 'BJ' retournerait zéro résultat dans GDELT.

COUNTRY_CODE = "BN"

# Code CAMEO des acteurs (Actor1CountryCode, Actor2CountryCode) — utilisé pour benin_role
COUNTRY_ACTOR_CODE = "BEN"

COUNTRY_NAME = "Benin"

# Pays voisins inclus pour le benchmark régional (Question 5)
# Chaque entrée : code GDELT → nom du pays
NEIGHBOR_CODES = {
    "BN": "Bénin",
    "TO": "Togo",
    "NI": "Nigeria",
    "UV": "Burkina Faso",
}


# ─────────────────────────────────────────────────────────────────
# PÉRIODE D'ANALYSE — JANVIER À DÉCEMBRE 2025
# ─────────────────────────────────────────────────────────────────
# La période est strictement cadrée sur l'année 2025 comme
# demandé par le challenge iSHEERO × DataCamp Donates.
# Le filtre YEAR est toujours posé EN PREMIER dans le WHERE
# pour permettre à BigQuery d'éliminer les partitions hors période
# avant de scanner les données, réduisant la consommation de quota.

START_YEAR      = 2025
END_YEAR        = 2025
START_MONTHYEAR = 202501   # Janvier 2025
END_MONTHYEAR   = 202512   # Décembre 2025


# ─────────────────────────────────────────────────────────────────
# COLONNES À EXTRAIRE DEPUIS BIGQUERY
# ─────────────────────────────────────────────────────────────────
# Sélection précise pour économiser le quota BigQuery.
# Chaque colonne est justifiée par sa question analytique.
# SELECT * consommerait 5 à 10 fois plus de quota inutilement.
#
# Q1 — Pics de couverture médiatique  : SQLDATE, NumArticles, NumMentions, EventRootCode
# Q2 — Ton médiatique dans le temps   : AvgTone, GoldsteinScale, SQLDATE
# Q3 — Délai de propagation           : SQLDATE, DATEADDED
# Q4 — Sources crise vs normale       : SOURCEURL, NumArticles, NumSources, AvgTone
# Q5 — Acteur ou spectateur           : Actor1CountryCode, Actor2CountryCode, IsRootEvent

COLUMNS = [
    # ── Temporel ──────────────────────────────────────────────────
    "SQLDATE",       # Date de l'événement au format YYYYMMDD  — Q1, Q2, Q3
    "DATEADDED",     # Date d'indexation GDELT YYYYMMDDHHMMSS  — Q3 délai propagation
    "MonthYear",     # Mois-Année condensé ex: 202504           — agrégations mensuelles
    "Year",          # Année seule                              — filtre BigQuery prioritaire

    # ── Acteurs — Q5 (acteur ou spectateur) ───────────────────────
    "Actor1Name",           # Nom de l'acteur initiateur de l'événement
    "Actor1CountryCode",    # Code pays GDELT de l'acteur initiateur
    "Actor1Type1Code",      # Type de l'acteur 1 (GOV, MIL, BUS, NGO...)
    "Actor2Name",           # Nom de l'acteur destinataire de l'événement
    "Actor2CountryCode",    # Code pays GDELT de l'acteur destinataire
    "Actor2Type1Code",      # Type de l'acteur 2
    "IsRootEvent",          # 1 = événement racine, 0 = événement dérivé

    # ── Classification de l'événement — Q1 ───────────────────────
    "EventCode",            # Code CAMEO précis (ex: 0231)
    "EventBaseCode",        # Code de base moins précis (ex: 023)
    "EventRootCode",        # Catégorie racine parmi 20 types (ex: 02)
    "QuadClass",            # 1=Coop verbale 2=Coop mat. 3=Conflit verb. 4=Conflit mat.

    # ── Intensité et sentiment — Q1, Q2 ──────────────────────────
    "GoldsteinScale",   # Impact stabilité nationale [-10, +10]  — Q2
    "AvgTone",          # Ton médiatique moyen [-100, +100]       — Q2, Q4
    "NumMentions",      # Nombre total de mentions dans les médias — Q1, Q3
    "NumSources",       # Nombre de sources médiatiques distinctes — Q4
    "NumArticles",      # Nombre d'articles publiés               — Q1, Q3, Q4

    # ── Géographie ────────────────────────────────────────────────
    "ActionGeo_FullName",       # Nom complet du lieu de l'événement
    "ActionGeo_CountryCode",    # Code pays du lieu (filtre principal = 'BN')
    "ActionGeo_Lat",            # Latitude pour la cartographie
    "ActionGeo_Long",           # Longitude pour la cartographie

    # ── Source médiatique — Q4 ────────────────────────────────────
    "SOURCEURL",    # URL complète de l'article source
]


# ─────────────────────────────────────────────────────────────────
# LIMITES D'EXTRACTION
# ─────────────────────────────────────────────────────────────────
# SAMPLE : utilisé pour les tests — consomme peu de quota BigQuery.
# FULL   : aucune limite — récupère TOUTES les données disponibles
#          pour le Bénin sur la période janvier–décembre 2025.

SAMPLE_LIMIT = 5_000   # Échantillon de test (économie de quota)
# Pas de FULL_LIMIT — le mode full récupère toutes les données


# ─────────────────────────────────────────────────────────────────
# CHEMINS DE FICHIERS DE SORTIE
# ─────────────────────────────────────────────────────────────────

DATA_DIR      = "data"
RAW_DIR       = f"{DATA_DIR}/raw"
PROCESSED_DIR = f"{DATA_DIR}/clean"
SAMPLES_DIR   = f"{DATA_DIR}/sample"

RAW_FILE       = f"{RAW_DIR}/benin_gdelt_raw.csv"
PROCESSED_FILE = f"{PROCESSED_DIR}/benin_gdelt_clean.csv"
PARQUET_FILE   = f"{PROCESSED_DIR}/benin_gdelt_clean.parquet"
JSON_FILE      = f"{PROCESSED_DIR}/benin_gdelt_clean.json"
QUALITY_REPORT = f"{PROCESSED_DIR}/quality_report.json"
SAMPLE_FILE    = f"{SAMPLES_DIR}/benin_gdelt_sample.csv"


# ─────────────────────────────────────────────────────────────────
# LOGGING
# ─────────────────────────────────────────────────────────────────

LOG_LEVEL  = "INFO"
LOG_FORMAT = "%(asctime)s — %(levelname)s — %(message)s"