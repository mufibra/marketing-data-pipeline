"""API key authentication via X-API-Key header."""

from fastapi import Depends, HTTPException, Security
from fastapi.security import APIKeyHeader

from config.settings import API_KEY

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def require_api_key(api_key: str = Security(api_key_header)) -> str:
    """Validate the API key from the X-API-Key header."""
    if api_key is None:
        raise HTTPException(status_code=401, detail="Missing API key — set X-API-Key header")
    if api_key != API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API key")
    return api_key
