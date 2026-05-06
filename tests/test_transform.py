"""
Unit tests for the transform module.

Tests clean_basic(), convert_types(), enrich_data() and filter_data()
using synthetic DataFrames — no BigQuery connection required.

Author  : Team 7 - Benin Insights Challenge 2026
Date    : May 2026
Version : 1.0
"""

import pytest
import pandas as pd


from pipeline.transform import clean_basic, convert_types, enrich_data, filter_data


# ─────────────────────────────────────────────────────────────────
# SHARED FIXTURE
# ─────────────────────────────────────────────────────────────────

@pytest.fixture
def sample_raw_df():
    """
    Minimal raw DataFrame mimicking BigQuery GDELT output.
    """
    return pd.DataFrame({
        "SQLDATE"              : [20250115, 20250210, None,     20250310, 20250415],
        "DATEADDED"            : [20250115, 20250212, 20250310, 20250310, 20250415],
        "MonthYear"            : [202501,   202502,   202503,   202503,   202504],
        "Year"                 : [2025,     2025,     2025,     2025,     2025],
        "Actor1Name"           : ["Benin",  "France", None,    "Nigeria", "Benin"],
        "Actor1CountryCode"    : ["BEN",    "FRA",    None,    "NI",      "BEN"],
        "Actor1Type1Code"      : ["GOV",    "GOV",    None,    "MIL",     "BUS"],
        "Actor2Name"           : ["France", "Benin",  "Benin", None,      None],
        "Actor2CountryCode"    : ["FRA",    "BEN",    "BEN",   None,      None],
        "Actor2Type1Code"      : ["GOV",    "GOV",    "CVL",   None,      None],
        "IsRootEvent"          : [1,        1,        0,       1,         1],
        "EventCode"            : ["051",    "036",    "190",   "172",     "043"],
        "EventBaseCode"        : ["051",    "036",    "190",   "172",     "043"],
        "EventRootCode"        : [5,        3,        19,      17,        4],
        "QuadClass"            : [2,        1,        4,       4,         1],
        "GoldsteinScale"       : [3.4,      4.0,      -10.0,   -5.0,      2.8],
        "AvgTone"              : [2.5,      1.0,      -8.0,    -6.0,      3.0],
        "NumMentions"          : [10,       5,        20,      15,        8],
        "NumSources"           : [3,        2,        8,       6,         3],
        "NumArticles"          : [10,       5,        20,      15,        8],
        "ActionGeo_FullName"   : ["Cotonou, Benin", "Paris, France",
                                   "Porto-Novo, Benin", "Lagos, Nigeria",
                                   "Abomey, Benin"],
        "ActionGeo_CountryCode": ["BN",     "FR",     "BN",    "NI",      "BN"],
        "ActionGeo_Lat"        : [6.37,     48.85,    6.49,    6.45,      7.18],
        "ActionGeo_Long"       : [2.42,     2.35,     2.61,    3.40,      1.99],
        "SOURCEURL"            : [
            "https://www.rfi.fr/benin/article1",
            "https://www.lemonde.fr/article2",
            "https://allafrica.com/article3",
            None,
            "https://www.bbc.com/article5",
        ],
    })


@pytest.fixture
def cleaned_df(sample_raw_df):
    """Clean and type-convert the sample DataFrame before enrichment tests."""
    df = clean_basic(sample_raw_df)
    return convert_types(df)


# ─────────────────────────────────────────────────────────────────
# TESTS — clean_basic()
# ─────────────────────────────────────────────────────────────────

class TestCleanBasic:
    """Tests for the basic cleaning step."""

    def test_removes_fully_duplicate_rows(self, sample_raw_df):
        """Fully duplicate rows must be removed."""
        df_with_dups = pd.concat(
            [sample_raw_df, sample_raw_df], ignore_index=True
        )
        result = clean_basic(df_with_dups)
        assert len(result) == 3

    def test_removes_rows_with_null_sqldate(self, sample_raw_df):
        """Rows with null SQLDATE must be removed."""
        result = clean_basic(sample_raw_df)
        assert result["SQLDATE"].isna().sum() == 0

    def test_removes_rows_with_null_sourceurl(self, sample_raw_df):
        """Rows with null SOURCEURL must be removed."""
        result = clean_basic(sample_raw_df)
        assert result["SOURCEURL"].isna().sum() == 0

    def test_index_is_reset_after_cleaning(self, sample_raw_df):
        """Index must be sequential (0, 1, 2...) after cleaning."""
        result = clean_basic(sample_raw_df)
        assert list(result.index) == list(range(len(result)))

    def test_returns_dataframe(self, sample_raw_df):
        """clean_basic must return a pandas DataFrame."""
        result = clean_basic(sample_raw_df)
        assert isinstance(result, pd.DataFrame)

    def test_valid_rows_are_preserved(self, sample_raw_df):
        """Rows with valid SQLDATE and SOURCEURL must be kept."""
        result = clean_basic(sample_raw_df)
        # 5 rows total:
        # - Row 2: null SQLDATE -> removed
        # - Row 3: null SOURCEURL -> removed
        # - Rows 0, 1, 4: valid -> kept
        assert len(result) == 3


# ─────────────────────────────────────────────────────────────────
# TESTS — convert_types()
# ─────────────────────────────────────────────────────────────────

class TestConvertTypes:
    """Tests for the type conversion step."""

    def test_sqldate_converted_to_datetime(self, sample_raw_df):
        """SQLDATE must be converted from int to datetime."""
        df = clean_basic(sample_raw_df)
        result = convert_types(df)
        assert pd.api.types.is_datetime64_any_dtype(result["SQLDATE"])

    def test_avgtone_is_float(self, sample_raw_df):
        """AvgTone must be float after conversion."""
        df = clean_basic(sample_raw_df)
        result = convert_types(df)
        assert result["AvgTone"].dtype in [float, "float64"]

    def test_numarticles_is_integer(self, sample_raw_df):
        """NumArticles must be integer after conversion."""
        df = clean_basic(sample_raw_df)
        result = convert_types(df)
        assert result["NumArticles"].dtype in ["int32", "int64"]

    def test_invalid_dates_become_nat(self, sample_raw_df):
        """Rows with invalid SQLDATE must produce NaT after conversion."""
        df = clean_basic(sample_raw_df.copy())
        df.loc[0, "SQLDATE"] = 99999999  # Invalid date
        result = convert_types(df)
        assert result["SQLDATE"].isna().any()


# ─────────────────────────────────────────────────────────────────
# TESTS — enrich_data()
# ─────────────────────────────────────────────────────────────────

class TestEnrichData:
    """Tests for the data enrichment step — all 5 analytical questions."""

    # --- Q1: event_root_label ------------------------------------

    def test_event_root_label_maps_int_4_to_consultation(self, cleaned_df):
        """EventRootCode = 4 (int64) must map to 'Consultation', not 'Autre'."""
        result = enrich_data(cleaned_df)
        code4_rows = result[
            result["EventRootCode"].apply(
                lambda x: int(float(x)) == 4 if pd.notna(x) else False
            )
        ]
        assert all(code4_rows["event_root_label"] == "Consultation")

    def test_event_root_label_maps_int_19_to_violence(self, cleaned_df):
        """EventRootCode = 19 (int64) must map to 'Violence de masse'."""
        result = enrich_data(cleaned_df)
        code19_rows = result[
            result["EventRootCode"].apply(
                lambda x: int(float(x)) == 19 if pd.notna(x) else False
            )
        ]
        assert all(code19_rows["event_root_label"] == "Violence de masse")

    def test_event_root_label_no_autre_for_valid_codes(self, cleaned_df):
        """All valid EventRootCode values in fixture must map to known labels."""
        result = enrich_data(cleaned_df)
        assert "Autre" not in result["event_root_label"].values

    def test_event_date_format_is_yyyy_mm_dd(self, cleaned_df):
        """event_date must be formatted as YYYY-MM-DD."""
        result = enrich_data(cleaned_df)
        import re
        pattern = re.compile(r"^\d{4}-\d{2}-\d{2}$")
        assert all(result["event_date"].apply(lambda d: bool(pattern.match(d))))

    def test_event_month_is_integer(self, cleaned_df):
        """event_month must be an integer between 1 and 12."""
        result = enrich_data(cleaned_df)
        assert result["event_month"].between(1, 12).all()

    # --- Q2: tone_category, stability_category -------------------

    def test_tone_positive_when_avgtone_above_threshold(self, cleaned_df):
        """AvgTone > 2 must produce tone_category == 'Positif'."""
        result = enrich_data(cleaned_df)
        positive_rows = result[result["AvgTone"] > 2]
        assert all(positive_rows["tone_category"] == "Positif")

    def test_tone_negative_when_avgtone_below_threshold(self, cleaned_df):
        """AvgTone < -2 must produce tone_category == 'Négatif'."""
        result = enrich_data(cleaned_df)
        negative_rows = result[result["AvgTone"] < -2]
        assert all(negative_rows["tone_category"] == "Négatif")

    def test_tone_neutre_when_avgtone_within_thresholds(self, cleaned_df):
        """AvgTone between -2 and 2 must produce tone_category == 'Neutre'."""
        result = enrich_data(cleaned_df)
        neutral_rows = result[result["AvgTone"].between(-2, 2)]
        assert all(neutral_rows["tone_category"] == "Neutre")

    def test_stability_destabilisant_when_goldstein_very_low(self, cleaned_df):
        """GoldsteinScale < -3 must produce stability_category == 'Déstabilisant'."""
        result = enrich_data(cleaned_df)
        destab_rows = result[result["GoldsteinScale"] < -3]
        assert all(destab_rows["stability_category"] == "Déstabilisant")

    def test_stability_stabilisant_when_goldstein_high(self, cleaned_df):
        """GoldsteinScale > 3 must produce stability_category == 'Stabilisant'."""
        result = enrich_data(cleaned_df)
        stab_rows = result[result["GoldsteinScale"] > 3]
        assert all(stab_rows["stability_category"] == "Stabilisant")

    # --- Q3: propagation_delay_days ------------------------------

    def test_propagation_delay_non_negative(self, cleaned_df):
        """propagation_delay_days must always be >= 0."""
        result = enrich_data(cleaned_df)
        non_null = result["propagation_delay_days"].dropna()
        assert (non_null >= 0).all()

    def test_propagation_delay_zero_when_same_date(self, cleaned_df):
        """propagation_delay_days must be 0 when SQLDATE == DATEADDED."""
        result = enrich_data(cleaned_df)
        same_date_rows = result[result["SQLDATE"] == result["DATEADDED"]]
        assert all(same_date_rows["propagation_delay_days"] == 0)

    # --- Q4: source_domain, is_crisis_period ---------------------

    def test_source_domain_extracted_from_rfi(self, cleaned_df):
        """rfi.fr must be extracted from https://www.rfi.fr/benin/article1."""
        result = enrich_data(cleaned_df)
        rfi_rows = result[result["SOURCEURL"].str.contains("rfi.fr", na=False)]
        assert all(rfi_rows["source_domain"] == "rfi.fr")

    def test_source_domain_extracted_from_lemonde(self, cleaned_df):
        """lemonde.fr must be extracted from https://www.lemonde.fr/article2."""
        result = enrich_data(cleaned_df)
        lemonde_rows = result[result["SOURCEURL"].str.contains("lemonde.fr", na=False)]
        assert all(lemonde_rows["source_domain"] == "lemonde.fr")

    def test_is_crisis_period_true_when_avgtone_very_negative(self, cleaned_df):
        """is_crisis_period must be True when AvgTone < -5."""
        result = enrich_data(cleaned_df)
        crisis_rows = result[result["AvgTone"] < -5]
        assert all(crisis_rows["is_crisis_period"])

    def test_is_crisis_period_is_boolean(self, cleaned_df):
        """is_crisis_period must be a boolean column."""
        result = enrich_data(cleaned_df)
        assert result["is_crisis_period"].dtype == bool

    # --- Q5: benin_role ------------------------------------------

    def test_benin_actor1_produces_acteur(self, cleaned_df):
        """Actor1CountryCode == 'BEN' (not Actor2) must produce 'Acteur'."""
        result = enrich_data(cleaned_df)
        acteur_rows = result[
            (result["Actor1CountryCode"] == "BEN") &
            (result["Actor2CountryCode"] != "BEN")
        ]
        assert all(acteur_rows["benin_role"] == "Acteur")

    def test_benin_actor2_produces_spectateur(self, cleaned_df):
        """Actor2CountryCode == 'BEN' (not Actor1) must produce 'Spectateur'."""
        result = enrich_data(cleaned_df)
        spectateur_rows = result[
            (result["Actor2CountryCode"] == "BEN") &
            (result["Actor1CountryCode"] != "BEN")
        ]
        assert all(spectateur_rows["benin_role"] == "Spectateur")

    def test_benin_both_actors_produces_mixte(self, cleaned_df):
        """Both Actor1 and Actor2 == 'BEN' must produce 'Mixte'."""
        mixte_row = cleaned_df.iloc[[0]].copy()
        mixte_row["Actor1CountryCode"] = "BEN"
        mixte_row["Actor2CountryCode"] = "BEN"
        df_test = pd.concat([cleaned_df, mixte_row], ignore_index=True)
        result = enrich_data(df_test)
        mixte_rows = result[
            (result["Actor1CountryCode"] == "BEN") &
            (result["Actor2CountryCode"] == "BEN")
        ]
        assert all(mixte_rows["benin_role"] == "Mixte")

    def test_nan_actor_codes_produce_contexte(self, cleaned_df):
        """Rows with NaN in both actor codes must produce 'Contexte'."""
        result = enrich_data(cleaned_df)
        contexte_rows = result[
            result["Actor1CountryCode"].isna() &
            result["Actor2CountryCode"].isna()
        ]
        assert all(contexte_rows["benin_role"] == "Contexte")

    def test_benin_role_column_exists(self, cleaned_df):
        """benin_role column must exist after enrichment."""
        result = enrich_data(cleaned_df)
        assert "benin_role" in result.columns

    def test_benin_role_only_valid_values(self, cleaned_df):
        """benin_role must only contain known values."""
        result = enrich_data(cleaned_df)
        valid_values = {"Acteur", "Spectateur", "Mixte", "Contexte"}
        assert set(result["benin_role"].unique()).issubset(valid_values)


# ─────────────────────────────────────────────────────────────────
# TESTS — filter_data()
# ─────────────────────────────────────────────────────────────────

class TestFilterData:
    """Tests for the final filtering step."""

    def test_removes_nat_dates_after_conversion(self, cleaned_df):
        """Rows with NaT SQLDATE must be removed by filter_data."""
        df = cleaned_df.copy()
        df.loc[0, "SQLDATE"] = pd.NaT
        result = filter_data(df)
        assert result["SQLDATE"].isna().sum() == 0

    def test_removes_aberrant_latitude(self, cleaned_df):
        """Rows with latitude outside [-90, 90] must be removed."""
        df = cleaned_df.copy()
        df.loc[0, "ActionGeo_Lat"] = 999.0
        result = filter_data(df)
        assert (result["ActionGeo_Lat"].dropna() <= 90).all()

    def test_removes_aberrant_longitude(self, cleaned_df):
        """Rows with longitude outside [-180, 180] must be removed."""
        df = cleaned_df.copy()
        df.loc[0, "ActionGeo_Long"] = 999.0
        result = filter_data(df)
        assert (result["ActionGeo_Long"].dropna() <= 180).all()

    def test_valid_coordinates_are_preserved(self, cleaned_df):
        """Rows with valid coordinates must not be removed."""
        result = filter_data(cleaned_df)
        # All coordinates in the fixture are valid
        assert len(result) == len(cleaned_df)