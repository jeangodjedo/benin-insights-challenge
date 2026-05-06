"""
Master orchestration script for the GDELT pipeline.

Single entry point — chains EXTRACT -> TRANSFORM -> LOAD.

Usage from the terminal (project root):
    python/python3 -m pipeline.run_pipeline --mode sample   # test 5k rows
    python/python3 -m pipeline.run_pipeline --mode full     # production, no limit

Prerequisites (once per team member):
    gcloud auth application-default login

MIN-10 FIX: @timer removed from run_pipeline() which calls sys.exit(1).
    sys.exit() raises SystemExit (inherits from BaseException, not Exception).
    The timer decorator does not capture SystemExit, so "Completed: run_pipeline"
    was never logged on error. Timing is now handled manually with start_time.

MIN-05 FIX: --mode full help text corrected to reflect no row limit.

MIN-09 FIX: ASCII table replaced by structured log lines to avoid
    misalignment when values exceed fixed column widths.

Author  : Team 7 — Bénin Insights Challenge 2026
Date    : May 2026
Version : 1.2
"""

import sys
import argparse
import traceback
from datetime import datetime
import pandas as pd


from .extract   import run_full_extraction, run_sample_extraction
from .transform import run_transform
from .load      import run_load
from .utils     import logger


# ─────────────────────────────────────────────────────────────────
# COMMAND LINE ARGUMENTS
# ─────────────────────────────────────────────────────────────────

def parse_arguments() -> argparse.Namespace:
    """
    Parse command line arguments.

    Returns:
        argparse.Namespace: Parsed arguments
    """
    parser = argparse.ArgumentParser(
        description="GDELT Pipeline - Benin Insights Challenge 2026",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m pipeline.run_pipeline --mode sample   # quick test
  python -m pipeline.run_pipeline --mode full     # production

Authentication prerequisite (once per team member):
  gcloud auth application-default login

Analytical questions covered:
  Q1 - When does the world talk about Benin?
  Q2 - Is the media tone positive, neutral or negative?
  Q3 - How many days to reach the coverage peak?
  Q4 - Are crisis sources different from normal sources?
  Q5 - Is Benin an actor or a bystander?
        """
    )
    parser.add_argument(
        "--mode",
        type=str,
        choices=["full", "sample"],
        default="sample",
        # MIN-05 FIX: Corrected help text — full mode has no row limit
        help="'sample' (5,000 rows, for testing) or 'full' (no limit, all available data)"
    )
    return parser.parse_args()


# ─────────────────────────────────────────────────────────────────
# PIPELINE SUMMARY
# ─────────────────────────────────────────────────────────────────

def print_summary(df: pd.DataFrame, duration: float, mode: str) -> None:
    """
    Log a structured pipeline summary after successful execution.

    MIN-09 FIX: Replaced fixed-width ASCII table with structured log lines.
    Fixed-width formatting breaks when values exceed allocated widths,
    producing misaligned output in logs. Structured lines are robust
    regardless of value length.

    Args:
        df      : Final output DataFrame
        duration: Total execution time in seconds
        mode    : Execution mode ('sample' or 'full')
    """
    logger.info("=" * 55)
    logger.info("PIPELINE SUMMARY - Benin Insights Challenge 2026")
    logger.info("=" * 55)
    logger.info(f"  Mode      : {mode}")
    logger.info(f"  Duration  : {duration}s")
    logger.info(f"  Events    : {len(df):,}")
    logger.info(f"  Columns   : {len(df.columns)}")

    if "SQLDATE" in df.columns:
        date_min = str(df["SQLDATE"].min())[:10]
        date_max = str(df["SQLDATE"].max())[:10]
        logger.info(f"  Period    : {date_min} -> {date_max}")

    if "tone_category" in df.columns:
        logger.info("  --- Q2: Media Tone ---")
        for tone, count in df["tone_category"].value_counts().items():
            pct = round(count / len(df) * 100, 1)
            logger.info(f"    {tone}: {count:,} ({pct}%)")

    if "benin_role" in df.columns:
        logger.info("  --- Q5: Benin Role ---")
        for role, count in df["benin_role"].value_counts().items():
            pct = round(count / len(df) * 100, 1)
            logger.info(f"    {role}: {count:,} ({pct}%)")

    logger.info("  --- Output files (data/clean/) ---")
    logger.info("    benin_gdelt_clean.csv")
    logger.info("    benin_gdelt_clean.parquet")
    logger.info("    benin_gdelt_clean.json")
    logger.info("    quality_report.json")
    logger.info("=" * 55)


# ─────────────────────────────────────────────────────────────────
# MAIN PIPELINE
# ─────────────────────────────────────────────────────────────────

def run_pipeline(mode: str = "sample") -> None:
    """
    Orchestrate EXTRACT -> TRANSFORM -> LOAD.

    MIN-10 FIX: @timer removed from this function because sys.exit(1)
    raises SystemExit (BaseException subclass, not Exception).
    The timer decorator's wrapper only calls result = func(*args, **kwargs)
    and never reaches the "Completed" log line when SystemExit is raised.
    Timing is now handled manually with start_time / duration.

    On error, the pipeline stops cleanly with a detailed error message.

    Args:
        mode: 'sample' (5,000 rows) or 'full' (all data, no limit)
    """
    start_time = datetime.now()

    logger.info("=" * 55)
    logger.info("GDELT PIPELINE - BENIN INSIGHTS CHALLENGE 2026")
    logger.info("=" * 55)
    logger.info(f"  Start : {str(start_time)[:19]}")
    logger.info(f"  Mode  : {mode}")
    logger.info("=" * 55)

    try:
        # Step 1: EXTRACT
        logger.info("")
        logger.info(">>> STEP 1/3 - BIGQUERY EXTRACTION")
        df_raw = run_sample_extraction() if mode == "sample" else run_full_extraction()

        # Step 2: TRANSFORM
        logger.info("")
        logger.info(">>> STEP 2/3 - TRANSFORMATION AND ENRICHMENT")
        df_clean = run_transform(df_raw)

        # Step 3: LOAD
        logger.info("")
        logger.info(">>> STEP 3/3 - FILE SAVING")
        run_load(df_clean)

        # Summary
        duration = round((datetime.now() - start_time).total_seconds(), 1)
        print_summary(df_clean, duration, mode)

    except Exception as e:
        logger.error(f"[ERROR] Pipeline failed: {e}")
        logger.error(traceback.format_exc())
        sys.exit(1)


# ─────────────────────────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import pandas as pd  # noqa: F401 — needed for print_summary type hint
    args = parse_arguments()
    run_pipeline(mode=args.mode)