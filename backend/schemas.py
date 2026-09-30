from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class QuoteResponse(BaseModel):
    symbol: str
    price: float
    change: float
    change_percent: float
    volume: int
    market_cap: Optional[float] = None
    last_updated: str

class HistoryPoint(BaseModel):
    timestamp: str
    open: float
    high: float
    low: float
    close: float
    volume: int

class HistoryResponse(BaseModel):
    symbol: str
    period: str
    data: List[HistoryPoint]

class NewsItem(BaseModel):
    headline: str
    summary: str
    url: str
    source: str
    published_at: str
    sentiment: str = Field(description="Calculated sentiment: Buy, Hold, or Sell")