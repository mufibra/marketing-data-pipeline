"""GA4 Transformer — standardizes and enriches GA4 session data."""

import pandas as pd


CHANNEL_RULES = {
    "paid_search": lambda s, m: m in ("cpc", "ppc", "paid search", "paidsearch"),
    "organic_search": lambda s, m: m in ("organic",),
    "social": lambda s, m: m in ("social", "social-network", "sm")
        or s in ("facebook", "instagram", "twitter", "linkedin", "tiktok", "youtube"),
    "email": lambda s, m: m in ("email", "e-mail"),
    "referral": lambda s, m: m in ("referral",),
    "direct": lambda s, m: s == "(direct)" and m == "(none)",
}


def _classify_channel(source: str, medium: str) -> str:
    s = str(source).lower().strip()
    m = str(medium).lower().strip()
    for channel, rule in CHANNEL_RULES.items():
        if rule(s, m):
            return channel
    return "other"


class GA4Transformer:
    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """Standardize and enrich GA4 session data."""
        df = df.copy()

        # Rename session_date -> date
        df.rename(columns={"session_date": "date"}, inplace=True)

        # Fill nulls in traffic dimensions
        df["traffic_source"].fillna("(direct)", inplace=True)
        df["traffic_medium"].fillna("(none)", inplace=True)
        df["campaign_name"].fillna("(not set)", inplace=True)

        # Channel grouping
        df["channel_grouping"] = df.apply(
            lambda r: _classify_channel(r["traffic_source"], r["traffic_medium"]),
            axis=1,
        )

        # Derived metrics
        df["conversion_rate"] = (df["purchases"] / df["sessions"]).fillna(0).round(4)
        df["revenue_per_session"] = (df["revenue"] / df["sessions"]).fillna(0).round(2)

        # Source tag
        df["data_source"] = "ga4"

        print(f"[GA4 Transform] {len(df)} rows, added channel_grouping + derived metrics")
        return df
