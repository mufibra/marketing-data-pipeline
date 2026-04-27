"""GA4 Extractor — queries BigQuery public GA4 dataset for session and funnel metrics."""

from google.cloud import bigquery
import pandas as pd

from config.settings import GCP_PROJECT_ID, GA4_SOURCE_TABLE


class GA4Extractor:
    def __init__(self):
        self.client = bigquery.Client(project=GCP_PROJECT_ID)
        self.source_table = GA4_SOURCE_TABLE

    def extract_sessions(self, start_date: str = "20210101", end_date: str = "20210131") -> pd.DataFrame:
        """Extract session-level metrics aggregated by date, source, medium, campaign."""
        query = f"""
        SELECT
            PARSE_DATE('%Y%m%d', event_date) AS session_date,
            collected_traffic_source.manual_source AS traffic_source,
            collected_traffic_source.manual_medium AS traffic_medium,
            collected_traffic_source.manual_campaign_name AS campaign_name,
            COUNT(DISTINCT user_pseudo_id) AS unique_users,
            COUNT(DISTINCT CONCAT(user_pseudo_id, '-',
                (SELECT value.int_value FROM UNNEST(event_params) WHERE key = 'ga_session_id'))
            ) AS sessions,
            COUNTIF(event_name = 'purchase') AS purchases,
            SUM(ecommerce.purchase_revenue) AS revenue
        FROM `{self.source_table}`
        WHERE event_date BETWEEN '{start_date}' AND '{end_date}'
        GROUP BY session_date, traffic_source, traffic_medium, campaign_name
        ORDER BY session_date
        """
        print(f"[GA4] Querying sessions from {start_date} to {end_date}...")
        df = self.client.query(query).to_dataframe()
        print(f"[GA4] Sessions extracted: {len(df)} rows")
        return df

    def extract_funnel(self, start_date: str = "20210101", end_date: str = "20210131") -> pd.DataFrame:
        """Extract event-level funnel data for key e-commerce events."""
        funnel_events = [
            "session_start",
            "page_view",
            "view_item",
            "add_to_cart",
            "begin_checkout",
            "purchase",
        ]
        events_list = ", ".join(f"'{e}'" for e in funnel_events)

        query = f"""
        SELECT
            PARSE_DATE('%Y%m%d', event_date) AS event_date,
            event_name,
            COUNT(*) AS event_count,
            COUNT(DISTINCT user_pseudo_id) AS unique_users
        FROM `{self.source_table}`
        WHERE event_date BETWEEN '{start_date}' AND '{end_date}'
          AND event_name IN ({events_list})
        GROUP BY event_date, event_name
        ORDER BY event_date, event_count DESC
        """
        print(f"[GA4] Querying funnel events from {start_date} to {end_date}...")
        df = self.client.query(query).to_dataframe()
        print(f"[GA4] Funnel events extracted: {len(df)} rows")
        return df
