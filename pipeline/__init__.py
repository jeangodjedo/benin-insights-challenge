# pipeline/__init__.py
"""
Package pipeline — Bénin Insights Challenge 2026
iSHEERO × DataCamp Donates

Pipeline ETL : données GDELT → Bénin 2025 (Jan → Déc)

Usage :
    python pipeline/run_pipeline.py --mode sample
    python pipeline/run_pipeline.py --mode full

Auteur  : Équipe Bénin Insights Challenge 2026
Version : 1.0
"""

from .extract   import run_full_extraction, run_sample_extraction
from .transform import run_transform
from .load      import run_load

__version__ = "1.0"
__author__  = "Équipe 7 Bénin Insights Challenge 2026"
__all__     = ["run_full_extraction", "run_sample_extraction", "run_transform", "run_load"]