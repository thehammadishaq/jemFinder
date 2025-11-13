"""
Yahoo Finance Routes
API endpoints for Yahoo Finance operations
"""
from fastapi import APIRouter, HTTPException, status, Query
from typing import Optional
from schemas.yfinance import YFinanceFetchRequest, YFinanceFetchResponse
from controllers.yfinance_controller import fetch_data_from_yfinance_post, fetch_data_from_yfinance_get

router = APIRouter(prefix="/yfinance", tags=["Yahoo Finance"])

@router.post("/fetch-data", response_model=YFinanceFetchResponse, status_code=status.HTTP_200_OK)
async def fetch_data_post(request: YFinanceFetchRequest):
    return await fetch_data_from_yfinance_post(request)

@router.get("/fetch-data/{ticker}", response_model=YFinanceFetchResponse, status_code=status.HTTP_200_OK)
async def fetch_data_get(ticker: str, save_to_db: bool = Query(True, description="Whether to save the fetched data to the database")):
    return await fetch_data_from_yfinance_get(ticker, save_to_db)

