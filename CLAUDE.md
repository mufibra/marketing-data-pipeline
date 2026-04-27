# Marketing Data Pipeline + FastAPI API

## Project Overview
ETL pipeline: GA4/BigQuery (real data) + Social Media (synthetic via Faker) + CRM (synthetic CSV) -> BigQuery warehouse -> FastAPI REST API.

## Architecture
- src/extractors/ — data extraction from 3 sources
- src/validators/ — schema validation before loading
- src/transformers/ — data cleaning and enrichment
- src/loaders/ — BigQuery loading
- src/api/ — FastAPI REST endpoints
- src/pipeline.py — master pipeline orchestrator
- config/settings.py — environment config
- tests/ — test scripts

## Key Context
- GCP Project: galvanic-smoke-489914-u7
- BigQuery dataset: marketing_warehouse
- GA4 source: bigquery-public-data.ga4_obfuscated_sample_ecommerce.events_*
- Social + CRM data is synthetic (generated via Faker)
- Python 3.14, Windows CMD, venv at venv\Scripts\activate

## API Endpoints
- GET /api/v1/health — no auth
- GET /api/v1/metrics/daily — API key required
- GET /api/v1/channels/performance — API key required
- POST /api/v1/predict/attribution — API key required
- GET /api/v1/pipeline/status — API key required

## Commands
- Run pipeline: python -m src.pipeline
- Start API: uvicorn src.api.main:app --reload --port 8000
- Run tests: python tests/test_validators.py

## Rules
- Always use galvanic-smoke-489914-u7 as project ID, never env var placeholders
- .env holds secrets, never commit it
- All BigQuery tables go under marketing_warehouse dataset
- Pydantic models for all API request/response schemas
- API key auth via X-API-Key header
