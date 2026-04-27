"""FastAPI application — Marketing Data Pipeline API."""

from datetime import datetime, timezone

from fastapi import FastAPI

from src.api.routes import router

app = FastAPI(
    title="Marketing Data Pipeline API",
    description="REST API for querying marketing analytics from the ETL pipeline warehouse.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.include_router(router)


@app.get("/")
async def root():
    """Service info and available endpoints."""
    return {
        "service": "Marketing Data Pipeline API",
        "version": "1.0.0",
        "docs": "/docs",
        "redoc": "/redoc",
        "endpoints": [
            {"method": "GET", "path": "/api/v1/health", "auth": False},
            {"method": "GET", "path": "/api/v1/metrics/daily", "auth": True},
            {"method": "GET", "path": "/api/v1/channels/performance", "auth": True},
            {"method": "POST", "path": "/api/v1/predict/attribution", "auth": True},
            {"method": "GET", "path": "/api/v1/pipeline/status", "auth": True},
        ],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
