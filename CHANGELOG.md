# Changelog — Bénin Insights Challenge 2026

All notable changes to this project are documented here.

## [1.3] — 2026-05-02 — da/eda-dashboard

### Added
- `GLOBALEVENTID` in `COLUMNS` — exact event deduplication
- `ActionGeo_ADM1Code` in `COLUMNS` — intra-Benin department breakdown
- `ActionGeo_Type` in `COLUMNS` — geographic precision level
- `Actor1Code`, `Actor2Code` in `COLUMNS` — compound actor codes (Q5 precision)
- `DEPT_LABELS` and `GEO_TYPE_LABELS` constants in `config.py`
- `event_department` derived column — French department name from ADM1Code
- `action_geo_precision` derived column — geographic precision label
- `clean_basic()`: GLOBALEVENTID-based deduplication
- `notebooks/eda_benin_gdelt_2025.ipynb` — full EDA with 5+ visualizations and ML model
- `dashboard/app.py` — complete Streamlit dashboard (Q1→Q5, filters, KPIs)
- `.idea/` removed from git tracking

### Fixed
- `DATEADDED`: now preserves full 14-character YYYYMMDDHHMMSS timestamp (was truncated to 8)
- `PROCESSED_DIR`: renamed from `data/clean/` to `data/processed/` (aligned with README)
- `.idea/` added to `.gitignore` and removed from index

### Changed
- `PIPELINE_VERSION` bumped to `1.3`

---

## [1.2] — 2026-05-01 — de/pipeline-gdelt (review corrections)

### Fixed
- BUG-01: `Actor1CountryCode` / `Actor2CountryCode` SQL filter: `BN` → `BEN` (CAMEO code)
- BUG-02: All imports converted to relative imports (`from .config import ...`)
- BUG-03: Removed dead code in `enrich_data()` (double `event_root_label` calculation)
- MAJ-01: `GCP_PROJECT_ID` loaded from `.env` via `python-dotenv` (no longer hardcoded)
- MAJ-02: Added `functools.wraps` to `timer` decorator
- MAJ-03: Logger uses named logger with guard block and `propagate=False`
- MAJ-04: All paths use `pathlib.Path`
- MAJ-05: Each function creates only its own required directories
- MAJ-06: `benin_role` vectorized with pandas operations
- MAJ-07: `END_YEAR` used via `END_MONTHYEAR` in SQL
- MAJ-08: `try/except` added to all save functions in `load.py`
- MAJ-09: All inline comments translated to English
- MIN-01 to MIN-10: See code review document in repository

### Added
- 72 unit tests across `tests/test_extract.py`, `tests/test_transform.py`, `tests/test_load.py`
- `conftest.py` for pytest path configuration
- `.env.example` template
- `PIPELINE_VERSION` as single source of truth in `config.py`

---

## [1.0] — 2026-04-27 — Initial release
- ETL pipeline: extract → transform → load
- BigQuery extraction with Benin filter
- 5 analytical questions (Q1→Q5) implemented
