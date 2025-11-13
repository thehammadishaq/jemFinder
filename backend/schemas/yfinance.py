from pydantic import BaseModel, Field
from typing import Dict, Any, Optional

class YFinanceFetchRequest(BaseModel):
    ticker: str = Field(..., description="Stock ticker symbol to fetch data for", example="AAPL")
    save_to_db: bool = Field(True, description="Whether to save the fetched data to the database")

class YFinanceFetchResponse(BaseModel):
    ticker: str = Field(..., description="Stock ticker symbol")
    data: Dict[str, Any] = Field(..., description="Fetched Yahoo Finance data")
    saved_to_db: bool = Field(..., description="Indicates if the data was saved to the database")
    profile_id: Optional[str] = Field(None, description="ID of the saved profile if saved to DB")

