"""CRM Transformer — enriches CRM contacts with pipeline and engagement metrics."""

import pandas as pd

STAGE_ORDER = {
    "lead": 1,
    "mql": 2,
    "sql": 3,
    "opportunity": 4,
    "customer": 5,
    "churned": 6,
}


class CRMTransformer:
    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """Standardize dates and add derived columns."""
        df = df.copy()

        # Standardize dates to datetime
        df["created_date"] = pd.to_datetime(df["created_date"])
        df["last_activity_date"] = pd.to_datetime(df["last_activity_date"])

        # Days in pipeline
        df["days_in_pipeline"] = (df["last_activity_date"] - df["created_date"]).dt.days

        # Stage order numeric mapping
        df["stage_order"] = df["lifecycle_stage"].map(STAGE_ORDER)

        # Engagement score
        df["engagement_score"] = (
            df["num_touches"] * 3
            + df["email_opens"] * 2
            + df["page_views"] * 1
        )

        # High-value flag (deal_value > 80th percentile)
        threshold = df["deal_value"].quantile(0.80)
        df["is_high_value"] = df["deal_value"] > threshold

        # Source tag
        df["data_source"] = "crm"

        print(f"[CRM Transform] {len(df)} rows, high-value threshold=${threshold:,.2f}")
        return df
