"""
Script maître d'orchestration du pipeline GDELT.

Point d'entrée unique — enchaîne EXTRACT → TRANSFORM → LOAD.

Usage depuis le terminal (racine du projet) :
    python pipeline/run_pipeline.py --mode sample   # test 5k lignes
    python pipeline/run_pipeline.py --mode full     # production 100k

Pré-requis (une seule fois par membre de l'équipe) :
    gcloud auth application-default login

Auteur  : Équipe Bénn Insights Challenge 2026
Date    : Avril 2026
Version : 1.0
"""

import sys
import os
import argparse
import traceback
from datetime import datetime

# Add pipeline/ to sys.path to enable absolute imports when running from project root
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from extract   import run_full_extraction, run_sample_extraction
from transform import run_transform
from load      import run_load
from utils     import logger, timer

def parse_arguments() -> argparse.Namespace:
    """
    Parse les arguments de la ligne de commande.

    Returns:
        argparse.Namespace: Arguments parsés
    """
    parser = argparse.ArgumentParser(
        description="Pipeline GDELT — Bénin Insights Challenge 2026",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemples :
  python pipeline/run_pipeline.py --mode sample   # test rapide
  python pipeline/run_pipeline.py --mode full     # production

Pré-requis authentification (une seule fois) :
  gcloud auth application-default login

Questions couvertes :
  Q1 — Quand le monde parle-t-il du Bénin ?
  Q2 — Le ton médiatique est-il positif, neutre ou négatif ?
  Q3 — Combien de jours pour atteindre le pic de couverture ?
  Q4 — Sources en crise vs sources en période normale ?
  Q5 — Le Bénin est-il acteur ou spectateur ?
        """
    )
    parser.add_argument(
        "--mode",
        type=str,
        choices=["full", "sample"],
        default="sample",
        help="'sample' (5,000 rows for testing) or 'full' (no limit, all available data)"
    )
    return parser.parse_args()


def print_summary(df, start_time: datetime, mode: str) -> None:
    """
    Affiche un résumé du pipeline après exécution.

    Args:
        df        : DataFrame final
        start_time: Heure de démarrage
        mode      : Mode d'exécution
    """
    duration = round((datetime.now() - start_time).total_seconds(), 1)

    logger.info("")
    logger.info("╔══════════════════════════════════════════════════╗")
    logger.info("║      RÉSUMÉ — PIPELINE BÉNIN INSIGHTS 2026      ║")
    logger.info("╠══════════════════════════════════════════════════╣")
    logger.info(f"║  Mode       : {mode:<35}║")
    logger.info(f"║  Durée      : {str(duration) + 's':<35}║")
    logger.info(f"║  Événements : {len(df):,}".ljust(50) + "║")
    logger.info(f"║  Colonnes   : {len(df.columns):<35}║")

    if "SQLDATE" in df.columns:
        periode = f"{str(df['SQLDATE'].min())[:10]} → {str(df['SQLDATE'].max())[:10]}"
        logger.info(f"║  Période    : {periode:<35}║")

    if "tone_category" in df.columns:
        logger.info("╠══════════════════════════════════════════════════╣")
        logger.info("║  Q2 — TON MÉDIATIQUE                             ║")
        for tone, count in df["tone_category"].value_counts().items():
            pct  = round(count / len(df) * 100, 1)
            line = f"{tone:<15} {count:>7,}  ({pct}%)"
            logger.info(f"║  {line:<48}║")

    if "benin_role" in df.columns:
        logger.info("╠══════════════════════════════════════════════════╣")
        logger.info("║  Q5 — RÔLE DU BÉNIN                             ║")
        for role, count in df["benin_role"].value_counts().items():
            pct  = round(count / len(df) * 100, 1)
            line = f"{role:<15} {count:>7,}  ({pct}%)"
            logger.info(f"║  {line:<48}║")

    logger.info("╠══════════════════════════════════════════════════╣")
    logger.info("║  FICHIERS PRODUITS                               ║")
    logger.info("║  data/processed/benin_gdelt_clean.csv            ║")
    logger.info("║  data/processed/benin_gdelt_clean.parquet        ║")
    logger.info("║  data/processed/benin_gdelt_clean.json           ║")
    logger.info("║  data/processed/quality_report.json              ║")
    logger.info("╚══════════════════════════════════════════════════╝")


def run_pipeline(mode: str = "sample") -> None:
    """
    Orchestre EXTRACT → TRANSFORM → LOAD.

    En cas d'erreur, le pipeline s'arrête proprement
    avec un message d'erreur détaillé.

    Args:
        mode: 'sample' ou 'full'
    """
    start_time = datetime.now()

    logger.info("╔══════════════════════════════════════════════════╗")
    logger.info("║    PIPELINE GDELT — BÉNIN INSIGHTS 2026         ║")
    logger.info(f"║  Démarrage : {str(start_time)[:19]:<36}║")
    logger.info(f"║  Mode      : {mode:<36}║")
    logger.info("╚══════════════════════════════════════════════════╝")

    try:
        logger.info("")
        logger.info(">>> ÉTAPE 1/3 — EXTRACTION BIGQUERY")
        df_raw = run_sample_extraction() if mode == "sample" else run_full_extraction()

        logger.info("")
        logger.info(">>> ÉTAPE 2/3 — TRANSFORMATION ET ENRICHISSEMENT")
        df_clean = run_transform(df_raw)

        logger.info("")
        logger.info(">>> ÉTAPE 3/3 — SAUVEGARDE DES FICHIERS")
        run_load(df_clean)

        print_summary(df_clean, start_time, mode)

    except Exception as e:
        logger.error(f"[ERROR] {e}")
        logger.error(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    args = parse_arguments()
    run_pipeline(mode=args.mode)