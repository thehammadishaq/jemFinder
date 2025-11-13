"""
Finnhub Service
Service to fetch company data using Finnhub API
"""
import requests
import asyncio
from typing import Dict, Optional, Any
from datetime import datetime, timedelta
from config.settings import settings
import os

FINNHUB_API_KEY = settings.FINNHUB_API_KEY if hasattr(settings, 'FINNHUB_API_KEY') else os.getenv("FINNHUB_API_KEY")
BASE_URL = "https://finnhub.io/api/v1"


def safe_get_sync(url: str, params: Optional[Dict] = None, retries: int = 2) -> Optional[Dict]:
    """Synchronously make an API request with retry logic and return JSON, or None on error."""
    import time
    
    for attempt in range(retries + 1):
        try:
            # Increase timeout to 60 seconds and add connection timeout
            response = requests.get(
                url, 
                params=params, 
                timeout=(10, 60),  # (connect_timeout, read_timeout)
                headers={'User-Agent': 'Mozilla/5.0'}
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.Timeout as e:
            if attempt < retries:
                wait_time = (attempt + 1) * 2  # Exponential backoff: 2s, 4s
                print(f"⚠️ Finnhub API timeout (attempt {attempt + 1}/{retries + 1}) for {url.split('?')[0]}, retrying in {wait_time}s...")
                time.sleep(wait_time)
                continue
            else:
                print(f"⚠️ Finnhub API request failed after {retries + 1} attempts for {url.split('?')[0]}: {e}")
                return None
        except requests.exceptions.RequestException as e:
            if attempt < retries and "timeout" in str(e).lower():
                wait_time = (attempt + 1) * 2
                print(f"⚠️ Finnhub API error (attempt {attempt + 1}/{retries + 1}) for {url.split('?')[0]}, retrying in {wait_time}s...")
                time.sleep(wait_time)
                continue
            else:
                print(f"⚠️ Finnhub API request failed for {url.split('?')[0]}: {type(e).__name__}")
                return None
    
    return None


async def get_all_finnhub_data(symbol: str) -> Optional[Dict]:
    """
    Fetch ALL available data from Finnhub API for a given symbol.
    Returns data directly with API response keys (Company Profile, Basic Financials, etc.)
    """
    if not FINNHUB_API_KEY:
        print("❌ FINNHUB_API_KEY not configured in settings.")
        return None

    loop = asyncio.get_event_loop()
    all_data = {}

    # Define all fetch functions
    def fetch_company_profile():
        url = f"{BASE_URL}/stock/profile2"
        return safe_get_sync(url, params={"symbol": symbol, "token": FINNHUB_API_KEY})

    def fetch_basic_financials():
        url = f"{BASE_URL}/stock/metric"
        return safe_get_sync(url, params={"symbol": symbol, "metric": "all", "token": FINNHUB_API_KEY})

    def fetch_earnings_surprises():
        url = f"{BASE_URL}/stock/earnings"
        return safe_get_sync(url, params={"symbol": symbol, "token": FINNHUB_API_KEY})

    def fetch_financials_reported():
        url = f"{BASE_URL}/stock/financials-reported"
        return safe_get_sync(url, params={"symbol": symbol, "token": FINNHUB_API_KEY})

    def fetch_insider_transactions():
        url = f"{BASE_URL}/stock/insider-transactions"
        return safe_get_sync(url, params={"symbol": symbol, "token": FINNHUB_API_KEY})

    # For date-based endpoints, use last 1 year
    to_date = datetime.now().strftime("%Y-%m-%d")
    from_date = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")

    def fetch_company_news():
        url = f"{BASE_URL}/company-news"
        return safe_get_sync(url, params={
            "symbol": symbol,
            "from": from_date,
            "to": to_date,
            "token": FINNHUB_API_KEY
        })

    def fetch_insider_sentiment():
        url = f"{BASE_URL}/stock/insider-sentiment"
        return safe_get_sync(url, params={
            "symbol": symbol,
            "from": from_date,
            "to": to_date,
            "token": FINNHUB_API_KEY
        })

    # For IPO Calendar - use last 3 months and next 3 months
    ipo_from = (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d")
    ipo_to = (datetime.now() + timedelta(days=90)).strftime("%Y-%m-%d")

    def fetch_ipo_calendar():
        url = f"{BASE_URL}/calendar/ipo"
        return safe_get_sync(url, params={
            "from": ipo_from,
            "to": ipo_to,
            "token": FINNHUB_API_KEY
        })

    # For Earnings Calendar - use last 1 month and next 1 month
    earnings_from = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    earnings_to = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")

    def fetch_earnings_calendar():
        url = f"{BASE_URL}/calendar/earnings"
        return safe_get_sync(url, params={
            "symbol": symbol,
            "from": earnings_from,
            "to": earnings_to,
            "token": FINNHUB_API_KEY
        })

    # Fetch data with delays to avoid rate limiting
    # Group requests: critical first, then others with delays
    import time
    
    # Fetch critical data first (Company Profile)
    print(f"📊 Fetching Company Profile from Finnhub...")
    company_profile = await loop.run_in_executor(None, fetch_company_profile)
    await asyncio.sleep(0.5)  # Small delay between requests
    
    # Fetch other data in smaller batches to avoid overwhelming the API
    print(f"📊 Fetching financial data from Finnhub...")
    batch1 = await asyncio.gather(
        loop.run_in_executor(None, fetch_basic_financials),
        loop.run_in_executor(None, fetch_earnings_surprises),
        loop.run_in_executor(None, fetch_financials_reported),
        return_exceptions=True
    )
    await asyncio.sleep(0.5)
    
    print(f"📊 Fetching insider and news data from Finnhub...")
    batch2 = await asyncio.gather(
        loop.run_in_executor(None, fetch_insider_transactions),
        loop.run_in_executor(None, fetch_company_news),
        loop.run_in_executor(None, fetch_insider_sentiment),
        return_exceptions=True
    )
    await asyncio.sleep(0.5)
    
    print(f"📊 Fetching calendar data from Finnhub...")
    batch3 = await asyncio.gather(
        loop.run_in_executor(None, fetch_ipo_calendar),
        loop.run_in_executor(None, fetch_earnings_calendar),
        return_exceptions=True
    )
    
    # Combine results
    (
        basic_financials,
        earnings_surprises,
        financials_reported,
        insider_transactions,
        company_news,
        insider_sentiment,
        ipo_calendar,
        earnings_calendar
    ) = (*batch1, *batch2, *batch3)

    # Store all fetched data
    if company_profile and not isinstance(company_profile, Exception):
        all_data["Company Profile"] = company_profile

    if basic_financials and not isinstance(basic_financials, Exception):
        all_data["Basic Financials"] = basic_financials

    if earnings_surprises and not isinstance(earnings_surprises, Exception):
        all_data["Earnings Surprises"] = earnings_surprises

    if financials_reported and not isinstance(financials_reported, Exception):
        all_data["Financials As Reported"] = financials_reported

    if insider_transactions and not isinstance(insider_transactions, Exception):
        all_data["Insider Transactions"] = insider_transactions

    if company_news and not isinstance(company_news, Exception):
        all_data["Company News"] = company_news

    if insider_sentiment and not isinstance(insider_sentiment, Exception):
        all_data["Insider Sentiment"] = insider_sentiment

    if ipo_calendar and not isinstance(ipo_calendar, Exception):
        all_data["IPO Calendar"] = ipo_calendar

    if earnings_calendar and not isinstance(earnings_calendar, Exception):
        all_data["Earnings Calendar"] = earnings_calendar

    # Add metadata (optional, can be used for debugging)
    all_data["_metadata"] = {
        "symbol": symbol,
        "fetched_at": datetime.now().isoformat(),
        "data_sections": list(all_data.keys()),
        "api_source": "Finnhub"
    }

    # Return data directly without wrapping in "What" and "Sources"
    # This allows the frontend to create dynamic buttons from the actual API response keys
    return all_data if all_data else None

