"""Routes module"""
from fastapi import APIRouter
from .company_profile_routes import router as company_profile_router
from .gemini_routes import router as gemini_router
from .fundamentals_routes import router as fundamentals_router
from .polygon_routes import router as polygon_router
from .finnhub_routes import router as finnhub_router
from .yfinance_routes import router as yfinance_router

# Create main API router
api_router = APIRouter()

# Include all route modules
api_router.include_router(company_profile_router)
api_router.include_router(gemini_router)
api_router.include_router(fundamentals_router)
api_router.include_router(polygon_router)
api_router.include_router(finnhub_router)
api_router.include_router(yfinance_router)

__all__ = ["api_router"]

