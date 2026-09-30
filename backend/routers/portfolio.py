from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import List
import os

from database import get_db
import schemas_portfolio
from services import portfolio_manager, sentiment_engine, pdf_generator

router = APIRouter(prefix="/api/portfolio", tags=["Portfolio Management"])

@router.post("/", response_model=schemas_portfolio.PortfolioResponse)
def create_portfolio(portfolio: schemas_portfolio.PortfolioCreate, db: Session = Depends(get_db)):
    return portfolio_manager.create_portfolio(db, portfolio)

@router.get("/", response_model=List[schemas_portfolio.PortfolioResponse])
def get_portfolios(db: Session = Depends(get_db)):
    return portfolio_manager.get_all_portfolios(db)

@router.get("/{portfolio_id}", response_model=schemas_portfolio.PortfolioResponse)
def get_portfolio_by_id(portfolio_id: int, db: Session = Depends(get_db)):
    return portfolio_manager.get_portfolio(db, portfolio_id)

@router.post("/{portfolio_id}/transaction", response_model=schemas_portfolio.AssetResponse)
def add_transaction(portfolio_id: int, tx: schemas_portfolio.TransactionCreate, db: Session = Depends(get_db)):
    return portfolio_manager.process_transaction(db, portfolio_id, tx)

@router.get("/{portfolio_id}/sentiment")
def get_portfolio_sentiment(portfolio_id: int, db: Session = Depends(get_db)):
    portfolio = portfolio_manager.get_portfolio(db, portfolio_id)
    return sentiment_engine.evaluate_portfolio_sentiment(portfolio.assets)

@router.get("/{portfolio_id}/report")
def download_portfolio_report(portfolio_id: int, db: Session = Depends(get_db)):
    portfolio = portfolio_manager.get_portfolio(db, portfolio_id)
    pdf_path = pdf_generator.generate_pdf_report(portfolio)
    
    if not os.path.exists(pdf_path):
        raise HTTPException(status_code=500, detail="Failed to generate PDF report.")
        
    return FileResponse(
        path=pdf_path, 
        media_type='application/pdf', 
        filename=os.path.basename(pdf_path)
    )