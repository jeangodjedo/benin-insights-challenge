# tests/test_transform.py
"""
Unit tests for transform.py
Tests functions: clean_basic, convert_types, enrich_data, filter_data
"""

import pytest
import pandas as pd
import sys
from pathlib import Path

# Add pipeline to path
sys.path.insert(0, str(Path(__file__).parent.parent / "pipeline"))

from transform import clean_basic, convert_types, enrich_data, filter_data, EVENT_ROOT_LABELS


class TestCleanBasic:
    """Tests for clean_basic function."""

    def test_clean_removes_duplicates(self):
        """Should remove duplicate rows."""
        data = {
            "GLOBALEVENTID": [1, 1, 2],
            "SQLDATE": ["2025-01-01", "2025-01-01", "2025-01-02"],
            "SOURCEURL": ["http://a.com", "http://a.com", "http://b.com"],
        }
        df = pd.DataFrame(data)
        result = clean_basic(df)
        assert len(result) == 2  # One duplicate removed

    def test_clean_removes_missing_critical(self):
        """Should remove rows with missing critical columns."""
        data = {
            "GLOBALEVENTID": [1, 2, 3],
            "SQLDATE": ["2025-01-01", None, "2025-01-03"],
            "SOURCEURL": ["http://a.com", "http://b.com", "http://c.com"],
        }
        df = pd.DataFrame(data)
        result = clean_basic(df)
        # Should have only rows with both columns
        assert result["SQLDATE"].notna().all()
        assert result["SOURCEURL"].notna().all()

    def test_clean_keeps_valid_rows(self):
        """Should keep valid rows."""
        data = {
            "GLOBALEVENTID": [1, 2],
            "SQLDATE": ["2025-01-01", "2025-01-02"],
            "SOURCEURL": ["http://a.com", "http://b.com"],
        }
        df = pd.DataFrame(data)
        result = clean_basic(df)
        assert len(result) == 2

    def test_clean_returns_dataframe(self):
        """Should return a pandas DataFrame."""
        data = {
            "GLOBALEVENTID": [1],
            "SQLDATE": ["2025-01-01"],
            "SOURCEURL": ["http://a.com"],
        }
        df = pd.DataFrame(data)
        result = clean_basic(df)
        assert isinstance(result, pd.DataFrame)


class TestConvertTypes:
    """Tests for convert_types function."""

    def test_convert_sql_date_to_datetime(self):
        """Should convert SQLDATE to datetime."""
        data = {
            "SQLDATE": ["2025-01-01", "2025-01-02"],
            "MonthYear": [202501, 202502],
            "GoldsteinScale": [5.0, 10.0],
            "AvgTone": [2.5, -1.0],
            "Latitude": [6.5, 6.6],
            "Longitude": [2.0, 2.1],
        }
        df = pd.DataFrame(data)
        result = convert_types(df)
        assert pd.api.types.is_datetime64_any_dtype(result["SQLDATE"])

    def test_convert_monthyear_to_int(self):
        """Should convert MonthYear to integer."""
        data = {
            "SQLDATE": ["2025-01-01"],
            "MonthYear": [202501],
            "GoldsteinScale": [5.0],
            "AvgTone": [2.5],
            "Latitude": [6.5],
            "Longitude": [2.0],
        }
        df = pd.DataFrame(data)
        result = convert_types(df)
        assert result["MonthYear"].dtype in [int, "int64"]

    def test_convert_numeric_columns(self):
        """Should convert GoldsteinScale, AvgTone, coordinates to float."""
        data = {
            "SQLDATE": ["2025-01-01"],
            "MonthYear": [202501],
            "GoldsteinScale": ["5", "10"],
            "AvgTone": ["2.5", "-1.0"],
            "Latitude": ["6.5", "6.6"],
            "Longitude": ["2.0", "2.1"],
        }
        df = pd.DataFrame(data)
        result = convert_types(df)
        assert pd.api.types.is_float_dtype(result["GoldsteinScale"])
        assert pd.api.types.is_float_dtype(result["AvgTone"])
        assert pd.api.types.is_float_dtype(result["Latitude"])
        assert pd.api.types.is_float_dtype(result["Longitude"])

    def test_convert_returns_dataframe(self):
        """Should return a pandas DataFrame."""
        data = {
            "SQLDATE": ["2025-01-01"],
            "MonthYear": [202501],
            "GoldsteinScale": [5.0],
            "AvgTone": [2.5],
            "Latitude": [6.5],
            "Longitude": [2.0],
        }
        df = pd.DataFrame(data)
        result = convert_types(df)
        assert isinstance(result, pd.DataFrame)


class TestEnrichData:
    """Tests for enrich_data function (Q1-Q5)."""

    def test_enrich_adds_event_root_label(self):
        """Should add event_root_label column."""
        data = {
            "SQLDATE": pd.to_datetime(["2025-01-01"]),
            "MonthYear": [202501],
            "EventRootCode": ["01", "02"],
            "GoldsteinScale": [5.0],
            "AvgTone": [2.5],
            "Latitude": [6.5],
            "Longitude": [2.0],
            "Actor1CountryCode": ["BEN"],
            "Actor2CountryCode": ["FRA"],
            "ActionCountryCode": ["BEN"],
            "NumSources": [5],
            "IsRootEvent": [1],
            "QuadClass": [1],
            "DATEADDED": [20250101000000],
            "SOURCEURL": ["http://test.com"],
        }
        df = pd.DataFrame(data)
        result = enrich_data(df)
        assert "event_root_label" in result.columns

    def test_enrich_adds_tone_category(self):
        """Should add tone_category column."""
        data = {
            "SQLDATE": pd.to_datetime(["2025-01-01"]),
            "MonthYear": [202501],
            "EventRootCode": ["01"],
            "GoldsteinScale": [5.0],
            "AvgTone": [5.0],  # Positive tone
            "Latitude": [6.5],
            "Longitude": [2.0],
            "Actor1CountryCode": ["BEN"],
            "Actor2CountryCode": ["FRA"],
            "ActionCountryCode": ["BEN"],
            "NumSources": [5],
            "IsRootEvent": [1],
            "QuadClass": [1],
            "DATEADDED": [20250101000000],
            "SOURCEURL": ["http://test.com"],
        }
        df = pd.DataFrame(data)
        result = enrich_data(df)
        assert "tone_category" in result.columns

    def test_enrich_adds_stability_category(self):
        """Should add stability_category column."""
        data = {
            "SQLDATE": pd.to_datetime(["2025-01-01"]),
            "MonthYear": [202501],
            "EventRootCode": ["01"],
            "GoldsteinScale": [5.0],
            "AvgTone": [2.5],
            "Latitude": [6.5],
            "Longitude": [2.0],
            "Actor1CountryCode": ["BEN"],
            "Actor2CountryCode": ["FRA"],
            "ActionCountryCode": ["BEN"],
            "NumSources": [5],
            "IsRootEvent": [1],
            "QuadClass": [1],
            "DATEADDED": [20250101000000],
            "SOURCEURL": ["http://test.com"],
        }
        df = pd.DataFrame(data)
        result = enrich_data(df)
        assert "stability_category" in result.columns

    def test_enrich_adds_propagation_delay(self):
        """Should add propagation_delay_days column."""
        data = {
            "SQLDATE": pd.to_datetime(["2025-01-01"]),
            "MonthYear": [202501],
            "EventRootCode": ["01"],
            "GoldsteinScale": [5.0],
            "AvgTone": [2.5],
            "Latitude": [6.5],
            "Longitude": [2.0],
            "Actor1CountryCode": ["BEN"],
            "Actor2CountryCode": ["FRA"],
            "ActionCountryCode": ["BEN"],
            "NumSources": [5],
            "IsRootEvent": [1],
            "QuadClass": [1],
            "DATEADDED": [20250105000000],  # 4 days later
            "SOURCEURL": ["http://test.com"],
        }
        df = pd.DataFrame(data)
        result = enrich_data(df)
        assert "propagation_delay_days" in result.columns

    def test_enrich_adds_benin_role(self):
        """Should add benin_role column."""
        data = {
            "SQLDATE": pd.to_datetime(["2025-01-01"]),
            "MonthYear": [202501],
            "EventRootCode": ["01"],
            "GoldsteinScale": [5.0],
            "AvgTone": [2.5],
            "Latitude": [6.5],
            "Longitude": [2.0],
            "Actor1CountryCode": ["BEN"],
            "Actor2CountryCode": ["FRA"],
            "ActionCountryCode": ["BEN"],
            "NumSources": [5],
            "IsRootEvent": [1],
            "QuadClass": [1],
            "DATEADDED": [20250101000000],
            "SOURCEURL": ["http://test.com"],
        }
        df = pd.DataFrame(data)
        result = enrich_data(df)
        assert "benin_role" in result.columns

    def test_enrich_returns_dataframe(self):
        """Should return a pandas DataFrame."""
        data = {
            "SQLDATE": pd.to_datetime(["2025-01-01"]),
            "MonthYear": [202501],
            "EventRootCode": ["01"],
            "GoldsteinScale": [5.0],
            "AvgTone": [2.5],
            "Latitude": [6.5],
            "Longitude": [2.0],
            "Actor1CountryCode": ["BEN"],
            "Actor2CountryCode": ["FRA"],
            "ActionCountryCode": ["BEN"],
            "NumSources": [5],
            "IsRootEvent": [1],
            "QuadClass": [1],
            "DATEADDED": [20250101000000],
            "SOURCEURL": ["http://test.com"],
        }
        df = pd.DataFrame(data)
        result = enrich_data(df)
        assert isinstance(result, pd.DataFrame)


class TestFilterData:
    """Tests for filter_data function."""

    def test_filter_removes_invalid_dates(self):
        """Should filter out rows with invalid dates."""
        data = {
            "SQLDATE": pd.to_datetime(["2025-01-01", "2024-12-31", "2025-06-15"]),
            "Latitude": [6.5, 6.5, 6.5],
            "Longitude": [2.0, 2.0, 2.0],
        }
        df = pd.DataFrame(data)
        result = filter_data(df)
        assert result["SQLDATE"].min().year >= 2025

    def test_filter_removes_invalid_coords(self):
        """Should filter out rows with invalid coordinates."""
        data = {
            "SQLDATE": pd.to_datetime(["2025-01-01", "2025-01-02"]),
            "Latitude": [6.5, 0.0],  # Invalid latitude
            "Longitude": [2.0, 2.0],
        }
        df = pd.DataFrame(data)
        result = filter_data(df)
        assert result["Latitude"].min() > 0

    def test_filter_returns_dataframe(self):
        """Should return a pandas DataFrame."""
        data = {
            "SQLDATE": pd.to_datetime(["2025-01-01"]),
            "Latitude": [6.5],
            "Longitude": [2.0],
        }
        df = pd.DataFrame(data)
        result = filter_data(df)
        assert isinstance(result, pd.DataFrame)


class TestEventRootLabels:
    """Tests event root code labels."""

    def test_event_root_labels_not_empty(self):
        """EVENT_ROOT_LABELS should not be empty."""
        assert len(EVENT_ROOT_LABELS) > 0

    def test_event_root_labels_01(self):
        """Should have label for code 01."""
        assert "01" in EVENT_ROOT_LABELS

    def test_event_root_labels_str_keys(self):
        """EVENT_ROOT_LABELS should have string keys."""
        for key in EVENT_ROOT_LABELS.keys():
            assert isinstance(key, str)