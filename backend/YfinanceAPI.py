import yfinance as yf
import pandas as pd
import json
import os
import warnings
import shutil
import platform
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

# Suppress yfinance deprecation warnings
warnings.filterwarnings('ignore', category=DeprecationWarning)

load_dotenv()

VERBOSE = (os.getenv("VERBOSE", "false") or "false").lower() in ("1", "true", "yes", "y")


def clear_yfinance_cache():
    """Clear yfinance cache to reset session and avoid rate limiting"""
    try:
        # Get yfinance cache location based on OS
        system = platform.system()
        user_home = Path.home()
        
        if system == "Windows":
            cache_dir = user_home / "AppData" / "Local" / "py-yfinance"
        elif system == "Linux":
            cache_dir = user_home / ".cache" / "py-yfinance"
        elif system == "Darwin":  # macOS
            cache_dir = user_home / "Library" / "Caches" / "py-yfinance"
        else:
            print(f"⚠️ [CACHE] Unknown OS: {system}, cannot determine cache location")
            return False
        
        # Check if cache directory exists
        if cache_dir.exists() and cache_dir.is_dir():
            print(f"🧹 [CACHE] Found yfinance cache at: {cache_dir}")
            
            # Count files before deletion
            file_count = sum(1 for _ in cache_dir.rglob('*') if _.is_file())
            print(f"🧹 [CACHE] Found {file_count} cache files")
            
            # Delete cache directory
            shutil.rmtree(cache_dir)
            print(f"✅ [CACHE] Successfully cleared yfinance cache ({file_count} files)")
            return True
        else:
            print(f"ℹ️ [CACHE] No cache found at: {cache_dir}")
            return False
            
    except Exception as e:
        print(f"❌ [CACHE] Error clearing yfinance cache: {e}")
        return False


def clear_yfinance_session():
    """Clear yfinance session by creating fresh ticker instances"""
    try:
        # Clear any module-level caches
        import yfinance.base as yf_base
        import yfinance.scrapers.quote as yf_quote
        
        # Clear session if it exists
        if hasattr(yf_base, '_session'):
            yf_base._session = None
        if hasattr(yf_quote, '_session'):
            yf_quote._session = None
            
        print(f"✅ [SESSION] Cleared yfinance session")
        return True
    except Exception as e:
        print(f"⚠️ [SESSION] Could not clear session: {e}")
        return False

# Initialize FastAPI app
app = FastAPI(
    title="Yahoo Finance API",
    description="REST API for fetching stock data using yfinance",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)


def debug(*args, **kwargs):
    if VERBOSE:
        print(*args, **kwargs)


def save_json(filename, data):
    """Save dictionary data to JSON file"""
    with open(filename, "w") as f:
        json.dump(data, f, indent=4)
    debug(f"✅ Saved → {filename}")


def get_company_profile(symbol):
    """Fetch company overview using yfinance."""
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info
        
        if info:
            # Map yfinance info to similar structure as Alpha Vantage
            result = {
                "Symbol": info.get("symbol", symbol),
                "AssetType": "Common Stock",
                "Name": info.get("longName") or info.get("shortName"),
                "Description": info.get("longBusinessSummary"),
                "CIK": str(info.get("cik", "")) if info.get("cik") else None,
                "Exchange": info.get("exchange"),
                "Currency": info.get("currency", "USD"),
                "Country": info.get("country"),
                "Sector": info.get("sector"),
                "Industry": info.get("industry"),
                "Address": info.get("address1"),
                "OfficialSite": info.get("website"),
                "FiscalYearEnd": None,  # yfinance doesn't provide this directly
                "LatestQuarter": info.get("mostRecentQuarter"),
                "MarketCapitalization": str(int(info.get("marketCap", 0))) if info.get("marketCap") else None,
                "EBITDA": str(int(info.get("ebitda", 0))) if info.get("ebitda") else None,
                "PERatio": str(info.get("trailingPE")) if info.get("trailingPE") else None,
                "PEGRatio": str(info.get("pegRatio")) if info.get("pegRatio") else None,
                "BookValue": str(info.get("bookValue")) if info.get("bookValue") else None,
                "DividendPerShare": str(info.get("dividendRate")) if info.get("dividendRate") else None,
                "DividendYield": str(info.get("dividendYield")) if info.get("dividendYield") else None,
                "EPS": str(info.get("trailingEps")) if info.get("trailingEps") else None,
                "RevenuePerShareTTM": str(info.get("revenuePerShare")) if info.get("revenuePerShare") else None,
                "ProfitMargin": str(info.get("profitMargins")) if info.get("profitMargins") else None,
                "OperatingMarginTTM": str(info.get("operatingMargins")) if info.get("operatingMargins") else None,
                "ReturnOnAssetsTTM": str(info.get("returnOnAssets")) if info.get("returnOnAssets") else None,
                "ReturnOnEquityTTM": str(info.get("returnOnEquity")) if info.get("returnOnEquity") else None,
                "RevenueTTM": str(int(info.get("totalRevenue", 0))) if info.get("totalRevenue") else None,
                "GrossProfitTTM": str(int(info.get("grossProfits", 0))) if info.get("grossProfits") else None,
                "DilutedEPSTTM": str(info.get("trailingEps")) if info.get("trailingEps") else None,
                "QuarterlyEarningsGrowthYOY": str(info.get("earningsQuarterlyGrowth")) if info.get("earningsQuarterlyGrowth") else None,
                "QuarterlyRevenueGrowthYOY": str(info.get("revenueGrowth")) if info.get("revenueGrowth") else None,
                "AnalystTargetPrice": str(info.get("targetMeanPrice")) if info.get("targetMeanPrice") else None,
                "AnalystRatingStrongBuy": None,  # yfinance doesn't provide detailed ratings
                "AnalystRatingBuy": None,
                "AnalystRatingHold": None,
                "AnalystRatingSell": None,
                "AnalystRatingStrongSell": None,
                "TrailingPE": str(info.get("trailingPE")) if info.get("trailingPE") else None,
                "ForwardPE": str(info.get("forwardPE")) if info.get("forwardPE") else None,
                "PriceToSalesRatioTTM": str(info.get("priceToSalesTrailing12Months")) if info.get("priceToSalesTrailing12Months") else None,
                "PriceToBookRatio": str(info.get("priceToBook")) if info.get("priceToBook") else None,
                "EVToRevenue": str(info.get("enterpriseToRevenue")) if info.get("enterpriseToRevenue") else None,
                "EVToEBITDA": str(info.get("enterpriseToEbitda")) if info.get("enterpriseToEbitda") else None,
                "Beta": str(info.get("beta")) if info.get("beta") else None,
                "52WeekHigh": str(info.get("fiftyTwoWeekHigh")) if info.get("fiftyTwoWeekHigh") else None,
                "52WeekLow": str(info.get("fiftyTwoWeekLow")) if info.get("fiftyTwoWeekLow") else None,
                "50DayMovingAverage": str(info.get("fiftyDayAverage")) if info.get("fiftyDayAverage") else None,
                "200DayMovingAverage": str(info.get("twoHundredDayAverage")) if info.get("twoHundredDayAverage") else None,
                "SharesOutstanding": str(int(info.get("sharesOutstanding", 0))) if info.get("sharesOutstanding") else None,
                "SharesFloat": str(int(info.get("floatShares", 0))) if info.get("floatShares") else None,
                "PercentInsiders": str(info.get("heldPercentInsiders")) if info.get("heldPercentInsiders") else None,
                "PercentInstitutions": str(info.get("heldPercentInstitutions")) if info.get("heldPercentInstitutions") else None,
                "DividendDate": None,
                "ExDividendDate": None
            }
            return result
    except Exception as e:
        debug(f"⚠️ yfinance overview failed: {e}")
    return None


def get_global_quote(symbol):
    """Fetch latest price/volume using yfinance."""
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info
        hist = ticker.history(period="1d")
        
        if not hist.empty and info:
            latest = hist.iloc[-1]
            prev_close = info.get("previousClose", latest.get("Close"))
            current_price = latest.get("Close")
            change = current_price - prev_close if current_price and prev_close else None
            change_percent = (change / prev_close * 100) if change and prev_close else None
            
            result = {
                "01. symbol": symbol,
                "02. open": str(latest.get("Open", "")),
                "03. high": str(latest.get("High", "")),
                "04. low": str(latest.get("Low", "")),
                "05. price": str(current_price) if current_price else "",
                "06. volume": str(int(latest.get("Volume", 0))),
                "07. latest trading day": latest.name.strftime("%Y-%m-%d") if hasattr(latest.name, 'strftime') else str(latest.name),
                "08. previous close": str(prev_close) if prev_close else "",
                "09. change": str(change) if change else "",
                "10. change percent": f"{change_percent:.4f}%" if change_percent else ""
            }
            return result
    except Exception as e:
        debug(f"⚠️ yfinance global quote failed: {e}")
    return None


def get_dividends(symbol):
    """Fetch historical dividend distributions using yfinance."""
    try:
        ticker = yf.Ticker(symbol)
        dividends = ticker.dividends
        
        if not dividends.empty:
            data = []
            for date, amount in dividends.items():
                data.append({
                    "ex_dividend_date": date.strftime("%Y-%m-%d") if hasattr(date, 'strftime') else str(date),
                    "declaration_date": None,  # yfinance doesn't provide this
                    "record_date": None,  # yfinance doesn't provide this
                    "payment_date": None,  # yfinance doesn't provide this
                    "amount": str(amount)
                })
            # Sort by date descending (most recent first)
            data.sort(key=lambda x: x["ex_dividend_date"], reverse=True)
            return {
                "symbol": symbol,
                "data": data
            }
    except Exception as e:
        debug(f"⚠️ yfinance dividends failed: {e}")
    return None


def get_splits(symbol):
    """Fetch historical stock split events using yfinance."""
    try:
        ticker = yf.Ticker(symbol)
        splits = ticker.splits
        
        if not splits.empty:
            data = []
            for date, split_factor in splits.items():
                data.append({
                    "effective_date": date.strftime("%Y-%m-%d") if hasattr(date, 'strftime') else str(date),
                    "split_factor": str(split_factor)
                })
            # Sort by date descending (most recent first)
            data.sort(key=lambda x: x["effective_date"], reverse=True)
            return {
                "symbol": symbol,
                "data": data
            }
    except Exception as e:
        debug(f"⚠️ yfinance splits failed: {e}")
    return None


def get_income_statement(symbol):
    """Fetch annual and quarterly income statements using yfinance."""
    try:
        ticker = yf.Ticker(symbol)
        annual = ticker.financials
        quarterly = ticker.quarterly_financials
        
        def format_financials(df, period_type):
            if df is None or df.empty:
                return []
            
            reports = []
            for date in df.columns:
                report = {
                    "fiscalDateEnding": date.strftime("%Y-%m-%d") if hasattr(date, 'strftime') else str(date),
                    "reportedCurrency": "USD"  # yfinance typically returns USD
                }
                
                # Map common financial statement fields
                for idx, row in df.iterrows():
                    field_name = str(idx).strip()
                    value = row[date]
                    if pd.notna(value) and value != 0:
                        # Convert to string, handling large numbers
                        report[field_name] = str(int(value)) if abs(value) >= 1 else str(value)
                
                reports.append(report)
            
            return reports
        
        annual_reports = format_financials(annual, "annual")
        quarterly_reports = format_financials(quarterly, "quarterly")
        
        return {
            "symbol": symbol,
            "annualReports": annual_reports,
            "quarterlyReports": quarterly_reports
        }
    except Exception as e:
        debug(f"⚠️ yfinance income statement failed: {e}")
    return None


def get_balance_sheet(symbol):
    """Fetch annual and quarterly balance sheets using yfinance."""
    try:
        ticker = yf.Ticker(symbol)
        annual = ticker.balance_sheet
        quarterly = ticker.quarterly_balance_sheet
        
        def format_balance_sheet(df, period_type):
            if df is None or df.empty:
                return []
            
            reports = []
            for date in df.columns:
                report = {
                    "fiscalDateEnding": date.strftime("%Y-%m-%d") if hasattr(date, 'strftime') else str(date),
                    "reportedCurrency": "USD"
                }
                
                for idx, row in df.iterrows():
                    field_name = str(idx).strip()
                    value = row[date]
                    if pd.notna(value) and value != 0:
                        report[field_name] = str(int(value)) if abs(value) >= 1 else str(value)
                
                reports.append(report)
            
            return reports
        
        annual_reports = format_balance_sheet(annual, "annual")
        quarterly_reports = format_balance_sheet(quarterly, "quarterly")
        
        return {
            "symbol": symbol,
            "annualReports": annual_reports,
            "quarterlyReports": quarterly_reports
        }
    except Exception as e:
        debug(f"⚠️ yfinance balance sheet failed: {e}")
    return None


def get_cash_flow(symbol):
    """Fetch annual and quarterly cash flow statements using yfinance."""
    try:
        ticker = yf.Ticker(symbol)
        annual = ticker.cashflow
        quarterly = ticker.quarterly_cashflow
        
        def format_cash_flow(df, period_type):
            if df is None or df.empty:
                return []
            
            reports = []
            for date in df.columns:
                report = {
                    "fiscalDateEnding": date.strftime("%Y-%m-%d") if hasattr(date, 'strftime') else str(date),
                    "reportedCurrency": "USD"
                }
                
                for idx, row in df.iterrows():
                    field_name = str(idx).strip()
                    value = row[date]
                    if pd.notna(value) and value != 0:
                        report[field_name] = str(int(value)) if abs(value) >= 1 else str(value)
                
                reports.append(report)
            
            return reports
        
        annual_reports = format_cash_flow(annual, "annual")
        quarterly_reports = format_cash_flow(quarterly, "quarterly")
        
        return {
            "symbol": symbol,
            "annualReports": annual_reports,
            "quarterlyReports": quarterly_reports
        }
    except Exception as e:
        debug(f"⚠️ yfinance cash flow failed: {e}")
    return None


def get_earnings_history(symbol):
    """Fetch annual earnings history using yfinance income statement."""
    try:
        ticker = yf.Ticker(symbol)
        annual_earnings = []
        
        # Use income statement to get EPS data (ticker.earnings is deprecated)
        try:
            # Get annual income statement
            income_stmt = ticker.income_stmt
            if income_stmt is not None and not income_stmt.empty:
                # Look for EPS-related rows in the income statement
                eps_row = None
                eps_row_names = [
                    'Diluted EPS',
                    'Basic EPS',
                    'Earnings Per Share',
                    'EPS - Earnings Per Share',
                    'Diluted EPS Including Extraordinary Items',
                    'Basic EPS Including Extraordinary Items'
                ]
                
                # Find the EPS row
                for row_name in eps_row_names:
                    if row_name in income_stmt.index:
                        eps_row = income_stmt.loc[row_name]
                        break
                
                # If no direct EPS row found, calculate from Net Income and Shares Outstanding
                if eps_row is None:
                    net_income_row = None
                    net_income_names = [
                        'Net Income',
                        'Net Income Common Stockholders',
                        'Net Income Including Noncontrolling Interests'
                    ]
                    
                    for row_name in net_income_names:
                        if row_name in income_stmt.index:
                            net_income_row = income_stmt.loc[row_name]
                            break
                    
                    # Get shares outstanding from balance sheet
                    shares_outstanding = None
                    try:
                        balance_sheet = ticker.balance_sheet
                        if balance_sheet is not None and not balance_sheet.empty:
                            shares_names = [
                                'Share Issued',
                                'Shares Outstanding',
                                'Common Stock Shares Outstanding'
                            ]
                            for row_name in shares_names:
                                if row_name in balance_sheet.index:
                                    shares_outstanding = balance_sheet.loc[row_name]
                                    break
                    except Exception:
                        pass
                    
                    # Calculate EPS if we have both net income and shares
                    if net_income_row is not None and shares_outstanding is not None:
                        # Align dates between net income and shares
                        common_dates = net_income_row.index.intersection(shares_outstanding.index)
                        for date in common_dates:
                            net_income = net_income_row[date]
                            shares = shares_outstanding[date]
                            if pd.notna(net_income) and pd.notna(shares) and shares != 0:
                                eps_value = net_income / shares
                                if pd.notna(eps_value) and eps_value != 0:
                                    fiscal_date = date.strftime("%Y-%m-%d") if hasattr(date, 'strftime') else str(date)
                                    annual_earnings.append({
                                        "fiscalDateEnding": fiscal_date,
                                        "reportedEPS": str(eps_value)
                                    })
                
                # If we found EPS row directly, use it
                if eps_row is not None:
                    for date in eps_row.index:
                        eps_value = eps_row[date]
                        if pd.notna(eps_value) and eps_value != 0:
                            fiscal_date = date.strftime("%Y-%m-%d") if hasattr(date, 'strftime') else str(date)
                            annual_earnings.append({
                                "fiscalDateEnding": fiscal_date,
                                "reportedEPS": str(eps_value)
                            })
                
        except Exception as e1:
            debug(f"⚠️ Income statement EPS extraction failed: {e1}")
        
        # Sort by date descending (most recent first)
        if annual_earnings:
            annual_earnings.sort(key=lambda x: x["fiscalDateEnding"], reverse=True)
            return {
                "symbol": symbol,
                "annualEarnings": annual_earnings
            }
    except Exception as e:
        debug(f"⚠️ yfinance earnings history failed: {e}")
    return None


def safe_get_data(func, default=None):
    """Safely execute a function and return default on any error."""
    try:
        result = func()
        return result if result is not None else default
    except Exception as e:
        debug(f"⚠️ Data fetch failed: {type(e).__name__}: {e}")
        return default


def get_all_yfinance_data(symbol):
    """Extract all available data from yfinance in organized sections."""
    try:
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
        all_data["Company Profile"] = safe_get_data(
            lambda: ticker.info if ticker.info and len(ticker.info) > 0 else None,
            None
        )
        
        # 2. Fast Info (faster access to key metrics)
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
        all_data["Fast Info"] = safe_get_data(get_fast_info, None)
        
        # 3. Historical Price Data (OHLCV)
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
        
        all_data["Historical Prices"] = safe_get_data(get_historical_prices, None)
        
        # 4. Financial Statements - Income Statement
        all_data["Income Statement Annual"] = safe_get_data(lambda: df_to_dict(ticker.financials), None)
        all_data["Income Statement Quarterly"] = safe_get_data(lambda: df_to_dict(ticker.quarterly_financials), None)
        all_data["Income Statement Annual (New)"] = safe_get_data(lambda: df_to_dict(ticker.income_stmt), None)
        all_data["Income Statement Quarterly (New)"] = safe_get_data(lambda: df_to_dict(ticker.quarterly_income_stmt), None)
        
        # 5. Balance Sheet
        all_data["Balance Sheet Annual"] = safe_get_data(lambda: df_to_dict(ticker.balance_sheet), None)
        all_data["Balance Sheet Quarterly"] = safe_get_data(lambda: df_to_dict(ticker.quarterly_balance_sheet), None)
        
        # 6. Cash Flow
        all_data["Cash Flow Annual"] = safe_get_data(lambda: df_to_dict(ticker.cashflow), None)
        all_data["Cash Flow Quarterly"] = safe_get_data(lambda: df_to_dict(ticker.quarterly_cashflow), None)
        
        # 7. Analyst Recommendations
        all_data["Analyst Recommendations"] = safe_get_data(lambda: df_to_records(ticker.recommendations), None)
        all_data["Recommendations Summary"] = safe_get_data(lambda: df_to_records(ticker.recommendations_summary), None)
        
        # 8. Analyst Price Target
        all_data["Analyst Price Target"] = safe_get_data(
            lambda: ticker.analyst_price_target.to_dict() if ticker.analyst_price_target is not None and not ticker.analyst_price_target.empty else None,
            None
        )
        
        # 9. Earnings (skip deprecated ticker.earnings, use income_stmt instead)
        all_data["Earnings Annual"] = None  # Deprecated
        all_data["Earnings Quarterly"] = safe_get_data(lambda: series_to_dict(ticker.quarterly_earnings), None)
        
        # 10. Earnings Calendar
        all_data["Earnings Calendar"] = safe_get_data(
            lambda: ticker.calendar.to_dict() if ticker.calendar is not None and not ticker.calendar.empty else None,
            None
        )
        
        # 11. Dividends
        all_data["Dividends"] = safe_get_data(
            lambda: [{"date": str(date), "amount": float(amount)} for date, amount in ticker.dividends.items()] if not ticker.dividends.empty else None,
            None
        )
        
        # 12. Stock Splits
        all_data["Splits"] = safe_get_data(
            lambda: [{"date": str(date), "split_factor": float(factor)} for date, factor in ticker.splits.items()] if not ticker.splits.empty else None,
            None
        )
        
        # 13. Shares Outstanding
        all_data["Shares Outstanding"] = safe_get_data(lambda: series_to_dict(ticker.shares), None)
        
        # 14. Major Holders
        all_data["Major Holders"] = safe_get_data(lambda: df_to_records(ticker.major_holders), None)
        
        # 15. Institutional Holders
        all_data["Institutional Holders"] = safe_get_data(lambda: df_to_records(ticker.institutional_holders), None)
        
        # 16. Insider Transactions
        all_data["Insider Transactions"] = safe_get_data(lambda: df_to_records(ticker.insider_transactions), None)
        
        # 17. Insider Purchases
        all_data["Insider Purchases"] = safe_get_data(lambda: df_to_records(ticker.insider_purchases), None)
        
        # 18. Insider Roster Holders
        all_data["Insider Roster Holders"] = safe_get_data(lambda: df_to_records(ticker.insider_roster_holders), None)
        
        # 19. Sustainability (ESG)
        all_data["Sustainability"] = safe_get_data(
            lambda: ticker.sustainability.to_dict() if ticker.sustainability is not None and not ticker.sustainability.empty else None,
            None
        )
        
        # 20. News
        all_data["News"] = safe_get_data(lambda: ticker.news if ticker.news else None, None)
        
        return all_data
        
    except Exception as e:
        debug(f"⚠️ Failed to get all yfinance data: {e}")
        return None


def get_company_identity_layer(symbol):
    profile = get_company_profile(symbol)
    quote = get_global_quote(symbol)
    dividends = get_dividends(symbol)
    splits = get_splits(symbol)
    income_statement = get_income_statement(symbol)
    balance_sheet = get_balance_sheet(symbol)
    cash_flow = get_cash_flow(symbol)
    earnings_history = get_earnings_history(symbol)

    # Return all eight sections separated
    return {
        "Overview": profile,
        "Global Quote": quote,
        "Dividends": dividends,
        "Splits": splits,
        "Income Statement": income_statement,
        "Balance Sheet": balance_sheet,
        "Cash Flow": cash_flow,
        "Earnings History": earnings_history
    }


# ------------------ FASTAPI ENDPOINTS ------------------

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Yahoo Finance API",
        "version": "1.0.0",
        "docs": "/docs",
        "endpoints": {
            "company_profile": "/api/v1/company-profile/{symbol}",
            "global_quote": "/api/v1/global-quote/{symbol}",
            "dividends": "/api/v1/dividends/{symbol}",
            "splits": "/api/v1/splits/{symbol}",
            "income_statement": "/api/v1/income-statement/{symbol}",
            "balance_sheet": "/api/v1/balance-sheet/{symbol}",
            "cash_flow": "/api/v1/cash-flow/{symbol}",
            "earnings_history": "/api/v1/earnings-history/{symbol}",
            "all_data": "/api/v1/all-data/{symbol}",
            "company_identity": "/api/v1/company-identity/{symbol}"
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "Yahoo Finance API"}


@app.post("/api/v1/clear-cache")
async def api_clear_cache():
    """Clear yfinance cache to reset session and avoid rate limiting"""
    try:
        cache_cleared = clear_yfinance_cache()
        session_cleared = clear_yfinance_session()
        
        return {
            "status": "success",
            "cache_cleared": cache_cleared,
            "session_cleared": session_cleared,
            "message": "yfinance cache and session cleared successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error clearing cache: {str(e)}")


@app.get("/api/v1/company-profile/{symbol}")
async def api_company_profile(symbol: str):
    """Get company profile/overview for a stock symbol"""
    try:
        symbol = symbol.upper()
        result = get_company_profile(symbol)
        if result is None:
            raise HTTPException(status_code=404, detail=f"No data found for symbol: {symbol}")
        return JSONResponse(content=result)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching company profile: {str(e)}")


@app.get("/api/v1/global-quote/{symbol}")
async def api_global_quote(symbol: str):
    """Get latest price/volume quote for a stock symbol"""
    try:
        symbol = symbol.upper()
        result = get_global_quote(symbol)
        if result is None:
            raise HTTPException(status_code=404, detail=f"No data found for symbol: {symbol}")
        return JSONResponse(content=result)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching global quote: {str(e)}")


@app.get("/api/v1/dividends/{symbol}")
async def api_dividends(symbol: str):
    """Get historical dividend distributions for a stock symbol"""
    try:
        symbol = symbol.upper()
        result = get_dividends(symbol)
        if result is None:
            raise HTTPException(status_code=404, detail=f"No dividend data found for symbol: {symbol}")
        return JSONResponse(content=result)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching dividends: {str(e)}")


@app.get("/api/v1/splits/{symbol}")
async def api_splits(symbol: str):
    """Get historical stock split events for a stock symbol"""
    try:
        symbol = symbol.upper()
        result = get_splits(symbol)
        if result is None:
            raise HTTPException(status_code=404, detail=f"No split data found for symbol: {symbol}")
        return JSONResponse(content=result)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching splits: {str(e)}")


@app.get("/api/v1/income-statement/{symbol}")
async def api_income_statement(symbol: str):
    """Get annual and quarterly income statements for a stock symbol"""
    try:
        symbol = symbol.upper()
        result = get_income_statement(symbol)
        if result is None:
            raise HTTPException(status_code=404, detail=f"No income statement data found for symbol: {symbol}")
        return JSONResponse(content=result)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching income statement: {str(e)}")


@app.get("/api/v1/balance-sheet/{symbol}")
async def api_balance_sheet(symbol: str):
    """Get annual and quarterly balance sheets for a stock symbol"""
    try:
        symbol = symbol.upper()
        result = get_balance_sheet(symbol)
        if result is None:
            raise HTTPException(status_code=404, detail=f"No balance sheet data found for symbol: {symbol}")
        return JSONResponse(content=result)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching balance sheet: {str(e)}")


@app.get("/api/v1/cash-flow/{symbol}")
async def api_cash_flow(symbol: str):
    """Get annual and quarterly cash flow statements for a stock symbol"""
    try:
        symbol = symbol.upper()
        result = get_cash_flow(symbol)
        if result is None:
            raise HTTPException(status_code=404, detail=f"No cash flow data found for symbol: {symbol}")
        return JSONResponse(content=result)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching cash flow: {str(e)}")


@app.get("/api/v1/earnings-history/{symbol}")
async def api_earnings_history(symbol: str):
    """Get annual earnings history for a stock symbol"""
    try:
        symbol = symbol.upper()
        result = get_earnings_history(symbol)
        if result is None:
            raise HTTPException(status_code=404, detail=f"No earnings history data found for symbol: {symbol}")
        return JSONResponse(content=result)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching earnings history: {str(e)}")


@app.get("/api/v1/all-data/{symbol}")
async def api_all_data(symbol: str):
    """Get all available yfinance data for a stock symbol (comprehensive endpoint)"""
    try:
        symbol = symbol.upper()
        result = get_all_yfinance_data(symbol)
        if result is None:
            raise HTTPException(status_code=404, detail=f"No data found for symbol: {symbol}")
        return JSONResponse(content=result)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching all data: {str(e)}")


@app.get("/api/v1/company-identity/{symbol}")
async def api_company_identity(symbol: str):
    """Get company identity layer (overview, quote, dividends, splits, financials, earnings)"""
    try:
        symbol = symbol.upper()
        result = get_company_identity_layer(symbol)
        if result is None:
            raise HTTPException(status_code=404, detail=f"No data found for symbol: {symbol}")
        return JSONResponse(content=result)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching company identity: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    # Use app directly instead of string to avoid module import issues
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        reload=False  # Set to False when using app object directly
    )

