# tests/test_extract.py
"""
Unit tests for extract.py
Tests functions: build_query, build_sample_query
"""

import pytest
import sys
from pathlib import Path

# Add pipeline to path
sys.path.insert(0, str(Path(__file__).parent.parent / "pipeline"))

from extract import build_query, build_sample_query, COUNTRY_ACTOR_CODE


class TestBuildQuery:
    """Tests for build_query function."""

    def test_build_query_sample_has_limit(self):
        """Sample query should have LIMIT clause."""
        query = build_query(limit=5000)
        assert "LIMIT 5000" in query

    def test_build_query_full_has_no_limit(self):
        """Full query should not have LIMIT clause."""
        query = build_query(limit=None)
        assert "LIMIT" not in query

    def test_build_query_uses_actor_code_ben(self):
        """Query should use BEN (CAMEO code) for actor country."""
        query = build_query()
        # Actor code in query
        assert COUNTRY_ACTOR_CODE in query
        # Check for Actor1CountryCode with BEN
        assert "Actor1CountryCode = 'BEN'" in query

    def test_build_query_has_year_filter(self):
        """Query should filter by year between START_YEAR and END_YEAR."""
        query = build_query()
        assert "YEAR BETWEEN" in query

    def test_build_query_has_monthyear_filter(self):
        """Query should filter by MonthYear."""
        query = build_query()
        assert "MonthYear BETWEEN" in query

    def test_build_query_has_benin_filter(self):
        """Query should include Benin country filter."""
        query = build_query()
        # Should have Actor2CountryCode filter
        assert "Actor2CountryCode" in query

    def test_build_query_has_gdeltonfilter(self):
        """Should filter out GDELT minor events."""
        query = build_query()
        assert "NumSources >" in query

    def test_build_query_has_order_by(self):
        """Query should order by SQLDATE descending."""
        query = build_query()
        assert "ORDER BY SQLDATE DESC" in query


class TestBuildSampleQuery:
    """Tests for build_sample_query function."""

    def test_sample_query_has_limit(self):
        """Sample query should have LIMIT 5000."""
        query = build_sample_query()
        assert "LIMIT 5000" in query

    def test_sample_query_uses_benin_code(self):
        """Sample query should use BEN actor code."""
        query = build_sample_query()
        assert "Actor1CountryCode = 'BEN'" in query


class TestQueryStructure:
    """Tests query structure and required components."""

    def test_query_has_select(self):
        """Query should have SELECT clause."""
        query = build_query()
        assert "SELECT" in query.upper()

    def test_query_has_from(self):
        """Query should have FROM clause."""
        query = build_query()
        assert "FROM" in query.upper()

    def test_query_has_where(self):
        """Query should have WHERE clause."""
        query = build_query()
        assert "WHERE" in query.upper()

    def test_query_is_string(self):
        """Query should return a string."""
        query = build_query()
        assert isinstance(query, str)

    def test_query_not_empty(self):
        """Query should not be empty."""
        query = build_query()
        assert len(query) > 0