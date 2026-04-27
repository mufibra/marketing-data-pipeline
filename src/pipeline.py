"""Master pipeline — orchestrates the full Extract → Validate → Transform → Load flow."""

import time
import uuid
from datetime import datetime, timezone

from src.extractors.runner import run_all_extractors
from src.validators.schema_validator import SchemaValidator
from src.transformers.ga4_transformer import GA4Transformer
from src.transformers.social_transformer import SocialTransformer
from src.transformers.crm_transformer import CRMTransformer
from src.loaders.bigquery_loader import BigQueryLoader


# Maps extractor output keys to (schema_name, transformer, bq_table_name)
PIPELINE_CONFIG = {
    "ga4_sessions": {
        "schema": "ga4_sessions",
        "transformer": GA4Transformer(),
        "table": "ga4_sessions",
    },
    "ga4_funnel": {
        "schema": "ga4_funnel",
        "transformer": None,  # Funnel data loaded as-is
        "table": "ga4_funnel",
    },
    "social": {
        "schema": "social",
        "transformer": SocialTransformer(),
        "table": "social_metrics",
    },
    "crm": {
        "schema": "crm",
        "transformer": CRMTransformer(),
        "table": "crm_contacts",
    },
}


def run_pipeline(start_date: str = "20210101", end_date: str = "20210131"):
    """Run the full ETL pipeline with timing and row counts."""
    run_id = str(uuid.uuid4())[:8]
    pipeline_start = time.time()
    start_ts = datetime.now(timezone.utc).isoformat()

    print("=" * 60)
    print(f"  PIPELINE RUN {run_id}")
    print(f"  Date range: {start_date} -> {end_date}")
    print("=" * 60)

    # ── EXTRACT ───────────────────────────────────────────────────
    print("\n[STEP 1/4] EXTRACT")
    print("-" * 60)
    t0 = time.time()
    raw_data = run_all_extractors(start_date, end_date)
    extract_time = time.time() - t0
    print(f"\nExtraction complete in {extract_time:.1f}s")
    for name, df in raw_data.items():
        print(f"  {name}: {len(df):,} rows")

    # ── VALIDATE ──────────────────────────────────────────────────
    print("\n[STEP 2/4] VALIDATE")
    print("-" * 60)
    t0 = time.time()
    validator = SchemaValidator()
    validation_failures = []

    for key, config in PIPELINE_CONFIG.items():
        if key not in raw_data:
            validation_failures.append(f"Missing expected data: {key}")
            continue

        result = validator.validate(raw_data[key], config["schema"])
        status = "PASS" if result.is_valid else "FAIL"
        print(f"  [{status}] {key} — {result.row_count:,} rows")

        for w in result.warnings:
            print(f"         WARN: {w}")
        for e in result.errors:
            print(f"         ERROR: {e}")

        if not result.is_valid:
            validation_failures.append(f"{key}: {'; '.join(result.errors)}")

    validate_time = time.time() - t0
    print(f"\nValidation complete in {validate_time:.1f}s")

    if validation_failures:
        print("\nPIPELINE ABORTED — validation errors:")
        for f in validation_failures:
            print(f"  - {f}")
        _log_metadata(run_id, start_ts, pipeline_start, "failed",
                      error="; ".join(validation_failures))
        return

    # ── TRANSFORM ─────────────────────────────────────────────────
    print("\n[STEP 3/4] TRANSFORM")
    print("-" * 60)
    t0 = time.time()
    transformed = {}

    for key, config in PIPELINE_CONFIG.items():
        transformer = config["transformer"]
        if transformer is not None:
            transformed[key] = transformer.transform(raw_data[key])
        else:
            transformed[key] = raw_data[key].copy()
            print(f"[{key}] No transformation needed, passing through")

    transform_time = time.time() - t0
    print(f"\nTransformation complete in {transform_time:.1f}s")
    for name, df in transformed.items():
        print(f"  {name}: {len(df):,} rows, {len(df.columns)} cols")

    # ── LOAD ──────────────────────────────────────────────────────
    print("\n[STEP 4/4] LOAD")
    print("-" * 60)
    t0 = time.time()
    loader = BigQueryLoader()
    loader.ensure_dataset()

    total_rows = 0
    tables_loaded = 0

    for key, config in PIPELINE_CONFIG.items():
        rows_loaded = loader.load_table(transformed[key], config["table"])
        total_rows += rows_loaded
        tables_loaded += 1

    load_time = time.time() - t0
    print(f"\nLoading complete in {load_time:.1f}s")
    print(f"  Tables loaded: {tables_loaded}")
    print(f"  Total rows: {total_rows:,}")

    # ── METADATA ──────────────────────────────────────────────────
    _log_metadata(run_id, start_ts, pipeline_start, "success",
                  tables_loaded=tables_loaded, total_rows=total_rows)

    # ── SUMMARY ───────────────────────────────────────────────────
    total_time = time.time() - pipeline_start
    print("\n" + "=" * 60)
    print("  PIPELINE COMPLETE")
    print("=" * 60)
    print(f"  Run ID:     {run_id}")
    print(f"  Extract:    {extract_time:.1f}s")
    print(f"  Validate:   {validate_time:.1f}s")
    print(f"  Transform:  {transform_time:.1f}s")
    print(f"  Load:       {load_time:.1f}s")
    print(f"  Total:      {total_time:.1f}s")
    print(f"  Tables:     {tables_loaded}")
    print(f"  Rows:       {total_rows:,}")
    print("=" * 60)


def _log_metadata(run_id, start_ts, pipeline_start, status,
                  error=None, tables_loaded=0, total_rows=0):
    """Log pipeline run metadata to BigQuery."""
    total_time = time.time() - pipeline_start
    metadata = {
        "run_id": run_id,
        "start_time": start_ts,
        "end_time": datetime.now(timezone.utc).isoformat(),
        "duration_seconds": round(total_time, 2),
        "status": status,
        "tables_loaded": tables_loaded,
        "total_rows_loaded": total_rows,
        "error_message": error,
    }
    try:
        loader = BigQueryLoader()
        loader.log_pipeline_metadata(metadata)
    except Exception as e:
        print(f"[WARNING] Failed to log metadata: {e}")


if __name__ == "__main__":
    run_pipeline()
