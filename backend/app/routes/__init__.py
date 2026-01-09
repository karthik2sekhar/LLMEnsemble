"""
Routes package initialization.
"""

from .ensemble import router as ensemble_router
from .health import router as health_router

__all__ = ["ensemble_router", "health_router"]
