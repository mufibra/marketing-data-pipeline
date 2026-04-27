"""Social Media Extractor — generates synthetic social media metrics using Faker."""

import random
from datetime import datetime, timedelta

import pandas as pd
from faker import Faker

fake = Faker()

PLATFORMS = ["facebook", "instagram", "twitter", "linkedin", "tiktok"]
CAMPAIGN_TYPES = ["awareness", "consideration", "conversion", "retargeting"]

# Base ranges per platform for realistic variation
PLATFORM_PROFILES = {
    "facebook":  {"imp_range": (5000, 50000), "cpc_range": (0.30, 1.50), "conv_rate": 0.02},
    "instagram": {"imp_range": (3000, 40000), "cpc_range": (0.40, 2.00), "conv_rate": 0.025},
    "twitter":   {"imp_range": (2000, 25000), "cpc_range": (0.20, 1.20), "conv_rate": 0.012},
    "linkedin":  {"imp_range": (1000, 15000), "cpc_range": (1.50, 5.00), "conv_rate": 0.03},
    "tiktok":    {"imp_range": (8000, 80000), "cpc_range": (0.10, 0.80), "conv_rate": 0.018},
}

CAMPAIGN_CTR_MULTIPLIER = {
    "awareness": 0.8,
    "consideration": 1.0,
    "conversion": 1.3,
    "retargeting": 1.5,
}


class SocialExtractor:
    def __init__(self, seed: int = 42):
        Faker.seed(seed)
        random.seed(seed)

    def extract(self, start_date: str = "20210101", end_date: str = "20210131") -> pd.DataFrame:
        """Generate daily synthetic social media metrics for all platform/campaign combos."""
        start = datetime.strptime(start_date, "%Y%m%d").date()
        end = datetime.strptime(end_date, "%Y%m%d").date()

        rows = []
        current = start
        while current <= end:
            for platform in PLATFORMS:
                for campaign_type in CAMPAIGN_TYPES:
                    row = self._generate_row(current, platform, campaign_type)
                    rows.append(row)
            current += timedelta(days=1)

        df = pd.DataFrame(rows)
        print(f"[Social] Generated {len(df)} rows ({start_date} to {end_date})")
        return df

    def _generate_row(self, date, platform: str, campaign_type: str) -> dict:
        profile = PLATFORM_PROFILES[platform]
        ctr_mult = CAMPAIGN_CTR_MULTIPLIER[campaign_type]

        impressions = random.randint(*profile["imp_range"])
        base_ctr = random.uniform(0.01, 0.04) * ctr_mult
        clicks = int(impressions * base_ctr)
        ctr = round(clicks / impressions, 4) if impressions else 0
        cpc = round(random.uniform(*profile["cpc_range"]), 2)
        spend = round(clicks * cpc, 2)
        conversions = int(clicks * profile["conv_rate"] * random.uniform(0.5, 1.5))
        conversion_value = round(conversions * random.uniform(20, 150), 2)
        roas = round(conversion_value / spend, 2) if spend else 0

        return {
            "date": date,
            "platform": platform,
            "campaign_type": campaign_type,
            "campaign_name": f"{platform}_{campaign_type}_{date.strftime('%Y%m')}",
            "impressions": impressions,
            "clicks": clicks,
            "ctr": ctr,
            "cpc": cpc,
            "spend": spend,
            "conversions": conversions,
            "conversion_value": conversion_value,
            "roas": roas,
        }
