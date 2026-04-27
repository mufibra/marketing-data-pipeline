"""Runner — executes all 3 extractors and returns a dict of DataFrames."""

import pandas as pd

from src.extractors.ga4_extractor import GA4Extractor
from src.extractors.social_extractor import SocialExtractor
from src.extractors.crm_extractor import CRMExtractor


def run_all_extractors(
    start_date: str = "20210101",
    end_date: str = "20210131",
) -> dict[str, pd.DataFrame]:
    """Run all extractors and return results as a dict of DataFrames."""
    results = {}

    # 1. GA4 (BigQuery)
    print("=" * 50)
    print("Running GA4 Extractor...")
    print("=" * 50)
    ga4 = GA4Extractor()
    results["ga4_sessions"] = ga4.extract_sessions(start_date, end_date)
    results["ga4_funnel"] = ga4.extract_funnel(start_date, end_date)

    # 2. Social Media (synthetic)
    print("=" * 50)
    print("Running Social Media Extractor...")
    print("=" * 50)
    social = SocialExtractor()
    results["social"] = social.extract(start_date, end_date)

    # 3. CRM (synthetic CSV)
    print("=" * 50)
    print("Running CRM Extractor...")
    print("=" * 50)
    crm = CRMExtractor()
    results["crm"] = crm.extract(start_date, end_date)

    print("=" * 50)
    print("All extractors complete.")
    for name, df in results.items():
        print(f"  {name}: {df.shape[0]} rows, {df.shape[1]} columns")
    print("=" * 50)

    return results


if __name__ == "__main__":
    run_all_extractors()
