"""Pydantic models for API request/response schemas."""

from datetime import date, datetime
from pydantic import BaseModel, Field


# ── Health ────────────────────────────────────────────────────────────────────

class HealthResponse(BaseModel):
    status: str = "healthy"
    bigquery_connected: bool
    tables_available: list[str] = []
    timestamp: datetime


# ── Daily Metrics ─────────────────────────────────────────────────────────────

class DailyMetric(BaseModel):
    date: date
    channel_grouping: str
    traffic_source: str | None = None
    traffic_medium: str | None = None
    unique_users: int
    sessions: int
    purchases: int
    revenue: float
    conversion_rate: float
    revenue_per_session: float


class DailyMetricsResponse(BaseModel):
    data: list[DailyMetric]
    total_rows: int
    start_date: str
    end_date: str
    channel_filter: str | None = None


# ── Channel Performance ──────────────────────────────────────────────────────

class ChannelPerformance(BaseModel):
    channel_grouping: str
    total_sessions: int
    total_revenue: float
    total_purchases: int
    avg_conversion_rate: float
    revenue_per_session: float


class ChannelPerformanceResponse(BaseModel):
    data: list[ChannelPerformance]
    total_channels: int


# ── Attribution Prediction ───────────────────────────────────────────────────

class AttributionRequest(BaseModel):
    channel: str = Field(..., description="Channel to predict for (e.g. paid_search, social)")
    budget: float = Field(..., gt=0, description="Budget to allocate")
    period_days: int = Field(default=30, gt=0, description="Prediction period in days")


class AttributionPrediction(BaseModel):
    channel: str
    budget: float
    period_days: int
    predicted_sessions: int
    predicted_revenue: float
    predicted_roas: float
    confidence: str = "low"
    model_type: str = "linear_extrapolation"


# ── Pipeline Status ──────────────────────────────────────────────────────────

class TableStatus(BaseModel):
    table_name: str
    row_count: int
    last_modified: datetime | None = None


class PipelineStatus(BaseModel):
    dataset: str
    tables: list[TableStatus]
    total_tables: int
    total_rows: int
