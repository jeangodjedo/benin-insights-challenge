"""
Unit tests for the BeninSentinel module.

Tests the early warning system on synthetic and reduced real data —
no BigQuery connection required, no full dataset dependency.

Author  : Team 7 — Bénin Insights Challenge 2026
"""

import pytest
import pandas as pd
import numpy as np

from pipeline.sentinel import (
    build_daily_series,
    compute_weak_signals,
    compute_risk_score,
    compute_department_risk,
    run_sentinel,
    detect_lead_time,
    ALERT_THRESHOLDS,
    ACTION_PLAYBOOK,
    DEFAULT_WEIGHTS,
    _classify_alert,
)


# ─────────────────────────────────────────────────────────────────
# FIXTURES
# ─────────────────────────────────────────────────────────────────

@pytest.fixture
def calm_dataset():
    """
    Generate a calm year (180 days, low-intensity events).
    No crisis should be detected on this dataset.
    """
    dates = pd.date_range("2025-01-01", periods=180, freq="D")
    np.random.seed(42)
    rows = []
    for d in dates:
        # 10 calm events per day
        for _ in range(10):
            rows.append({
                "SQLDATE": d,
                "NumArticles": np.random.randint(1, 5),
                "AvgTone": np.random.normal(-1, 1),
                "GoldsteinScale": np.random.normal(2, 1),
                "tone_category": np.random.choice(["Neutre", "Positif"], p=[0.7, 0.3]),
                "event_root_label": np.random.choice(["Consultation", "Coopération", "Diplomatie"]),
                "QuadClass": np.random.choice([1, 2]),
                "source_domain": np.random.choice([f"src{i}.com" for i in range(5)]),
                "event_department": np.random.choice(["Littoral", "Atlantique", "Ouémé"]),
            })
    return pd.DataFrame(rows)


@pytest.fixture
def crisis_dataset(calm_dataset):
    """
    Inject a sharp crisis on day 60 — 5x volume, violent events, very negative tone.
    """
    crisis_day = pd.Timestamp("2025-03-02")  # day 60
    np.random.seed(123)
    crisis_rows = []
    for _ in range(50):  # 5x normal volume
        crisis_rows.append({
            "SQLDATE": crisis_day,
            "NumArticles": np.random.randint(20, 100),
            "AvgTone": np.random.normal(-7, 1),
            "GoldsteinScale": np.random.normal(-6, 1),
            "tone_category": "Négatif",
            "event_root_label": np.random.choice(["Assaut", "Violence de masse", "Menace"]),
            "QuadClass": np.random.choice([3, 4]),
            "source_domain": np.random.choice([f"news{i}.com" for i in range(15)]),
            "event_department": np.random.choice(["Alibori", "Atacora"]),
        })
    return pd.concat([calm_dataset, pd.DataFrame(crisis_rows)], ignore_index=True)


# ─────────────────────────────────────────────────────────────────
# TESTS — build_daily_series()
# ─────────────────────────────────────────────────────────────────

class TestBuildDailySeries:
    """Tests for the daily series construction step."""

    def test_returns_dataframe(self, calm_dataset):
        """build_daily_series must return a DataFrame."""
        result = build_daily_series(calm_dataset)
        assert isinstance(result, pd.DataFrame)

    def test_one_row_per_day(self, calm_dataset):
        """One row per calendar day must be produced."""
        result = build_daily_series(calm_dataset)
        expected_days = calm_dataset["SQLDATE"].nunique()
        assert len(result) == expected_days

    def test_required_columns_present(self, calm_dataset):
        """All expected aggregation columns must be present."""
        result = build_daily_series(calm_dataset)
        expected = {"date", "n_events", "n_articles", "avg_tone", "avg_goldstein",
                    "n_negative", "n_protest", "n_violence", "n_quad3", "n_quad4",
                    "n_sources", "pct_negative"}
        assert expected.issubset(set(result.columns))

    def test_chronological_order(self, calm_dataset):
        """Dates must be sorted ascending."""
        result = build_daily_series(calm_dataset)
        assert (result["date"].diff().dropna() > pd.Timedelta(0)).all()

    def test_empty_input_returns_empty(self):
        """Empty input DataFrame must return empty result."""
        result = build_daily_series(pd.DataFrame())
        assert result.empty


# ─────────────────────────────────────────────────────────────────
# TESTS — compute_weak_signals()
# ─────────────────────────────────────────────────────────────────

class TestComputeWeakSignals:
    """Tests for weak signal computation."""

    def test_signals_in_unit_interval(self, calm_dataset):
        """All weak signals must lie in [0, 1]."""
        daily = build_daily_series(calm_dataset)
        result = compute_weak_signals(daily)
        for sig in ["sig_tone", "sig_negative", "sig_protest", "sig_quad3", "sig_quad4", "sig_violence"]:
            assert (result[sig] >= 0).all(), f"{sig} contains negative values"
            assert (result[sig] <= 1).all(), f"{sig} contains values > 1"

    def test_calm_dataset_has_low_signals(self, calm_dataset):
        """On a calm dataset, all signal means must remain low (< 0.3)."""
        daily = build_daily_series(calm_dataset)
        result = compute_weak_signals(daily)
        # Skip warmup period (first 30 days)
        steady = result.iloc[30:]
        for sig in ["sig_negative", "sig_quad4", "sig_violence"]:
            assert steady[sig].mean() < 0.3, f"{sig} mean too high on calm data: {steady[sig].mean()}"


# ─────────────────────────────────────────────────────────────────
# TESTS — compute_risk_score()
# ─────────────────────────────────────────────────────────────────

class TestComputeRiskScore:
    """Tests for composite risk score computation."""

    def test_score_in_unit_interval(self, crisis_dataset):
        """Risk score must remain in [0, 1]."""
        result = run_sentinel(crisis_dataset)
        assert (result["risk_score"] >= 0).all()
        assert (result["risk_score"] <= 1).all()

    def test_alert_levels_valid(self, crisis_dataset):
        """alert_level must be one of VERT/JAUNE/ORANGE/ROUGE."""
        result = run_sentinel(crisis_dataset)
        valid = {"VERT", "JAUNE", "ORANGE", "ROUGE"}
        assert set(result["alert_level"].unique()).issubset(valid)

    def test_action_provided_for_each_alert(self, crisis_dataset):
        """Every row must have a non-empty action recommendation."""
        result = run_sentinel(crisis_dataset)
        assert result["action"].notna().all()
        assert (result["action"].str.len() > 10).all()

    def test_custom_weights_change_score(self, crisis_dataset):
        """Different weights must produce different scores."""
        result_default = run_sentinel(crisis_dataset)
        custom = {"tone": 1.0, "negative": 0, "protest": 0, "quad3": 0, "quad4": 0, "violence": 0}
        result_custom = run_sentinel(crisis_dataset, weights=custom)
        # Some rows must differ
        assert not result_default["risk_score"].equals(result_custom["risk_score"])


# ─────────────────────────────────────────────────────────────────
# TESTS — _classify_alert()
# ─────────────────────────────────────────────────────────────────

class TestClassifyAlert:
    """Tests for alert classification logic."""

    def test_low_score_returns_vert(self):
        assert _classify_alert(0.0) == "VERT"
        assert _classify_alert(0.35) == "VERT"

    def test_mid_score_returns_jaune(self):
        assert _classify_alert(0.40) == "JAUNE"
        assert _classify_alert(0.55) == "JAUNE"

    def test_high_score_returns_orange(self):
        assert _classify_alert(0.60) == "ORANGE"
        assert _classify_alert(0.75) == "ORANGE"

    def test_extreme_score_returns_rouge(self):
        assert _classify_alert(0.80) == "ROUGE"
        assert _classify_alert(1.00) == "ROUGE"

    def test_thresholds_consistent(self):
        """ALERT_THRESHOLDS must cover the full [0, 1] interval without gaps."""
        levels = list(ALERT_THRESHOLDS.values())
        # Sort by lower bound
        levels = sorted(levels, key=lambda x: x[0])
        for i in range(len(levels) - 1):
            assert levels[i][1] == levels[i + 1][0], f"Gap between {levels[i]} and {levels[i+1]}"


# ─────────────────────────────────────────────────────────────────
# TESTS — detect_lead_time()
# ─────────────────────────────────────────────────────────────────

class TestDetectLeadTime:
    """Tests for the lead time detection helper."""

    def test_no_detection_returns_minus_one(self, calm_dataset):
        """On calm data with no crisis, detection should fail gracefully."""
        result = run_sentinel(calm_dataset)
        target = pd.Timestamp("2025-04-01")
        lead, date = detect_lead_time(result, target, "ORANGE", 14)
        # On a fully calm dataset, no ORANGE should be detected
        assert lead == -1
        assert date is None

    def test_invalid_level_raises(self, calm_dataset):
        """An invalid alert level must raise ValueError."""
        result = run_sentinel(calm_dataset)
        with pytest.raises(ValueError):
            detect_lead_time(result, pd.Timestamp("2025-01-15"), "VIOLET", 14)


# ─────────────────────────────────────────────────────────────────
# TESTS — compute_department_risk()
# ─────────────────────────────────────────────────────────────────

class TestDepartmentRisk:
    """Tests for the department-level risk decomposition."""

    def test_returns_dataframe(self, crisis_dataset):
        result = compute_department_risk(crisis_dataset, pd.Timestamp("2025-03-02"))
        assert isinstance(result, pd.DataFrame)

    def test_local_risk_in_unit_interval(self, crisis_dataset):
        result = compute_department_risk(crisis_dataset, pd.Timestamp("2025-03-02"))
        if not result.empty:
            assert (result["local_risk"] >= 0).all()
            assert (result["local_risk"] <= 1).all()

    def test_sorted_descending(self, crisis_dataset):
        """Result must be sorted by local_risk descending."""
        result = compute_department_risk(crisis_dataset, pd.Timestamp("2025-03-02"))
        if len(result) > 1:
            assert (result["local_risk"].diff().dropna() <= 0).all()


# ─────────────────────────────────────────────────────────────────
# TESTS — Configuration constants
# ─────────────────────────────────────────────────────────────────

class TestConfiguration:
    """Tests for module-level configuration constants."""

    def test_default_weights_sum_to_one(self):
        """DEFAULT_WEIGHTS must sum to exactly 1.0."""
        assert abs(sum(DEFAULT_WEIGHTS.values()) - 1.0) < 1e-9

    def test_alert_thresholds_cover_unit_interval(self):
        """ALERT_THRESHOLDS must cover [0, 1]."""
        lower_bounds = sorted([low for low, high in ALERT_THRESHOLDS.values()])
        upper_bounds = sorted([high for low, high in ALERT_THRESHOLDS.values()])
        assert lower_bounds[0] == 0.0
        assert max(upper_bounds) >= 1.0

    def test_action_playbook_has_all_levels(self):
        """ACTION_PLAYBOOK must contain an entry for each alert level."""
        for level in ["VERT", "JAUNE", "ORANGE", "ROUGE"]:
            assert level in ACTION_PLAYBOOK
            assert len(ACTION_PLAYBOOK[level]) > 30  # substantive content
