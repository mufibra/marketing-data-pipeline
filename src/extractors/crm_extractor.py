"""CRM Extractor — generates 500 synthetic CRM contacts and saves to CSV."""

import os
import random
from datetime import datetime, timedelta

import pandas as pd
from faker import Faker

fake = Faker()

INDUSTRIES = [
    "Technology", "Healthcare", "Finance", "Retail", "Manufacturing",
    "Education", "Real Estate", "Media", "Consulting", "Energy",
]

LEAD_SOURCES = [
    "organic_search", "paid_search", "social_media", "email_campaign",
    "referral", "webinar", "trade_show", "content_download",
]

# Realistic funnel weights — most contacts are early-stage
LIFECYCLE_STAGES = ["lead", "mql", "sql", "opportunity", "customer", "churned"]
LIFECYCLE_WEIGHTS = [0.30, 0.25, 0.18, 0.12, 0.10, 0.05]

OUTPUT_PATH = os.path.join("data", "raw", "crm_export.csv")


class CRMExtractor:
    def __init__(self, num_contacts: int = 500, seed: int = 42):
        self.num_contacts = num_contacts
        Faker.seed(seed)
        random.seed(seed)

    def extract(self, start_date: str = "20210101", end_date: str = "20210131") -> pd.DataFrame:
        """Generate synthetic CRM contacts and save to CSV."""
        start = datetime.strptime(start_date, "%Y%m%d").date()
        end = datetime.strptime(end_date, "%Y%m%d").date()
        date_range_days = (end - start).days

        rows = []
        for i in range(1, self.num_contacts + 1):
            created = start + timedelta(days=random.randint(0, date_range_days))
            days_since_created = (end - created).days
            last_activity = created + timedelta(days=random.randint(0, max(days_since_created, 0)))

            stage = random.choices(LIFECYCLE_STAGES, weights=LIFECYCLE_WEIGHTS, k=1)[0]
            deal_value = self._deal_value_for_stage(stage)

            rows.append({
                "contact_id": f"CRM-{i:05d}",
                "email": fake.unique.email(),
                "company": fake.company(),
                "industry": random.choice(INDUSTRIES),
                "lead_source": random.choice(LEAD_SOURCES),
                "lifecycle_stage": stage,
                "created_date": created,
                "last_activity_date": last_activity,
                "deal_value": deal_value,
                "num_touches": random.randint(1, 30),
                "email_opens": random.randint(0, 50),
                "page_views": random.randint(1, 200),
            })

        df = pd.DataFrame(rows)

        os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
        df.to_csv(OUTPUT_PATH, index=False)
        print(f"[CRM] Generated {len(df)} contacts -> {OUTPUT_PATH}")
        return df

    @staticmethod
    def _deal_value_for_stage(stage: str) -> float:
        """Higher-stage contacts tend to have larger deal values."""
        ranges = {
            "lead": (0, 0),
            "mql": (0, 5000),
            "sql": (1000, 25000),
            "opportunity": (5000, 75000),
            "customer": (10000, 150000),
            "churned": (0, 50000),
        }
        low, high = ranges[stage]
        return round(random.uniform(low, high), 2)
