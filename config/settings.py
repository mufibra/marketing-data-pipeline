import os
from dotenv import load_dotenv

load_dotenv()

GCP_PROJECT_ID = os.getenv("GCP_PROJECT_ID", "galvanic-smoke-489914-u7")
BQ_DATASET = os.getenv("BQ_DATASET", "marketing_warehouse")
API_KEY = os.getenv("API_KEY", "default-dev-key")
GA4_SOURCE_TABLE = os.getenv(
    "GA4_SOURCE_TABLE",
    "bigquery-public-data.ga4_obfuscated_sample_ecommerce.events_*",
)
