"""
Fonctions utilitaires transversales du pipeline GDELT.

Ce module est importé par tous les autres modules du pipeline.
Il fournit les outils communs suivants :

    - logger            : système de logs standardisé pour tout le pipeline
    - timer             : décorateur mesurant le temps d'exécution des fonctions
    - create_directories: automatic creation of working directories
    - validate_dataframe: vérification de la validité des DataFrames

Auteur  : Équipe Bénin Insights Challenge 2026
Date    : Avril 2026
Version : 1.0
"""

import os
import time
import logging
import functools
import pandas as pd
from .config import LOG_LEVEL, LOG_FORMAT


# ─────────────────────────────────────────────────────────────────
# LOGGING
# ─────────────────────────────────────────────────────────────────

def setup_logger(name: str = "gdelt_pipeline") -> logging.Logger:
    """
    Configure and return a standardized logger for the entire pipeline.

    The logger is used in all modules to display information,
    warning and error messages in the terminal with a coherent format.

    Output format:
        2026-04-29 10:32:15 — INFO — Message here

    Args:
        name: Logger name (default 'gdelt_pipeline')

    Returns:
        logging.Logger: Configured logger ready to use
    """
    logger = logging.getLogger(name)
    if not logger.handlers:  # Prevent duplicate handlers
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter(LOG_FORMAT))
        logger.addHandler(handler)
        logger.setLevel(getattr(logging, LOG_LEVEL))
        logger.propagate = False  # Do not propagate to root logger
    return logger


# Instance globale du logger — importée par tous les modules du pipeline
logger = setup_logger()


# ─────────────────────────────────────────────────────────────────
# DÉCORATEUR TIMER
# ─────────────────────────────────────────────────────────────────

def timer(func):
    """
    Decorator that measures and logs the execution time of a function.

    Applied to all main pipeline functions to identify slow stages
    and document performance in logs. Useful for monitoring and debugging.

    Usage:
        @timer
        def my_function():
            ...

    Logs:
        INFO — Starting: my_function
        INFO — Completed: my_function — 3.42s

    Args:
        func: Function to decorate

    Returns:
        function: Wrapped function with timing
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start = time.time()
        logger.info(f"Starting: {func.__name__}")
        result = func(*args, **kwargs)
        duration = round(time.time() - start, 2)
        logger.info(f"Completed: {func.__name__} — {duration}s")
        return result
    return wrapper


# ─────────────────────────────────────────────────────────────────
# CRÉATION DES DOSSIERS
# ─────────────────────────────────────────────────────────────────

def create_directories(*paths: str) -> None:
    """
    Crée les dossiers nécessaires au pipeline s'ils n'existent pas.

    Called at the start of each extraction and load to ensure directories exist.
    s'assurer que les dossiers data/raw/, data/clean/ et
    data/sample/ existent avant toute tentative d'écriture.

    Utilise os.makedirs avec exist_ok=True — aucune erreur si le
    dossier existe déjà. Crée également les dossiers parents
    intermédiaires si nécessaire.

    Args:
        *paths: Un ou plusieurs chemins de dossiers à créer

    Example:
        create_directories("data/raw", "data/clean", "data/sample")
    """
    for path in paths:
        os.makedirs(path, exist_ok=True)
        logger.info(f"Dossier prêt : {path}")


# ─────────────────────────────────────────────────────────────────
# VALIDATION DES DATAFRAMES
# ─────────────────────────────────────────────────────────────────

def validate_dataframe(df: pd.DataFrame, name: str = "dataframe") -> bool:
    """
    Vérifie qu'un DataFrame pandas est valide et non vide.

    Called between each pipeline step to detect data issues early.
    après transformation, avant chargement) pour détecter
    immédiatement tout problème de données et éviter de propager
    un DataFrame vide ou None aux étapes suivantes.

    Affiche dans les logs :
        - Nombre de lignes et de colonnes
        - Liste des valeurs manquantes par colonne (si présentes)

    Args:
        df  : DataFrame pandas à valider
        name: Nom descriptif du DataFrame pour les messages de log

    Returns:
        bool: True si le DataFrame est valide et non vide,
              False si le DataFrame est None ou vide

    Example:
        if not validate_dataframe(df, "raw data"):
            raise ValueError("DataFrame invalide")
    """
    # Vérification que le DataFrame existe et n'est pas vide
    if df is None or df.empty:
        logger.error(f"{name} est vide ou None — pipeline interrompu")
        return False

    # Affichage du résumé dimensionnel
    logger.info(f"{name} — {len(df):,} lignes × {len(df.columns)} colonnes")

    # Détection et affichage des valeurs manquantes par colonne
    missing = df.isnull().sum()
    missing = missing[missing > 0]
    if not missing.empty:
        logger.warning(" Valeurs manquantes détectées :")
        for col, count in missing.items():
            pct = round(count / len(df) * 100, 1)
            logger.warning(f"   → {col} : {count:,} valeurs manquantes ({pct}%)")

    return True