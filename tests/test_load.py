"""
Unit tests for the load module.

Tests generate_quality_report() using an in-memory DataFrame.
File I/O functions (save_to_csv, save_to_parquet, save_to_json)
are tested with a temporary directory to avoid side effects.

Author  : Team 7 - Benin Insights Challenge 2026
Date    : May 2026
Version : 1.0
"""

import json
import pytest
import pandas as pd
import tempfile
from pathlib import Path

from pipeline.load import (
    save_to_csv,
    save_to_parquet,
    save_to_json,
    generate_quality_report,
)
from pipeline.config import PIPELINE_VERSION


# ─────────────────────────────────────────────────────────────────
# FIXTURE
# ─────────────────────────────────────────────────────────────────

@pytest.fixture
def clean_df():
    """
    Minimal clean DataFrame mimicking transform.py output.
    Includes all enriched columns expected by generate_quality_report.
    """
    return pd.DataFrame({
        "SQLDATE"                : pd.to_datetime(["2025-01-15", "2025-02-10", "2025-06-20"]),
        "DATEADDED"              : pd.to_datetime(["2025-01-15", "2025-02-12", "2025-06-20"]),
        "Actor1CountryCode"      : ["BEN", "FRA", None],
        "Actor2CountryCode"      : ["FRA", "BEN", "BEN"],
        "EventRootCode"          : ["05", "03", "14"],
        "AvgTone"                : [2.5, -1.0, -8.0],
        "GoldsteinScale"         : [3.4, 0.5, -7.0],
        "NumArticles"            : [10, 5, 20],
        "NumMentions"            : [10, 5, 20],
        "NumSources"             : [3, 2, 8],
        "ActionGeo_Lat"          : [6.37, 48.85, 6.49],
        "ActionGeo_Long"         : [2.42, 2.35, 2.61],
        "SOURCEURL"              : [
            "https://www.rfi.fr/benin/article1",
            "https://www.lemonde.fr/article2",
            "https://allafrica.com/article3",
        ],
        "event_date"             : ["2025-01-15", "2025-02-10", "2025-06-20"],
        "event_month"            : [1, 2, 6],
        "event_quarter"          : ["2025Q1", "2025Q1", "2025Q2"],
        "event_root_label"       : ["Engagement / Soutien", "Expression d'intention", "Protestation"],
        "tone_category"          : ["Positif", "Neutre", "Négatif"],
        "stability_category"     : ["Stabilisant", "Neutre", "Déstabilisant"],
        "propagation_delay_days" : [0, 2, 0],
        "source_domain"          : ["rfi.fr", "lemonde.fr", "allafrica.com"],
        "is_crisis_period"       : [False, False, True],
        "benin_role"             : ["Acteur", "Spectateur", "Spectateur"],
        "actor1_type_label"      : ["Gouvernement", "Gouvernement", "Non identifié"],
        "actor2_type_label"      : ["Gouvernement", "Gouvernement", "Civil / Population"],
        "quad_class_label"       : ["Coopération matérielle", "Coopération verbale", "Conflit verbal"],
    })


@pytest.fixture
def tmp_dir():
    """Provide a temporary directory for file I/O tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


# ─────────────────────────────────────────────────────────────────
# TESTS — save_to_csv()
# ─────────────────────────────────────────────────────────────────

class TestSaveToCsv:
    """Tests for CSV save function."""

    def test_csv_file_is_created(self, clean_df, tmp_dir):
        """CSV file must be created at the specified path."""
        filepath = tmp_dir / "test.csv"
        save_to_csv(clean_df, filepath)
        assert filepath.exists()

    def test_csv_has_correct_row_count(self, clean_df, tmp_dir):
        """Saved CSV must have the same number of rows as the input DataFrame."""
        filepath = tmp_dir / "test.csv"
        save_to_csv(clean_df, filepath)
        result = pd.read_csv(filepath)
        assert len(result) == len(clean_df)

    def test_csv_has_correct_column_count(self, clean_df, tmp_dir):
        """Saved CSV must have the same columns as the input DataFrame."""
        filepath = tmp_dir / "test.csv"
        save_to_csv(clean_df, filepath)
        result = pd.read_csv(filepath)
        assert list(result.columns) == list(clean_df.columns)

    def test_csv_is_utf8_encoded(self, clean_df, tmp_dir):
        """CSV must be readable as UTF-8 (French characters preserved)."""
        filepath = tmp_dir / "test.csv"
        save_to_csv(clean_df, filepath)
        with open(filepath, encoding="utf-8") as f:
            content = f.read()
        assert "Engagement / Soutien" in content


# ─────────────────────────────────────────────────────────────────
# TESTS — save_to_parquet()
# ─────────────────────────────────────────────────────────────────

class TestSaveToParquet:
    """Tests for Parquet save function."""

    def test_parquet_file_is_created(self, clean_df, tmp_dir):
        """Parquet file must be created at the specified path."""
        filepath = tmp_dir / "test.parquet"
        save_to_parquet(clean_df, filepath)
        assert filepath.exists()

    def test_parquet_is_readable(self, clean_df, tmp_dir):
        """Saved Parquet file must be readable by pandas."""
        filepath = tmp_dir / "test.parquet"
        save_to_parquet(clean_df, filepath)
        result = pd.read_parquet(filepath)
        assert len(result) == len(clean_df)

    def test_parquet_preserves_datetime_type(self, clean_df, tmp_dir):
        """Parquet must preserve datetime column types."""
        filepath = tmp_dir / "test.parquet"
        save_to_parquet(clean_df, filepath)
        result = pd.read_parquet(filepath)
        assert pd.api.types.is_datetime64_any_dtype(result["SQLDATE"])


# ─────────────────────────────────────────────────────────────────
# TESTS — save_to_json()
# ─────────────────────────────────────────────────────────────────

class TestSaveToJson:
    """Tests for JSON save function."""

    def test_json_file_is_created(self, clean_df, tmp_dir):
        """JSON file must be created at the specified path."""
        filepath = tmp_dir / "test.json"
        save_to_json(clean_df, filepath)
        assert filepath.exists()

    def test_json_is_valid_and_parseable(self, clean_df, tmp_dir):
        """Saved JSON file must be valid and parseable."""
        filepath = tmp_dir / "test.json"
        save_to_json(clean_df, filepath)
        with open(filepath, encoding="utf-8") as f:
            data = json.load(f)
        assert isinstance(data, list)
        assert len(data) == len(clean_df)

    def test_json_preserves_french_characters(self, clean_df, tmp_dir):
        """JSON must preserve French characters (force_ascii=False)."""
        filepath = tmp_dir / "test.json"
        save_to_json(clean_df, filepath)
        with open(filepath, encoding="utf-8") as f:
            content = f.read()
        assert "Négatif" in content or "Positif" in content


# ─────────────────────────────────────────────────────────────────
# TESTS — generate_quality_report()
# ─────────────────────────────────────────────────────────────────

class TestGenerateQualityReport:
    """Tests for the quality report generation."""

    def test_report_contains_pipeline_version(self, clean_df, tmp_dir, monkeypatch):
        """Report must contain the correct pipeline version from config."""
        monkeypatch.setattr("pipeline.load.QUALITY_REPORT", tmp_dir / "report.json")
        report = generate_quality_report(clean_df)
        assert report["pipeline_version"] == PIPELINE_VERSION

    def test_report_volume_matches_dataframe(self, clean_df, tmp_dir, monkeypatch):
        """Report volume.total_rows must match the DataFrame row count."""
        monkeypatch.setattr("pipeline.load.QUALITY_REPORT", tmp_dir / "report.json")
        report = generate_quality_report(clean_df)
        assert report["volume"]["total_rows"] == len(clean_df)

    def test_report_contains_q1_metrics(self, clean_df, tmp_dir, monkeypatch):
        """Report must contain Q1 coverage peaks metrics."""
        monkeypatch.setattr("pipeline.load.QUALITY_REPORT", tmp_dir / "report.json")
        report = generate_quality_report(clean_df)
        assert "q1_coverage_peaks" in report
        assert "total_articles" in report["q1_coverage_peaks"]
        assert "top_5_event_types" in report["q1_coverage_peaks"]

    def test_report_contains_q2_metrics(self, clean_df, tmp_dir, monkeypatch):
        """Report must contain Q2 media tone metrics."""
        monkeypatch.setattr("pipeline.load.QUALITY_REPORT", tmp_dir / "report.json")
        report = generate_quality_report(clean_df)
        assert "q2_media_tone" in report
        assert "avg_tone" in report["q2_media_tone"]
        assert "distribution" in report["q2_media_tone"]

    def test_report_contains_q3_metrics(self, clean_df, tmp_dir, monkeypatch):
        """Report must contain Q3 propagation delay metrics."""
        monkeypatch.setattr("pipeline.load.QUALITY_REPORT", tmp_dir / "report.json")
        report = generate_quality_report(clean_df)
        assert "q3_propagation" in report
        assert "avg_delay_days" in report["q3_propagation"]

    def test_report_contains_q4_metrics(self, clean_df, tmp_dir, monkeypatch):
        """Report must contain Q4 source domain metrics."""
        monkeypatch.setattr("pipeline.load.QUALITY_REPORT", tmp_dir / "report.json")
        report = generate_quality_report(clean_df)
        assert "q4_sources" in report
        assert "unique_domains" in report["q4_sources"]
        assert "top_10_domains" in report["q4_sources"]

    def test_report_contains_q5_metrics(self, clean_df, tmp_dir, monkeypatch):
        """Report must contain Q5 Benin role metrics."""
        monkeypatch.setattr("pipeline.load.QUALITY_REPORT", tmp_dir / "report.json")
        report = generate_quality_report(clean_df)
        assert "q5_benin_role" in report
        assert "distribution" in report["q5_benin_role"]

    def test_report_file_is_saved_to_disk(self, clean_df, tmp_dir, monkeypatch):
        """Quality report JSON file must be written to disk."""
        report_path = tmp_dir / "quality_report.json"
        monkeypatch.setattr("pipeline.load.QUALITY_REPORT", report_path)
        generate_quality_report(clean_df)
        assert report_path.exists()

    def test_report_json_is_valid(self, clean_df, tmp_dir, monkeypatch):
        """Quality report file must be valid JSON."""
        report_path = tmp_dir / "quality_report.json"
        monkeypatch.setattr("pipeline.load.QUALITY_REPORT", report_path)
        generate_quality_report(clean_df)
        with open(report_path, encoding="utf-8") as f:
            data = json.load(f)
        assert isinstance(data, dict)

    def test_report_period_dates_are_correct(self, clean_df, tmp_dir, monkeypatch):
        """Report period dates must match the DataFrame's actual date range."""
        monkeypatch.setattr("pipeline.load.QUALITY_REPORT", tmp_dir / "report.json")
        report = generate_quality_report(clean_df)
        assert report["period_covered"]["date_min"] == "2025-01-15"
        assert report["period_covered"]["date_max"] == "2025-06-20"

    def test_report_q5_distribution_sums_to_total_rows(self, clean_df, tmp_dir, monkeypatch):
        """Q5 role distribution counts must sum to total rows."""
        monkeypatch.setattr("pipeline.load.QUALITY_REPORT", tmp_dir / "report.json")
        report = generate_quality_report(clean_df)
        total = sum(report["q5_benin_role"]["distribution"].values())
        assert total == len(clean_df)