"""
Yahoo Finance Service
Service to fetch company data using yfinance library
"""
import yfinance as yf
import pandas as pd
import asyncio
from typing import Dict, Optional
import os
import warnings
from contextlib import contextmanager
from config.settings import settings
import requests
import json
from datetime import datetime

# Suppress yfinance deprecation warnings
warnings.filterwarnings('ignore', category=DeprecationWarning)

VERBOSE = (os.getenv("VERBOSE", "false") or "false").lower() in ("1", "true", "yes", "y")

# Get proxy servers from settings
PROXY_SERVER = settings.PROXY_SERVER or os.getenv("PROXY_SERVER")
PROXY_SERVERS_STR = settings.PROXY_SERVERS or os.getenv("PROXY_SERVERS")

# Parse proxy servers list
PROXY_SERVERS_LIST = []
if PROXY_SERVERS_STR:
    # Parse comma-separated proxy list
    PROXY_SERVERS_LIST = [p.strip() for p in PROXY_SERVERS_STR.split(',') if p.strip()]
elif PROXY_SERVER:
    # If only single proxy, use it as list
    PROXY_SERVERS_LIST = [PROXY_SERVER]

# Proxy rotation index (thread-safe using threading.local or simple counter)
_proxy_index = 0
import threading
_proxy_lock = threading.Lock()


def debug(*args, **kwargs):
    if VERBOSE:
        print(*args, **kwargs)


def save_response_to_file(symbol: str, section_name: str, data: any):
    """Save response data to a JSON file"""
    try:
        # Get the backend directory (parent of services)
        backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        # Create responses directory in project root
        responses_dir = os.path.join(backend_dir, "..", "yfinance_responses")
        responses_dir = os.path.abspath(responses_dir)
        
        if not os.path.exists(responses_dir):
            os.makedirs(responses_dir)
        
        # Create filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        # Clean section name for filename
        clean_section = section_name.replace(" ", "_").replace("/", "_").replace("(", "").replace(")", "").replace("_New_", "_New")
        filename = os.path.join(responses_dir, f"{symbol}_{clean_section}_{timestamp}.json")
        
        # Prepare data to save
        response_data = {
            "symbol": symbol,
            "section": section_name,
            "timestamp": timestamp,
            "data": data
        }
        
        # Save to file
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(response_data, f, indent=2, default=str, ensure_ascii=False)
        
        print(f"💾 Saved response to: {filename}")
    except Exception as e:
        print(f"⚠️ Failed to save response to file: {e}")


def safe_get_data(func, default=None, symbol=None, section_name=None):
    """Safely execute a function and return default on error"""
    try:
        result = func()
        # Save response to file if symbol and section_name provided
        if symbol and section_name:
            save_response_to_file(symbol, section_name, result)
        return result
    except Exception as e:
        debug(f"⚠️ Data fetch failed: {type(e).__name__}: {e}")
        # Save error to file as well
        if symbol and section_name:
            save_response_to_file(symbol, f"{section_name}_ERROR", {"error": str(e), "error_type": type(e).__name__})
        return default


def get_current_ip(proxy_url: Optional[str] = None) -> Optional[str]:
    """Get current public IP address to verify proxy usage"""
    try:
        # Get proxy from parameter or environment
        proxies = None
        if proxy_url:
            proxies = {
                'http': proxy_url,
                'https': proxy_url
            }
        else:
            http_proxy = os.environ.get('HTTP_PROXY') or os.environ.get('HTTPS_PROXY')
            if http_proxy:
                proxies = {
                    'http': http_proxy,
                    'https': http_proxy
                }
        
        # Try multiple IP checking services
        ip_services = [
            'https://api.ipify.org?format=json',
            'https://httpbin.org/ip',
            'https://api.myip.com'
        ]
        
        for service_url in ip_services:
            try:
                response = requests.get(service_url, timeout=5, proxies=proxies)
                if response.status_code == 200:
                    data = response.json()
                    # Handle different response formats
                    if 'ip' in data:
                        return data['ip']
                    elif 'origin' in data:
                        # httpbin returns "origin" which can be comma-separated
                        origin = data['origin']
                        if isinstance(origin, str):
                            return origin.split(',')[0].strip()
                        return str(origin)
                    elif 'query' in data:
                        return data['query']
            except Exception:
                continue
        return None
    except Exception:
        return None


def get_next_proxy() -> Optional[str]:
    """Get next proxy from rotation list"""
    global _proxy_index
    if not PROXY_SERVERS_LIST:
        return None
    
    with _proxy_lock:
        proxy = PROXY_SERVERS_LIST[_proxy_index % len(PROXY_SERVERS_LIST)]
        _proxy_index += 1
        return proxy


@contextmanager
def proxy_context(proxy_url: Optional[str] = None, request_name: str = "request"):
    """
    Context manager to temporarily set proxy environment variables for requests.
    yfinance uses requests library internally, which automatically picks up HTTP_PROXY/HTTPS_PROXY.
    
    Args:
        proxy_url: Specific proxy to use (if None, uses rotation or single proxy)
        request_name: Name of the request for logging (e.g., "Company Profile", "Fast Info")
    """
    old_http_proxy = os.environ.get('HTTP_PROXY')
    old_https_proxy = os.environ.get('HTTPS_PROXY')
    
    # Determine which proxy to use
    if proxy_url is None:
        if PROXY_SERVERS_LIST:
            proxy_url = get_next_proxy()
        elif PROXY_SERVER:
            proxy_url = PROXY_SERVER
    
    if proxy_url:
        # Set proxy for both HTTP and HTTPS
        os.environ['HTTP_PROXY'] = proxy_url
        os.environ['HTTPS_PROXY'] = proxy_url
        
        # Get and log IP address
        try:
            current_ip = get_current_ip(proxy_url)
            if current_ip:
                print(f"🔗 [YFINANCE] [{request_name}] Proxy: {proxy_url} → IP: {current_ip}")
            else:
                print(f"🔗 [YFINANCE] [{request_name}] Using proxy: {proxy_url} (IP verification failed)")
        except Exception as e:
            print(f"🔗 [YFINANCE] [{request_name}] Using proxy: {proxy_url} (Error checking IP: {e})")
    else:
        # Remove proxy if it was set before
        if 'HTTP_PROXY' in os.environ:
            del os.environ['HTTP_PROXY']
        if 'HTTPS_PROXY' in os.environ:
            del os.environ['HTTPS_PROXY']
        
        # Get and log IP address
        try:
            current_ip = get_current_ip()
            if current_ip:
                print(f"🌐 [YFINANCE] [{request_name}] Direct connection → IP: {current_ip}")
            else:
                print(f"🌐 [YFINANCE] [{request_name}] Direct connection (no proxy)")
        except Exception as e:
            print(f"🌐 [YFINANCE] [{request_name}] Direct connection (Error checking IP: {e})")
    
    try:
        yield
    finally:
        # Restore original proxy settings
        if old_http_proxy is not None:
            os.environ['HTTP_PROXY'] = old_http_proxy
        elif 'HTTP_PROXY' in os.environ:
            del os.environ['HTTP_PROXY']
            
        if old_https_proxy is not None:
            os.environ['HTTPS_PROXY'] = old_https_proxy
        elif 'HTTPS_PROXY' in os.environ:
            del os.environ['HTTPS_PROXY']


async def get_all_yfinance_data(symbol: str) -> Optional[Dict]:
    """
    Fetch ALL available data from Yahoo Finance using yfinance library.
    Returns data directly with API response keys (Company Profile, Fast Info, etc.)
    """
    try:
        # Run yfinance operations in executor (yfinance is synchronous)
        loop = asyncio.get_event_loop()
        
        def fetch_data():
            # Create ticker object (no proxy needed for initialization)
            ticker = yf.Ticker(symbol)
            all_data = {}
            
            # Helper functions for data conversion
            def df_to_dict(df):
                """Convert DataFrame to JSON-serializable dict."""
                if df is None or df.empty:
                    return None
                result = {}
                for idx, row in df.iterrows():
                    row_name = str(idx).strip()
                    result[row_name] = {}
                    for col in df.columns:
                        date_str = col.strftime("%Y-%m-%d") if hasattr(col, 'strftime') else str(col)
                        val = row[col]
                        if pd.notna(val):
                            result[row_name][date_str] = str(int(val)) if abs(val) >= 1 else str(val)
                        else:
                            result[row_name][date_str] = None
                return result
            
            def df_to_records(df):
                """Convert DataFrame to list of records."""
                if df is None or df.empty:
                    return None
                records = []
                for idx, row in df.iterrows():
                    record = {}
                    if hasattr(idx, 'strftime'):
                        record['date'] = idx.strftime("%Y-%m-%d")
                    else:
                        record['date'] = str(idx)
                    for col in df.columns:
                        val = row[col]
                        if pd.notna(val):
                            record[str(col)] = float(val) if isinstance(val, (int, float)) else str(val)
                        else:
                            record[str(col)] = None
                    records.append(record)
                return records
            
            def series_to_dict(series):
                """Convert Series to dict."""
                if series is None or series.empty:
                    return None
                result = {}
                for date, value in series.items():
                    date_str = date.strftime("%Y-%m-%d") if hasattr(date, 'strftime') else str(date)
                    if pd.notna(value):
                        result[date_str] = float(value) if isinstance(value, (int, float)) else str(value)
                    else:
                        result[date_str] = None
                return result
            
            # 1. Company Profile & Info
            with proxy_context(request_name="Company Profile"):
                all_data["Company Profile"] = safe_get_data(
                    lambda: ticker.info if ticker.info and len(ticker.info) > 0 else None,
                    None,
                    symbol=symbol,
                    section_name="Company Profile"
                )
            
            # 2. Fast Info (faster access to key metrics)
            with proxy_context(request_name="Fast Info"):
                def get_fast_info():
                    fi = ticker.fast_info
                    try:
                        keys = list(fi.keys())
                    except Exception:
                        try:
                            return dict(fi)
                        except Exception:
                            return None
                    out = {}
                    for k in keys:
                        try:
                            val = fi[k]
                            if isinstance(val, (int, float, str, bool)) or val is None:
                                out[k] = val
                            else:
                                out[k] = str(val)
                        except Exception:
                            out[k] = None
                    return out or None
                all_data["Fast Info"] = safe_get_data(get_fast_info, None, symbol=symbol, section_name="Fast Info")
            
            # 3. Historical Price Data (OHLCV)
            with proxy_context(request_name="Historical Prices"):
                def get_historical_prices():
                    hist = ticker.history(period="max")
                    if not hist.empty:
                        hist_dict = {}
                        for col in hist.columns:
                            hist_dict[col] = {}
                            for date, value in hist[col].items():
                                date_str = date.strftime("%Y-%m-%d") if hasattr(date, 'strftime') else str(date)
                                hist_dict[col][date_str] = float(value) if pd.notna(value) else None
                        return hist_dict
                    return None
                
                all_data["Historical Prices"] = safe_get_data(get_historical_prices, None, symbol=symbol, section_name="Historical Prices")
            
            # 4. Financial Statements - Income Statement
            with proxy_context(request_name="Income Statement Annual"):
                all_data["Income Statement Annual"] = safe_get_data(lambda: df_to_dict(ticker.financials), None, symbol=symbol, section_name="Income Statement Annual")
            with proxy_context(request_name="Income Statement Quarterly"):
                all_data["Income Statement Quarterly"] = safe_get_data(lambda: df_to_dict(ticker.quarterly_financials), None, symbol=symbol, section_name="Income Statement Quarterly")
            with proxy_context(request_name="Income Statement Annual (New)"):
                all_data["Income Statement Annual (New)"] = safe_get_data(lambda: df_to_dict(ticker.income_stmt), None, symbol=symbol, section_name="Income Statement Annual (New)")
            with proxy_context(request_name="Income Statement Quarterly (New)"):
                all_data["Income Statement Quarterly (New)"] = safe_get_data(lambda: df_to_dict(ticker.quarterly_income_stmt), None, symbol=symbol, section_name="Income Statement Quarterly (New)")
            
            # 5. Balance Sheet
            with proxy_context(request_name="Balance Sheet Annual"):
                all_data["Balance Sheet Annual"] = safe_get_data(lambda: df_to_dict(ticker.balance_sheet), None, symbol=symbol, section_name="Balance Sheet Annual")
            with proxy_context(request_name="Balance Sheet Quarterly"):
                all_data["Balance Sheet Quarterly"] = safe_get_data(lambda: df_to_dict(ticker.quarterly_balance_sheet), None, symbol=symbol, section_name="Balance Sheet Quarterly")
            
            # 6. Cash Flow
            with proxy_context(request_name="Cash Flow Annual"):
                all_data["Cash Flow Annual"] = safe_get_data(lambda: df_to_dict(ticker.cashflow), None, symbol=symbol, section_name="Cash Flow Annual")
            with proxy_context(request_name="Cash Flow Quarterly"):
                all_data["Cash Flow Quarterly"] = safe_get_data(lambda: df_to_dict(ticker.quarterly_cashflow), None, symbol=symbol, section_name="Cash Flow Quarterly")
            
            # 7. Analyst Recommendations
            with proxy_context(request_name="Analyst Recommendations"):
                all_data["Analyst Recommendations"] = safe_get_data(lambda: df_to_records(ticker.recommendations), None, symbol=symbol, section_name="Analyst Recommendations")
            with proxy_context(request_name="Recommendations Summary"):
                all_data["Recommendations Summary"] = safe_get_data(lambda: df_to_records(ticker.recommendations_summary), None, symbol=symbol, section_name="Recommendations Summary")
            
            # 8. Analyst Price Target
            with proxy_context(request_name="Analyst Price Target"):
                all_data["Analyst Price Target"] = safe_get_data(
                    lambda: ticker.analyst_price_target.to_dict() if ticker.analyst_price_target is not None and not ticker.analyst_price_target.empty else None,
                    None,
                    symbol=symbol,
                    section_name="Analyst Price Target"
                )
            
            # 9. Earnings
            with proxy_context(request_name="Earnings Quarterly"):
                all_data["Earnings Quarterly"] = safe_get_data(lambda: series_to_dict(ticker.quarterly_earnings), None, symbol=symbol, section_name="Earnings Quarterly")
            
            # 10. Earnings Calendar
            with proxy_context(request_name="Earnings Calendar"):
                all_data["Earnings Calendar"] = safe_get_data(
                    lambda: ticker.calendar.to_dict() if ticker.calendar is not None and not ticker.calendar.empty else None,
                    None,
                    symbol=symbol,
                    section_name="Earnings Calendar"
                )
            
            # 11. Dividends
            with proxy_context(request_name="Dividends"):
                all_data["Dividends"] = safe_get_data(
                    lambda: [{"date": str(date), "amount": float(amount)} for date, amount in ticker.dividends.items()] if not ticker.dividends.empty else None,
                    None,
                    symbol=symbol,
                    section_name="Dividends"
                )
            
            # 12. Stock Splits
            with proxy_context(request_name="Splits"):
                all_data["Splits"] = safe_get_data(
                    lambda: [{"date": str(date), "split_factor": float(factor)} for date, factor in ticker.splits.items()] if not ticker.splits.empty else None,
                    None,
                    symbol=symbol,
                    section_name="Splits"
                )
            
            # 13. Shares Outstanding
            with proxy_context(request_name="Shares Outstanding"):
                all_data["Shares Outstanding"] = safe_get_data(lambda: series_to_dict(ticker.shares), None, symbol=symbol, section_name="Shares Outstanding")
            
            # 14. Major Holders
            with proxy_context(request_name="Major Holders"):
                all_data["Major Holders"] = safe_get_data(lambda: df_to_records(ticker.major_holders), None, symbol=symbol, section_name="Major Holders")
            
            # 15. Institutional Holders
            with proxy_context(request_name="Institutional Holders"):
                all_data["Institutional Holders"] = safe_get_data(lambda: df_to_records(ticker.institutional_holders), None, symbol=symbol, section_name="Institutional Holders")
            
            # 16. Insider Transactions
            with proxy_context(request_name="Insider Transactions"):
                all_data["Insider Transactions"] = safe_get_data(lambda: df_to_records(ticker.insider_transactions), None, symbol=symbol, section_name="Insider Transactions")
            
            # 17. Insider Purchases
            with proxy_context(request_name="Insider Purchases"):
                all_data["Insider Purchases"] = safe_get_data(lambda: df_to_records(ticker.insider_purchases), None, symbol=symbol, section_name="Insider Purchases")
            
            # 18. Insider Roster Holders
            with proxy_context(request_name="Insider Roster Holders"):
                all_data["Insider Roster Holders"] = safe_get_data(lambda: df_to_records(ticker.insider_roster_holders), None, symbol=symbol, section_name="Insider Roster Holders")
            
            # 19. Sustainability (ESG)
            with proxy_context(request_name="Sustainability"):
                all_data["Sustainability"] = safe_get_data(
                    lambda: ticker.sustainability.to_dict() if ticker.sustainability is not None and not ticker.sustainability.empty else None,
                    None,
                    symbol=symbol,
                    section_name="Sustainability"
                )
            
            # 20. News
            with proxy_context(request_name="News"):
                all_data["News"] = safe_get_data(lambda: ticker.news if ticker.news else None, None, symbol=symbol, section_name="News")
            
            # Filter out None values to keep only sections with data
            filtered_data = {k: v for k, v in all_data.items() if v is not None}
            
            return filtered_data if filtered_data else None
        
        # Execute in executor
        result = await loop.run_in_executor(None, fetch_data)
        return result
        
    except Exception as e:
        debug(f"⚠️ Failed to get all yfinance data: {e}")
        return None

