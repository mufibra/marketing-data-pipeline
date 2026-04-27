"""Social Transformer — enriches social media metrics with derived columns."""

import pandas as pd


class SocialTransformer:
    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """Standardize dates and add derived metrics."""
        df = df.copy()

        # Standardize date to datetime
        df["date"] = pd.to_datetime(df["date"])

        # Cost per conversion (avoid division by zero)
        df["cost_per_conversion"] = (
            df["spend"] / df["conversions"].replace(0, float("nan"))
        ).fillna(0).round(2)

        # Efficiency score
        df["efficiency_score"] = (df["roas"] * df["ctr"] * 100).round(4)

        # Source tag
        df["data_source"] = "social"

        print(f"[Social Transform] {len(df)} rows, added cost_per_conversion + efficiency_score")
        return df
