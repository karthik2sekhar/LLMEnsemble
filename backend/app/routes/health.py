"""
Health check routes for monitoring and status.
"""

from datetime import datetime

from fastapi import APIRouter

from ..config import get_settings
from ..schemas import HealthResponse

router = APIRouter(tags=["health"])
settings = get_settings()

# Application version
VERSION = "1.0.0"


@router.get("/api/health", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint.
    
    Returns the current status of the application including:
    - Overall status
    - Current timestamp
    - Application version
    - Configuration status
    """
    return HealthResponse(
        status="healthy",
        timestamp=datetime.utcnow(),
        version=VERSION,
        api_key_configured=settings.validate_api_key(),
        cache_enabled=settings.cache_enabled,
    )


@router.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": "LLM Ensemble API",
        "version": VERSION,
        "description": "Query multiple LLMs in parallel and synthesize responses",
        "docs": "/docs",
        "health": "/api/health",
    }
