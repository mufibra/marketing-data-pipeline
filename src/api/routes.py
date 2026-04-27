"""API routes — all endpoints under /api/v1."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from google.cloud import bigquery

from config.settings import GCP_PROJECT_ID, BQ_DATASET
from src.api.auth import require_api_key
from src.api.models import (
    AttributionPrediction,
    AttributionRequest,
    ChannelPerformance,
    ChannelPerformanceResponse,
    DailyMetric,
    DailyMetricsResponse,
    HealthResponse,
    PipelineStatus,
    TableStatus,
)

router = APIRouter(prefix="/api/v1")

DATASET_ID = f"{GCP_PROJECT_ID}.{BQ_DATASET}"


def _get_client() -> bigquery.Client:
    return bigquery.Client(project=GCP_PROJECT_ID)


# ── GET /health ──────────────────────────────────────────────────────────────

@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Check API health and BigQuery connectivity."""
    try:
        client = _get_client()
        tables = [t.table_id for t in client.list_tables(DATASET_ID)]
        return HealthResponse(
            status="healthy",
            bigquery_connected=True,
            tables_available=tables,
            timestamp=datetime.now(timezone.utc),
        )
    except Exception as e:
        return HealthResponse(
            status="degraded",
            bigquery_connected=False,
            tables_available=[],
            timestamp=datetime.now(timezone.utc),
        )


# ── GET /metrics/daily ───────────────────────────────────────────────────────

@router.get("/metrics/daily", response_model=DailyMetricsResponse,
            dependencies=[Depends(require_api_key)])
async def get_daily_metrics(
    start_date: str = Query(default="2021-01-01", description="Start date (YYYY-MM-DD)"),
    end_date: str = Query(default="2021-01-31", description="End date (YYYY-MM-DD)"),
    channel: str | None = Query(default=None, description="Filter by channel_grouping"),
):
    """Get daily session metrics from the ga4_sessions table."""
    client = _get_client()
    table = f"`{DATASET_ID}.ga4_sessions`"

    query = f"""
    SELECT date, channel_grouping, traffic_source, traffic_medium,
           unique_users, sessions, purchases, revenue,
           conversion_rate, revenue_per_session
    FROM {table}
    WHERE date BETWEEN '{start_date}' AND '{end_date}'
    """
    if channel:
        query += f"  AND channel_grouping = '{channel}'\n"
    query += "ORDER BY date"

    try:
        rows = list(client.query(query).result())
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"BigQuery error: {e}")

    data = [DailyMetric(**dict(row)) for row in rows]
    return DailyMetricsResponse(
        data=data,
        total_rows=len(data),
        start_date=start_date,
        end_date=end_date,
        channel_filter=channel,
    )


# ── GET /channels/performance ────────────────────────────────────────────────

@router.get("/channels/performance", response_model=ChannelPerformanceResponse,
            dependencies=[Depends(require_api_key)])
async def get_channel_performance():
    """Get aggregated performance metrics grouped by channel."""
    client = _get_client()
    table = f"`{DATASET_ID}.ga4_sessions`"

    query = f"""
    SELECT
        channel_grouping,
        SUM(sessions) AS total_sessions,
        SUM(revenue) AS total_revenue,
        SUM(purchases) AS total_purchases,
        SAFE_DIVIDE(SUM(purchases), SUM(sessions)) AS avg_conversion_rate,
        SAFE_DIVIDE(SUM(revenue), SUM(sessions)) AS revenue_per_session
    FROM {table}
    GROUP BY channel_grouping
    ORDER BY total_revenue DESC
    """

    try:
        rows = list(client.query(query).result())
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"BigQuery error: {e}")

    data = [
        ChannelPerformance(
            channel_grouping=row.channel_grouping,
            total_sessions=row.total_sessions or 0,
            total_revenue=round(row.total_revenue or 0, 2),
            total_purchases=row.total_purchases or 0,
            avg_conversion_rate=round(row.avg_conversion_rate or 0, 4),
            revenue_per_session=round(row.revenue_per_session or 0, 2),
        )
        for row in rows
    ]
    return ChannelPerformanceResponse(data=data, total_channels=len(data))


# ── POST /predict/attribution ────────────────────────────────────────────────

@router.post("/predict/attribution", response_model=AttributionPrediction,
             dependencies=[Depends(require_api_key)])
async def predict_attribution(request: AttributionRequest):
    """Simple linear prediction based on historical channel averages."""
    client = _get_client()
    table = f"`{DATASET_ID}.ga4_sessions`"

    # Get historical averages for the channel
    query = f"""
    SELECT
        SUM(sessions) AS total_sessions,
        SUM(revenue) AS total_revenue,
        COUNT(DISTINCT date) AS num_days
    FROM {table}
    WHERE channel_grouping = '{request.channel}'
    """

    try:
        rows = list(client.query(query).result())
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"BigQuery error: {e}")

    row = rows[0] if rows else None
    if not row or not row.total_sessions or not row.num_days:
        raise HTTPException(
            status_code=404,
            detail=f"No historical data for channel '{request.channel}'",
        )

    # Linear extrapolation: scale historical daily averages by budget ratio
    daily_sessions = row.total_sessions / row.num_days
    daily_revenue = row.total_revenue / row.num_days
    historical_daily_cost = daily_revenue * 0.3  # Assume 30% cost ratio as baseline

    if historical_daily_cost > 0:
        budget_ratio = (request.budget / request.period_days) / historical_daily_cost
    else:
        budget_ratio = 1.0

    predicted_sessions = int(daily_sessions * request.period_days * budget_ratio)
    predicted_revenue = round(daily_revenue * request.period_days * budget_ratio, 2)
    predicted_roas = round(predicted_revenue / request.budget, 2) if request.budget else 0

    return AttributionPrediction(
        channel=request.channel,
        budget=request.budget,
        period_days=request.period_days,
        predicted_sessions=predicted_sessions,
        predicted_revenue=predicted_revenue,
        predicted_roas=predicted_roas,
        confidence="low",
        model_type="linear_extrapolation",
    )


# ── GET /pipeline/status ─────────────────────────────────────────────────────

@router.get("/pipeline/status", response_model=PipelineStatus,
            dependencies=[Depends(require_api_key)])
async def get_pipeline_status():
    """List all tables with row counts and last modified timestamps."""
    client = _get_client()

    try:
        tables_iter = client.list_tables(DATASET_ID)
        tables = []
        total_rows = 0

        for table_ref in tables_iter:
            full_table = client.get_table(table_ref)
            tables.append(TableStatus(
                table_name=full_table.table_id,
                row_count=full_table.num_rows or 0,
                last_modified=full_table.modified,
            ))
            total_rows += full_table.num_rows or 0

        return PipelineStatus(
            dataset=BQ_DATASET,
            tables=tables,
            total_tables=len(tables),
            total_rows=total_rows,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"BigQuery error: {e}")
