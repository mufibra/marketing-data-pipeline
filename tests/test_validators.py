"""Tests for SchemaValidator — runs extractors then validates each DataFrame."""

import sys
import pandas as pd

from src.extractors.social_extractor import SocialExtractor
from src.extractors.crm_extractor import CRMExtractor
from src.validators.schema_validator import SchemaValidator, ValidationResult


def _print_result(name: str, result: ValidationResult):
    status = "PASS" if result.is_valid else "FAIL"
    print(f"\n[{status}] {name} — {result.row_count} rows")
    for e in result.errors:
        print(f"  ERROR: {e}")
    for w in result.warnings:
        print(f"  WARN:  {w}")
    if result.null_counts:
        non_zero = {k: v for k, v in result.null_counts.items() if v > 0}
        if non_zero:
            print(f"  Nulls: {non_zero}")


def test_social_validation():
    """Social metrics should pass validation."""
    df = SocialExtractor().extract("20210101", "20210131")
    result = SchemaValidator().validate(df, "social")
    _print_result("social", result)
    assert result.is_valid, f"Social validation failed: {result.errors}"


def test_crm_validation():
    """CRM contacts should pass validation."""
    df = CRMExtractor().extract("20210101", "20210131")
    result = SchemaValidator().validate(df, "crm")
    _print_result("crm", result)
    assert result.is_valid, f"CRM validation failed: {result.errors}"


def test_empty_dataframe():
    """Empty DataFrame should fail validation."""
    df = pd.DataFrame()
    result = SchemaValidator().validate(df, "social")
    _print_result("empty_df", result)
    assert not result.is_valid
    assert "DataFrame is empty" in result.errors[0]


def test_missing_columns():
    """DataFrame with missing columns should fail."""
    df = pd.DataFrame({"date": ["2021-01-01"], "platform": ["facebook"]})
    result = SchemaValidator().validate(df, "social")
    _print_result("missing_cols", result)
    assert not result.is_valid
    assert any("Missing required columns" in e for e in result.errors)


def test_negative_values():
    """Negative values in non-negative columns should fail."""
    df = SocialExtractor().extract("20210101", "20210105")
    df.loc[0, "impressions"] = -100
    result = SchemaValidator().validate(df, "social")
    _print_result("negative_vals", result)
    assert not result.is_valid
    assert any("negative" in e for e in result.errors)


def test_invalid_categorical():
    """Invalid categorical values should fail."""
    df = SocialExtractor().extract("20210101", "20210105")
    df.loc[0, "platform"] = "myspace"
    result = SchemaValidator().validate(df, "social")
    _print_result("invalid_cat", result)
    assert not result.is_valid
    assert any("invalid values" in e for e in result.errors)


def test_duplicate_unique():
    """Duplicate values in unique columns should fail."""
    df = CRMExtractor().extract("20210101", "20210131")
    df.loc[1, "contact_id"] = df.loc[0, "contact_id"]
    result = SchemaValidator().validate(df, "crm")
    _print_result("duplicate_unique", result)
    assert not result.is_valid
    assert any("duplicate" in e for e in result.errors)


def test_high_null_rate():
    """Null rate >10% should fail validation."""
    df = SocialExtractor().extract("20210101", "20210131")
    # Set >10% of 'platform' to None
    n_to_null = int(len(df) * 0.15)
    df.loc[:n_to_null, "platform"] = None
    result = SchemaValidator().validate(df, "social")
    _print_result("high_null", result)
    assert not result.is_valid
    assert any("null rate" in e for e in result.errors)


def test_unknown_schema():
    """Unknown schema name should fail."""
    df = pd.DataFrame({"a": [1]})
    result = SchemaValidator().validate(df, "nonexistent")
    _print_result("unknown_schema", result)
    assert not result.is_valid
    assert "Unknown schema" in result.errors[0]


if __name__ == "__main__":
    tests = [
        test_social_validation,
        test_crm_validation,
        test_empty_dataframe,
        test_missing_columns,
        test_negative_values,
        test_invalid_categorical,
        test_duplicate_unique,
        test_high_null_rate,
        test_unknown_schema,
    ]
    passed = 0
    failed = 0
    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"\n  ASSERTION FAILED: {e}")
            failed += 1
        except Exception as e:
            print(f"\n  EXCEPTION in {test.__name__}: {e}")
            failed += 1

    print(f"\n{'=' * 50}")
    print(f"Results: {passed} passed, {failed} failed out of {len(tests)} tests")
    print("=" * 50)
    sys.exit(1 if failed else 0)
