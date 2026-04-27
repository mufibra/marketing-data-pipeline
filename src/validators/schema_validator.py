"""Schema Validator — validates DataFrames against defined schemas before loading."""

from dataclasses import dataclass, field

import pandas as pd


@dataclass
class ValidationResult:
    is_valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    row_count: int = 0
    null_counts: dict[str, int] = field(default_factory=dict)


@dataclass
class SchemaDefinition:
    required_columns: list[str]
    non_negative_columns: list[str] = field(default_factory=list)
    unique_columns: list[str] = field(default_factory=list)
    allowed_values: dict[str, list[str]] = field(default_factory=dict)
    max_null_rate: float = 0.10


# ── Schema registry ──────────────────────────────────────────────────────────

SCHEMAS: dict[str, SchemaDefinition] = {
    "ga4_sessions": SchemaDefinition(
        required_columns=[
            "session_date", "traffic_source", "traffic_medium", "campaign_name",
            "unique_users", "sessions", "purchases", "revenue",
        ],
        non_negative_columns=["unique_users", "sessions", "purchases", "revenue"],
    ),
    "ga4_funnel": SchemaDefinition(
        required_columns=["event_date", "event_name", "event_count", "unique_users"],
        non_negative_columns=["event_count", "unique_users"],
        allowed_values={
            "event_name": [
                "session_start", "page_view", "view_item",
                "add_to_cart", "begin_checkout", "purchase",
            ],
        },
    ),
    "social": SchemaDefinition(
        required_columns=[
            "date", "platform", "campaign_type", "campaign_name",
            "impressions", "clicks", "ctr", "cpc", "spend",
            "conversions", "conversion_value", "roas",
        ],
        non_negative_columns=[
            "impressions", "clicks", "ctr", "cpc", "spend",
            "conversions", "conversion_value",
        ],
        allowed_values={
            "platform": ["facebook", "instagram", "twitter", "linkedin", "tiktok"],
            "campaign_type": ["awareness", "consideration", "conversion", "retargeting"],
        },
    ),
    "crm": SchemaDefinition(
        required_columns=[
            "contact_id", "email", "company", "industry", "lead_source",
            "lifecycle_stage", "created_date", "last_activity_date",
            "deal_value", "num_touches", "email_opens", "page_views",
        ],
        non_negative_columns=["deal_value", "num_touches", "email_opens", "page_views"],
        unique_columns=["contact_id", "email"],
        allowed_values={
            "lifecycle_stage": ["lead", "mql", "sql", "opportunity", "customer", "churned"],
        },
    ),
}


# ── Validator ─────────────────────────────────────────────────────────────────

class SchemaValidator:
    def validate(self, df: pd.DataFrame, schema_name: str) -> ValidationResult:
        """Validate a DataFrame against a named schema."""
        if schema_name not in SCHEMAS:
            return ValidationResult(
                is_valid=False,
                errors=[f"Unknown schema: '{schema_name}'"],
            )

        schema = SCHEMAS[schema_name]
        errors: list[str] = []
        warnings: list[str] = []

        # 1. Empty DataFrame check
        if df.empty:
            return ValidationResult(
                is_valid=False,
                errors=["DataFrame is empty"],
                row_count=0,
            )

        row_count = len(df)

        # 2. Required columns
        missing = set(schema.required_columns) - set(df.columns)
        if missing:
            errors.append(f"Missing required columns: {sorted(missing)}")

        # Stop early if columns are missing — remaining checks would fail
        if errors:
            return ValidationResult(
                is_valid=False,
                errors=errors,
                warnings=warnings,
                row_count=row_count,
            )

        # 3. Null rate check (>10% triggers error)
        null_counts: dict[str, int] = {}
        for col in schema.required_columns:
            n_nulls = int(df[col].isna().sum())
            null_counts[col] = n_nulls
            null_rate = n_nulls / row_count
            if null_rate > schema.max_null_rate:
                errors.append(
                    f"Column '{col}' null rate {null_rate:.1%} exceeds "
                    f"threshold {schema.max_null_rate:.0%}"
                )
            elif n_nulls > 0:
                warnings.append(f"Column '{col}' has {n_nulls} nulls ({null_rate:.1%})")

        # 4. Non-negative numeric columns
        for col in schema.non_negative_columns:
            if col not in df.columns:
                continue
            numeric_vals = pd.to_numeric(df[col], errors="coerce").dropna()
            n_negative = int((numeric_vals < 0).sum())
            if n_negative > 0:
                errors.append(f"Column '{col}' has {n_negative} negative values")

        # 5. Allowed categorical values
        for col, allowed in schema.allowed_values.items():
            if col not in df.columns:
                continue
            actual = set(df[col].dropna().unique())
            invalid = actual - set(allowed)
            if invalid:
                errors.append(
                    f"Column '{col}' has invalid values: {sorted(invalid)}"
                )

        # 6. Uniqueness constraints
        for col in schema.unique_columns:
            if col not in df.columns:
                continue
            n_dupes = int(df[col].duplicated().sum())
            if n_dupes > 0:
                errors.append(f"Column '{col}' has {n_dupes} duplicate values")

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            row_count=row_count,
            null_counts=null_counts,
        )
