"""
Polygon.io Service
Service to fetch company profile data using Polygon.io API
"""
import requests
import asyncio
from typing import Dict, Optional, Any
from config.settings import settings
import os

POLYGON_API_KEY = settings.POLYGON_API_KEY or os.getenv("POLYGON_API_KEY")
VERBOSE = (os.getenv("VERBOSE", "false") or "false").lower() in ("1", "true", "yes", "y")


def debug(*args, **kwargs):
    if VERBOSE:
        print(*args, **kwargs)


def safe_get(url: str, params: Optional[Dict] = None) -> Optional[Dict]:
    """Safely make API request"""
    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        debug(f"⚠️ API request failed: {type(e).__name__}: {e}")
        return None


async def get_company_profile_from_polygon(symbol: str) -> Optional[Dict]:
    """
    Fetch ALL data from Polygon.io (complete data like polygonFundamentals.py)
    Returns data directly with API response keys (Ticker Details, Company Info, etc.)
    """
    if not POLYGON_API_KEY:
        debug("⚠️ POLYGON_API_KEY not found in settings or .env file")
        return None
    
    base_url = "https://api.polygon.io"
    all_data = {}
    
    # Run API calls in executor (requests is synchronous)
    loop = asyncio.get_event_loop()
    
    # Define all fetch functions
    def fetch_ticker_details():
        ticker_url = f"{base_url}/v3/reference/tickers/{symbol}"
        return safe_get(ticker_url, params={"apiKey": POLYGON_API_KEY})
    
    def fetch_financials_annual():
        fundamentals_url = f"{base_url}/vX/reference/financials"
        return safe_get(fundamentals_url, params={
            "ticker": symbol,
            "apiKey": POLYGON_API_KEY,
            "timeframe": "annual",
            "limit": 10
        })
    
    def fetch_financials_quarterly():
        fundamentals_url = f"{base_url}/vX/reference/financials"
        return safe_get(fundamentals_url, params={
            "ticker": symbol,
            "apiKey": POLYGON_API_KEY,
            "timeframe": "quarterly",
            "limit": 10
        })
    
    def fetch_dividends():
        dividends_url = f"{base_url}/v2/reference/dividends/{symbol}"
        return safe_get(dividends_url, params={"apiKey": POLYGON_API_KEY})
    
    def fetch_splits():
        splits_url = f"{base_url}/v2/reference/splits/{symbol}"
        return safe_get(splits_url, params={"apiKey": POLYGON_API_KEY})
    
    def fetch_news():
        news_url = f"{base_url}/v2/reference/news"
        return safe_get(news_url, params={
            "ticker": symbol,
            "apiKey": POLYGON_API_KEY,
            "limit": 10
        })
    
    def fetch_market_status():
        market_status_url = f"{base_url}/v1/marketstatus/now"
        return safe_get(market_status_url, params={"apiKey": POLYGON_API_KEY})
    
    def fetch_previous_close():
        prev_close_url = f"{base_url}/v2/aggs/ticker/{symbol}/prev"
        return safe_get(prev_close_url, params={"apiKey": POLYGON_API_KEY})
    
    # Fetch all data in parallel
    results = await asyncio.gather(
        loop.run_in_executor(None, fetch_ticker_details),
        loop.run_in_executor(None, fetch_financials_annual),
        loop.run_in_executor(None, fetch_financials_quarterly),
        loop.run_in_executor(None, fetch_dividends),
        loop.run_in_executor(None, fetch_splits),
        loop.run_in_executor(None, fetch_news),
        loop.run_in_executor(None, fetch_market_status),
        loop.run_in_executor(None, fetch_previous_close),
        return_exceptions=True
    )
    
    ticker_data, financials_annual, financials_quarterly, dividends_data, splits_data, news_data, market_status, prev_close = results
    
    # Store all fetched data
    if ticker_data and not isinstance(ticker_data, Exception):
        all_data["Ticker Details"] = ticker_data
        
        # Extract Company Info from ticker details
        if "results" in ticker_data:
            ticker_info = ticker_data.get("results", {})
            all_data["Company Info"] = {
                "Name": ticker_info.get("name"),
                "Description": ticker_info.get("description"),
                "Ticker": ticker_info.get("ticker"),
                "Market": ticker_info.get("market"),
                "Locale": ticker_info.get("locale"),
                "Primary Exchange": ticker_info.get("primary_exchange"),
                "Type": ticker_info.get("type"),
                "Active": ticker_info.get("active"),
                "Currency": ticker_info.get("currency_name"),
                "CIK": ticker_info.get("cik"),
                "Composite FIGI": ticker_info.get("composite_figi"),
                "Share Class FIGI": ticker_info.get("share_class_figi"),
                "Last Updated UTC": ticker_info.get("last_updated_utc"),
                "Delisted UTC": ticker_info.get("delisted_utc"),
            }
    
    if financials_annual and not isinstance(financials_annual, Exception):
        all_data["Financials Annual"] = financials_annual
    
    if financials_quarterly and not isinstance(financials_quarterly, Exception):
        all_data["Financials Quarterly"] = financials_quarterly
    
    if dividends_data and not isinstance(dividends_data, Exception):
        all_data["Dividends"] = dividends_data
    
    if splits_data and not isinstance(splits_data, Exception):
        all_data["Splits"] = splits_data
    
    if news_data and not isinstance(news_data, Exception):
        all_data["News"] = news_data
    
    if market_status and not isinstance(market_status, Exception):
        all_data["Market Status"] = market_status
    
    if prev_close and not isinstance(prev_close, Exception):
        all_data["Previous Close"] = prev_close
    
    # Return data directly without wrapping in "What" and "Sources"
    # This allows the frontend to create dynamic buttons from the actual API response keys
    return all_data if all_data else None

