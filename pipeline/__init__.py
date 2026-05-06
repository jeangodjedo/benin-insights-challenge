# pipeline/__init__.py
"""
GDELT pipeline package.
Benin Insights Challenge 2026 — iSHEERO x DataCamp Donates

ETL pipeline: GDELT data -> Benin 2025 (Jan -> Dec)

BUG-02 FIX: All imports use relative syntax (from .module import ...)
instead of absolute imports (from module import ...).

Note on imports: extract.py depends on google-cloud-bigquery.
The try/except block allows the package to be partially imported
in environments where BigQuery is not available (e.g. CI pipelines,
minimal test environments). In production, all dependencies must
be installed via requirements.txt.

Usage:
    python -m pipeline.run_pipeline --mode sample
    python -m pipeline.run_pipeline --mode full

Author  : Team 7 - Benin Insights Challenge 2026
Date    : May 2026
Version : 1.2
"""

from .transform import run_transform
from .load      import run_load

try:
    # google-cloud-bigquery required — may not be available
    # in minimal test environments or CI without full dependencies
    from .extract import run_full_extraction, run_sample_extraction
except ImportError:
    run_full_extraction  = None  # type: ignore
    run_sample_extraction = None  # type: ignore

__version__ = "1.2"
__author__  = "Team 7 — Bénin Insights Challenge 2026"
__all__     = [
    "run_full_extraction",
    "run_sample_extraction",
    "run_transform",
    "run_load",
]