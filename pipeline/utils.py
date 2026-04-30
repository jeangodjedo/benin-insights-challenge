"""
Fonctions utilitaires transversales du pipeline GDELT.

Ce module est importé par tous les autres modules du pipeline.
Il fournit les outils communs suivants :

    - logger            : système de logs standardisé pour tout le pipeline
    - timer             : décorateur mesurant le temps d'exécution des fonctions
    - create_directories: création automatique des dossiers de travail
    - validate_dataframe: vérification de la validité des DataFrames

Auteur  : Équipe Bénin Insights Challenge 2026
Date    : Avril 2026
Version : 1.0
"""

import os
import time
import logging
from config import LOG_LEVEL, LOG_FORMAT


# ─────────────────────────────────────────────────────────────────
# LOGGING
# ─────────────────────────────────────────────────────────────────

def setup_logger(name: str = "gdelt_pipeline") -> logging.Logger:
    """
    Configure et retourne un logger standardisé pour tout le pipeline.

    Le logger est utilisé dans tous les modules pour afficher
    les messages d'information, d'avertissement et d'erreur
    dans le terminal avec un format cohérent.

    Format de sortie :
        2026-04-29 10:32:15 — INFO — Message ici

    Args:
        name: Nom du logger (par défaut 'gdelt_pipeline')

    Returns:
        logging.Logger: Logger configuré et prêt à l'emploi
    """
    logging.basicConfig(
        level=getattr(logging, LOG_LEVEL),
        format=LOG_FORMAT
    )
    return logging.getLogger(name)


# Instance globale du logger — importée par tous les modules du pipeline
logger = setup_logger()


# ─────────────────────────────────────────────────────────────────
# DÉCORATEUR TIMER
# ─────────────────────────────────────────────────────────────────

def timer(func):
    """
    Décorateur qui mesure et logue le temps d'exécution d'une fonction.

    Appliqué sur toutes les fonctions principales du pipeline pour
    identifier les étapes lentes et documenter les performances
    dans les logs. Utile pour le suivi et le débogage.

    Usage :
        @timer
        def ma_fonction():
            ...

    Produit dans les logs :
        INFO — Démarrage : ma_fonction
        INFO — Terminé   : ma_fonction — 3.42s

    Args:
        func: Fonction à décorer

    Returns:
        function: Fonction enveloppée avec mesure du temps
    """
    def wrapper(*args, **kwargs):
        start  = time.time()
        logger.info(f"Démarrage : {func.__name__}")
        result = func(*args, **kwargs)
        duration = round(time.time() - start, 2)
        logger.info(f"Terminé   : {func.__name__} — {duration}s")
        return result
    return wrapper


# ─────────────────────────────────────────────────────────────────
# CRÉATION DES DOSSIERS
# ─────────────────────────────────────────────────────────────────

def create_directories(*paths: str) -> None:
    """
    Crée les dossiers nécessaires au pipeline s'ils n'existent pas.

    Appelée au début de chaque extraction et chargement pour
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

def validate_dataframe(df, name: str = "dataframe") -> bool:
    """
    Vérifie qu'un DataFrame pandas est valide et non vide.

    Appelée entre chaque étape du pipeline (après extraction,
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
        if not validate_dataframe(df, "données brutes"):
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