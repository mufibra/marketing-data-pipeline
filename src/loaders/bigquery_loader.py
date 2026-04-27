"""BigQuery Loader — loads transformed DataFrames into BigQuery tables."""

from datetime import datetime, timezone

from google.cloud import bigquery
from google.cloud.exceptions import NotFound
import pandas as pd

from config.settings import GCP_PROJECT_ID, BQ_DATASET


class BigQueryLoader:
    def __init__(self):
        self.client = bigquery.Client(project=GCP_PROJECT_ID)
        self.dataset_id = f"{GCP_PROJECT_ID}.{BQ_DATASET}"

    def ensure_dataset(self):
        """Create the dataset if it doesn't exist."""
        dataset = bigquery.Dataset(self.dataset_id)
        dataset.location = "US"
        try:
            self.client.get_dataset(self.dataset_id)
            print(f"[Loader] Dataset {self.dataset_id} already exists")
        except NotFound:
            self.client.create_dataset(dataset, exists_ok=True)
            print(f"[Loader] Created dataset {self.dataset_id}")

    def load_table(self, df: pd.DataFrame, table_name: str) -> int:
        """Load a DataFrame into a BigQuery table (WRITE_TRUNCATE)."""
        table_id = f"{self.dataset_id}.{table_name}"

        job_config = bigquery.LoadJobConfig(
            write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
            autodetect=True,
        )

        job = self.client.load_table_from_dataframe(df, table_id, job_config=job_config)
        job.result()  # Wait for completion

        loaded = self.client.get_table(table_id).num_rows
        print(f"[Loader] Loaded {loaded} rows -> {table_id}")
        return loaded

    def log_pipeline_metadata(self, metadata: dict):
        """Log pipeline run metadata to a dedicated table."""
        table_id = f"{self.dataset_id}.pipeline_metadata"

        row = {
            "run_id": metadata.get("run_id", "unknown"),
            "start_time": metadata.get("start_time"),
            "end_time": metadata.get("end_time"),
            "duration_seconds": metadata.get("duration_seconds", 0),
            "status": metadata.get("status", "unknown"),
            "tables_loaded": metadata.get("tables_loaded", 0),
            "total_rows_loaded": metadata.get("total_rows_loaded", 0),
            "error_message": metadata.get("error_message"),
            "logged_at": datetime.now(timezone.utc).isoformat(),
        }

        df = pd.DataFrame([row])

        job_config = bigquery.LoadJobConfig(
            write_disposition=bigquery.WriteDisposition.WRITE_APPEND,
            autodetect=True,
        )

        job = self.client.load_table_from_dataframe(df, table_id, job_config=job_config)
        job.result()
        print(f"[Loader] Pipeline metadata logged -> {table_id}")
