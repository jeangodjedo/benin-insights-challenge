"""
Unit tests for the extract module.

Tests build_query() only — no BigQuery connection required.
BigQuery integration tests would require a live connection
and are out of scope for unit testing.

Author  : Team 7 - Benin Insights Challenge 2026
Date    : May 2026
Version : 1.0
"""

from pipeline.extract import build_query


class TestBuildQuery:
    """Tests for SQL query generation logic."""

    def test_sample_mode_has_limit_clause(self):
        """Sample mode must include a LIMIT clause."""
        query = build_query(limit=5000)
        assert "LIMIT 5000" in query

    def test_full_mode_has_no_limit_clause(self):
        """Full mode must NOT include any LIMIT clause."""
        query = build_query(limit=None)
        assert "LIMIT" not in query

    def test_query_uses_cameo_actor_code_ben_for_actor1(self):
        """Actor1 filter must use CAMEO code 'BEN', not geographic code 'BN'."""
        query = build_query()
        assert "Actor1CountryCode = 'BEN'" in query

    def test_query_uses_cameo_actor_code_ben_for_actor2(self):
        """Actor2 filter must use CAMEO code 'BEN', not geographic code 'BN'."""
        query = build_query()
        assert "Actor2CountryCode = 'BEN'" in query

    def test_query_does_not_use_bn_for_actors(self):
        """Actor filters must NOT use geographic code 'BN' (BUG-01 regression)."""
        query = build_query()
        assert "Actor1CountryCode = 'BN'" not in query
        assert "Actor2CountryCode = 'BN'" not in query

    def test_query_uses_geographic_code_bn_for_geo_filter(self):
        """Geographic filter must use GDELT code 'BN' for ActionGeo_CountryCode."""
        query = build_query()
        assert "ActionGeo_CountryCode = 'BN'" in query

    def test_year_filter_appears_before_monthyear_filter(self):
        """YEAR filter must appear before MonthYear filter for quota optimization."""
        query = build_query()
        year_pos      = query.find("YEAR = 2025")
        monthyear_pos = query.find("MonthYear BETWEEN")
        assert year_pos < monthyear_pos

    def test_monthyear_filter_appears_before_country_filter(self):
        """MonthYear filter must appear before country filter in the WHERE clause."""
        query = build_query()
        # Isolate only the WHERE clause to avoid false matches in SELECT
        where_clause = query[query.find("WHERE"):]
        monthyear_pos = where_clause.find("MonthYear BETWEEN")
        country_pos = where_clause.find("ActionGeo_CountryCode")
        assert monthyear_pos < country_pos

    def test_query_excludes_nigeria_in_noise_filter(self):
        """Noise filter must exclude locations containing 'nigeria'."""
        query = build_query()
        assert "nigeria" in query.lower()

    def test_query_excludes_edo_in_noise_filter(self):
        """Noise filter must exclude locations containing 'edo'."""
        query = build_query()
        assert "%edo%" in query.lower()

    def test_query_excludes_benin_city_in_noise_filter(self):
        """Noise filter must exclude locations containing 'benin city'."""
        query = build_query()
        assert "benin city" in query.lower()

    def test_query_uses_not_like_for_noise_filter(self):
        """Noise filter must use NOT LIKE operator."""
        query = build_query()
        assert "NOT LIKE" in query

    def test_query_covers_full_year_2025(self):
        """Query must cover January 2025 (202501) to December 2025 (202512)."""
        query = build_query()
        assert "202501" in query
        assert "202512" in query

    def test_query_filters_year_2025(self):
        """Query must filter on YEAR = 2025."""
        query = build_query()
        assert "YEAR = 2025" in query

    def test_all_required_columns_in_query(self):
        """All columns defined in config.COLUMNS must appear in the SELECT."""
        from pipeline.config import COLUMNS
        query = build_query()
        for col in COLUMNS:
            assert col in query, f"Column '{col}' missing from SELECT clause"