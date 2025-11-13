"""
Yahoo Finance Controller
Controller for Yahoo Finance operations
"""
from services.yfinance_service import get_all_yfinance_data
from services.company_profile_service import CompanyProfileService
from schemas.yfinance import YFinanceFetchRequest, YFinanceFetchResponse
from schemas.company_profile import CompanyProfileCreate, CompanyProfileUpdate
from fastapi import HTTPException, status
from typing import Optional, Dict, Any


class YFinanceController:
    """Controller for Yahoo Finance operations"""
    
    async def fetch_all_data(self, ticker: str) -> Optional[Dict]:
        """
        Fetch all available data from Yahoo Finance
        
        Args:
            ticker: Stock ticker symbol (e.g., AAPL, TSLA)
            
        Returns:
            Dict containing company data or None if failed
        """
        try:
            data = await get_all_yfinance_data(ticker.upper())
            return data
        except Exception as e:
            print(f"❌ Error fetching data from Yahoo Finance: {e}")
            return None


# Router functions
async def fetch_data_from_yfinance_post(request: YFinanceFetchRequest) -> YFinanceFetchResponse:
    """POST endpoint handler for fetching data from Yahoo Finance"""
    ticker = request.ticker.upper()
    save_to_db = request.save_to_db
    
    print(f"Received request to fetch data for {ticker} from Yahoo Finance (POST)")
    
    try:
        controller = YFinanceController()
        data = await controller.fetch_all_data(ticker)
        
        if not data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No data found for {ticker} from Yahoo Finance."
            )
        
        profile_id = None
        if save_to_db:
            company_profile_service = CompanyProfileService()
            existing_profile = await company_profile_service.get_by_ticker(ticker)
            
            if existing_profile:
                existing_data = existing_profile.data or {}
                updated_data = {
                    **existing_data,
                    "YahooFinance": data  # Save separately by source
                }
                updated_profile = await company_profile_service.update_profile(
                    str(existing_profile.id),
                    CompanyProfileUpdate(data=updated_data)
                )
                profile_id = str(updated_profile.id) if updated_profile else None
                print(f"Updated existing profile for {ticker} in DB with Yahoo Finance data: {profile_id}")
            else:
                new_profile = await company_profile_service.create_profile(
                    CompanyProfileCreate(ticker=ticker, data={"YahooFinance": data})
                )
                profile_id = str(new_profile.id) if new_profile else None
                print(f"Created new profile for {ticker} in DB with Yahoo Finance data: {profile_id}")
        
        return YFinanceFetchResponse(
            ticker=ticker,
            data=data,
            saved_to_db=save_to_db,
            profile_id=profile_id
        )
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error fetching data from Yahoo Finance: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching data from Yahoo Finance: {e}"
        )


async def fetch_data_from_yfinance_get(ticker: str, save_to_db: bool = True) -> YFinanceFetchResponse:
    """GET endpoint handler for fetching data from Yahoo Finance"""
    ticker = ticker.upper()
    
    print(f"Received request to fetch data for {ticker} from Yahoo Finance (GET)")
    
    try:
        controller = YFinanceController()
        data = await controller.fetch_all_data(ticker)
        
        if not data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No data found for {ticker} from Yahoo Finance."
            )
        
        profile_id = None
        if save_to_db:
            company_profile_service = CompanyProfileService()
            existing_profile = await company_profile_service.get_by_ticker(ticker)
            
            if existing_profile:
                existing_data = existing_profile.data or {}
                updated_data = {
                    **existing_data,
                    "YahooFinance": data  # Save separately by source
                }
                updated_profile = await company_profile_service.update_profile(
                    str(existing_profile.id),
                    CompanyProfileUpdate(data=updated_data)
                )
                profile_id = str(updated_profile.id) if updated_profile else None
                print(f"Updated existing profile for {ticker} in DB with Yahoo Finance data: {profile_id}")
            else:
                new_profile = await company_profile_service.create_profile(
                    CompanyProfileCreate(ticker=ticker, data={"YahooFinance": data})
                )
                profile_id = str(new_profile.id) if new_profile else None
                print(f"Created new profile for {ticker} in DB with Yahoo Finance data: {profile_id}")
        
        return YFinanceFetchResponse(
            ticker=ticker,
            data=data,
            saved_to_db=save_to_db,
            profile_id=profile_id
        )
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error fetching data from Yahoo Finance: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching data from Yahoo Finance: {e}"
        )

