from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from models import TransactionType

class TransactionCreate(BaseModel):
    symbol: str = Field(..., description="Stock ticker symbol (e.g., AAPL)")
    type: TransactionType = Field(..., description="BUY or SELL")
    quantity: float = Field(..., gt=0, description="Amount of shares")
    price: float = Field(..., gt=0, description="Price per share at transaction time")

class TransactionResponse(BaseModel):
    id: int
    type: str
    quantity: float
    price: float
    timestamp: datetime

    class Config:
        orm_mode = True
        from_attributes = True

class AssetResponse(BaseModel):
    id: int
    symbol: str
    quantity: float
    average_price: float
    last_updated: datetime
    transactions: List[TransactionResponse] = []

    class Config:
        orm_mode = True
        from_attributes = True

class PortfolioCreate(BaseModel):
    name: str = Field(..., description="Name of the portfolio")

class PortfolioResponse(BaseModel):
    id: int
    name: str
    created_at: datetime
    assets: List[AssetResponse] = []

    class Config:
        orm_mode = True
        from_attributes = True