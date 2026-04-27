"""Tests for transformers — runs extractors, transforms, validates output shapes and columns."""

import sys

import pandas as pd

from src.extractors.social_extractor import SocialExtractor
from src.extractors.crm_extractor import CRMExtractor
from src.transformers.ga4_transformer import GA4Transformer
from src.transformers.social_transformer import SocialTransformer
from src.transformers.crm_transformer import CRMTransformer


def _make_fake_ga4_sessions() -> pd.DataFrame:
    """Build a synthetic GA4 sessions DataFrame (avoids BigQuery dependency)."""
    return pd.DataFrame({
        "session_date": pd.date_range("2021-01-01", periods=10, freq="D"),
        "traffic_source": ["google", None, "facebook", "(direct)", "newsletter",
                           "bing", None, "twitter", "partner_site", None],
        "traffic_medium": ["cpc", None, "social", "(none)", "email",
                           "organic", None, "social", "referral", "cpc"],
        "campaign_name": ["spring_sale", None, "brand_awareness", None, "weekly_digest",
                          None, None, "product_launch", None, "summer_promo"],
        "unique_users": [120, 80, 200, 150, 60, 90, 45, 180, 70, 110],
        "sessions": [150, 100, 250, 180, 75, 110, 55, 220, 85, 130],
        "purchases": [5, 2, 8, 3, 1, 4, 0, 6, 2, 3],
        "revenue": [500.0, 150.0, 1200.0, 200.0, 50.0, 350.0, 0.0, 900.0, 180.0, 250.0],
    })


def test_ga4_transformer():
    """GA4 transformer should rename date, fill nulls, add channel + derived cols."""
    df = _make_fake_ga4_sessions()
    result = GA4Transformer().transform(df)

    # Column checks
    assert "date" in result.columns, "Missing 'date' column"
    assert "session_date" not in result.columns, "'session_date' should be renamed"
    assert "channel_grouping" in result.columns, "Missing 'channel_grouping'"
    assert "conversion_rate" in result.columns, "Missing 'conversion_rate'"
    assert "revenue_per_session" in result.columns, "Missing 'revenue_per_session'"
    assert "data_source" in result.columns, "Missing 'data_source'"
    assert (result["data_source"] == "ga4").all()

    # Null fills
    assert result["traffic_source"].isna().sum() == 0, "traffic_source still has nulls"
    assert result["traffic_medium"].isna().sum() == 0, "traffic_medium still has nulls"
    assert result["campaign_name"].isna().sum() == 0, "campaign_name still has nulls"

    # Channel grouping spot checks
    channels = result["channel_grouping"].tolist()
    assert channels[0] == "paid_search"    # google / cpc
    assert channels[1] == "direct"         # (direct) / (none) after fill
    assert channels[2] == "social"         # facebook / social
    assert channels[3] == "direct"         # (direct) / (none)
    assert channels[4] == "email"          # newsletter / email
    assert channels[5] == "organic_search" # bing / organic
    assert channels[7] == "social"         # twitter / social
    assert channels[8] == "referral"       # partner_site / referral

    print(f"  Shape: {result.shape}")
    print(f"  Channels: {result['channel_grouping'].value_counts().to_dict()}")
    print(f"  Conversion rate range: {result['conversion_rate'].min():.4f} - {result['conversion_rate'].max():.4f}")


def test_social_transformer():
    """Social transformer should add cost_per_conversion, efficiency_score, data_source."""
    df = SocialExtractor().extract("20210101", "20210131")
    result = SocialTransformer().transform(df)

    assert "cost_per_conversion" in result.columns
    assert "efficiency_score" in result.columns
    assert "data_source" in result.columns
    assert (result["data_source"] == "social").all()
    assert pd.api.types.is_datetime64_any_dtype(result["date"])
    # cost_per_conversion should be non-negative
    assert (result["cost_per_conversion"] >= 0).all()

    print(f"  Shape: {result.shape}")
    print(f"  Avg cost/conv: ${result['cost_per_conversion'].mean():.2f}")
    print(f"  Avg efficiency: {result['efficiency_score'].mean():.4f}")


def test_crm_transformer():
    """CRM transformer should add pipeline days, stage order, engagement, high-value flag."""
    df = CRMExtractor().extract("20210101", "20210131")
    result = CRMTransformer().transform(df)

    assert "days_in_pipeline" in result.columns
    assert "stage_order" in result.columns
    assert "engagement_score" in result.columns
    assert "is_high_value" in result.columns
    assert "data_source" in result.columns
    assert (result["data_source"] == "crm").all()
    assert pd.api.types.is_datetime64_any_dtype(result["created_date"])
    assert pd.api.types.is_datetime64_any_dtype(result["last_activity_date"])
    # days_in_pipeline should be non-negative
    assert (result["days_in_pipeline"] >= 0).all()
    # stage_order should be 1-6
    assert result["stage_order"].between(1, 6).all()
    # ~20% should be high-value
    hv_pct = result["is_high_value"].mean()
    assert 0.05 < hv_pct < 0.40, f"High-value pct {hv_pct:.1%} out of expected range"

    print(f"  Shape: {result.shape}")
    print(f"  High-value contacts: {result['is_high_value'].sum()} ({hv_pct:.1%})")
    print(f"  Avg engagement score: {result['engagement_score'].mean():.1f}")
    print(f"  Stage distribution:\n{result['lifecycle_stage'].value_counts().to_string()}")


if __name__ == "__main__":
    tests = [
        ("GA4 Transformer", test_ga4_transformer),
        ("Social Transformer", test_social_transformer),
        ("CRM Transformer", test_crm_transformer),
    ]
    passed = 0
    failed = 0
    for name, test_fn in tests:
        print(f"\n{'=' * 50}")
        print(f"Testing {name}...")
        print("=" * 50)
        try:
            test_fn()
            print(f"[PASS] {name}")
            passed += 1
        except AssertionError as e:
            print(f"[FAIL] {name}: {e}")
            failed += 1
        except Exception as e:
            print(f"[ERROR] {name}: {e}")
            failed += 1

    print(f"\n{'=' * 50}")
    print(f"Results: {passed} passed, {failed} failed out of {len(tests)} tests")
    print("=" * 50)
    sys.exit(1 if failed else 0)
