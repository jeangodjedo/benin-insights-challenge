# tests/test_load.py
"""
Unit tests for load.py
Tests functions: save_to_csv, save_to_parquet, save_to_json, generate_quality_report
"""

import pytest
import pandas as pd
import json
import sys
import os
import tempfile
from pathlib import Path

# Add pipeline to path
sys.path.insert(0, str(Path(__file__).parent.parent / "pipeline"))

from load import save_to_csv, save_to_parquet, save_to_json, generate_quality_report


class TestSaveToCSV:
    """Tests for save_to_csv function."""

    def test_save_to_csv_creates_file(self):
        """Should create a CSV file."""
        data = {
            "col1": [1, 2],
            "col2": ["a", "b"],
        }
        df = pd.DataFrame(data)
        
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            filepath = f.name
        
        try:
            save_to_csv(df, filepath)
            assert os.path.exists(filepath)
        finally:
            if os.path.exists(filepath):
                os.remove(filepath)

    def test_save_to_csv_has_data(self):
        """CSV file should contain the data."""
        data = {
            "col1": [1, 2],
            "col2": ["a", "b"],
        }
        df = pd.DataFrame(data)
        
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            filepath = f.name
        
        try:
            save_to_csv(df, filepath)
            result_df = pd.read_csv(filepath)
            assert len(result_df) == 2
        finally:
            if os.path.exists(filepath):
                os.remove(filepath)


class TestSaveToParquet:
    """Tests for save_to_parquet function."""

    def test_save_to_parquet_creates_file(self):
        """Should create a Parquet file."""
        data = {
            "col1": [1, 2],
            "col2": ["a", "b"],
        }
        df = pd.DataFrame(data)
        
        with tempfile.NamedTemporaryFile(suffix=".parquet", delete=False) as f:
            filepath = f.name
        
        try:
            save_to_parquet(df, filepath)
            assert os.path.exists(filepath)
        finally:
            if os.path.exists(filepath):
                os.remove(filepath)


class TestSaveToJSON:
    """Tests for save_to_json function."""

    def test_save_to_json_creates_file(self):
        """Should create a JSON file."""
        data = {
            "col1": [1, 2],
            "col2": ["a", "b"],
        }
        df = pd.DataFrame(data)
        
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            filepath = f.name
        
        try:
            save_to_json(df, filepath)
            assert os.path.exists(filepath)
        finally:
            if os.path.exists(filepath):
                os.remove(filepath)

    def test_save_to_json_has_valid_json(self):
        """JSON file should be valid."""
        data = {
            "col1": [1, 2],
            "col2": ["a", "b"],
        }
        df = pd.DataFrame(data)
        
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            filepath = f.name
        
        try:
            save_to_json(df, filepath)
            with open(filepath, "r") as f:
                content = json.load(f)
            assert isinstance(content, list)
        finally:
            if os.path.exists(filepath):
                os.remove(filepath)


class TestGenerateQualityReport:
    """Tests for generate_quality_report function."""

    def test_report_has_required_keys(self):
        """Report should have required keys."""
        data = {
            "SQLDATE": pd.to_datetime(["2025-01-01", "2025-01-02"]),
            "MonthYear": [202501, 202502],
            "EventRootCode": ["01", "02"],
            "AvgTone": [2.5, -1.0],
            "Latitude": [6.5, 6.6],
            "Longitude": [2.0, 2.1],
            "Actor1CountryCode": ["BEN", "BEN"],
            "SOURCEURL": ["http://a.com", "http://b.com"],
            "NumSources": [5, 10],
        }
        df = pd.DataFrame(data)
        report = generate_quality_report(df)
        
        assert "generated_at" in report
        assert "total_rows" in report
        assert "date_range" in report

    def test_report_has_analytical_columns(self):
        """Report should have analytical columns."""
        data = {
            "SQLDATE": pd.to_datetime(["2025-01-01"]),
            "MonthYear": [202501],
            "EventRootCode": ["01"],
            "AvgTone": [2.5],
            "Latitude": [6.5],
            "Longitude": [2.0],
            "Actor1CountryCode": ["BEN"],
            "SOURCEURL": ["http://a.com"],
            "NumSources": [5],
        }
        df = pd.DataFrame(data)
        report = generate_quality_report(df)
        
        # Should have Q1-Q5 sections
        assert "q1_event_diversity" in report
        assert "q2_tone" in report
        assert "q3_propagation" in report
        assert "q4_sources" in report
        assert "q5_role" in report

    def test_report_row_count(self):
        """Report should have correct row count."""
        data = {
            "SQLDATE": pd.to_datetime(["2025-01-01", "2025-01-02", "2025-01-03"]),
            "MonthYear": [202501, 202501, 202502],
            "EventRootCode": ["01", "02", "01"],
            "AvgTone": [2.5, -1.0, 0.0],
            "Latitude": [6.5, 6.5, 6.6],
            "Longitude": [2.0, 2.0, 2.1],
            "Actor1CountryCode": ["BEN", "BEN", "FRA"],
            "SOURCEURL": ["http://a.com", "http://b.com", "http://c.com"],
            "NumSources": [5, 10, 3],
        }
        df = pd.DataFrame(data)
        report = generate_quality_report(df)
        
        assert report["total_rows"] == 3

    def test_report_returns_dict(self):
        """Report should return a dictionary."""
        data = {
            "SQLDATE": pd.to_datetime(["2025-01-01"]),
            "MonthYear": [202501],
            "EventRootCode": ["01"],
            "AvgTone": [2.5],
            "Latitude": [6.5],
            "Longitude": [2.0],
            "Actor1CountryCode": ["BEN"],
            "SOURCEURL": ["http://a.com"],
            "NumSources": [5],
        }
        df = pd.DataFrame(data)
        report = generate_quality_report(df)
        
        assert isinstance(report, dict)


class TestQualityReportContent:
    """Tests for quality report content."""

    def test_report_has_pipeline_version(self):
        """Report should include pipeline version."""
        data = {
            "SQLDATE": pd.to_datetime(["2025-01-01"]),
            "MonthYear": [202501],
            "EventRootCode": ["01"],
            "AvgTone": [2.5],
            "Latitude": [6.5],
            "Longitude": [2.0],
            "Actor1CountryCode": ["BEN"],
            "SOURCEURL": ["http://a.com"],
            "NumSources": [5],
        }
        df = pd.DataFrame(data)
        report = generate_quality_report(df)
        
        assert "pipeline_version" in report

    def test_report_q1_event_diversity_keys(self):
        """Q1 should have correct structure."""
        data = {
            "SQLDATE": pd.to_datetime(["2025-01-01"]),
            "MonthYear": [202501],
            "EventRootCode": ["01"],
            "AvgTone": [2.5],
            "Latitude": [6.5],
            "Longitude": [2.0],
            "Actor1CountryCode": ["BEN"],
            "SOURCEURL": ["http://a.com"],
            "NumSources": [5],
        }
        df = pd.DataFrame(data)
        report = generate_quality_report(df)
        
        assert "unique_events" in report["q1_event_diversity"]
        assert "event_types" in report["q1_event_diversity"]

    def test_report_q2_tone_keys(self):
        """Q2 should have correct structure."""
        data = {
            "SQLDATE": pd.to_datetime(["2025-01-01"]),
            "MonthYear": [202501],
            "EventRootCode": ["01"],
            "AvgTone": [2.5],
            "Latitude": [6.5],
            "Longitude": [2.0],
            "Actor1CountryCode": ["BEN"],
            "SOURCEURL": ["http://a.com"],
            "NumSources": [5],
        }
        df = pd.DataFrame(data)
        report = generate_quality_report(df)
        
        assert "mean" in report["q2_tone"]
        assert "median" in report["q2_tone"]
        assert "categories" in report["q2_tone"]