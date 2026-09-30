from sqlalchemy.orm import Session
from fastapi import HTTPException
import models
from schemas_portfolio import PortfolioCreate, TransactionCreate

def create_portfolio(db: Session, port_data: PortfolioCreate) -> models.Portfolio:
    existing = db.query(models.Portfolio).filter(models.Portfolio.name == port_data.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Portfolio with this name already exists.")
    
    new_portfolio = models.Portfolio(name=port_data.name)
    db.add(new_portfolio)
    db.commit()
    db.refresh(new_portfolio)
    return new_portfolio

def get_all_portfolios(db: Session) -> list[models.Portfolio]:
    return db.query(models.Portfolio).all()

def get_portfolio(db: Session, portfolio_id: int) -> models.Portfolio:
    portfolio = db.query(models.Portfolio).filter(models.Portfolio.id == portfolio_id).first()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found.")
    return portfolio

def process_transaction(db: Session, portfolio_id: int, tx_data: TransactionCreate) -> models.Asset:
    portfolio = get_portfolio(db, portfolio_id)
    symbol_upper = tx_data.symbol.upper()
    
    asset = db.query(models.Asset).filter(
        models.Asset.portfolio_id == portfolio_id,
        models.Asset.symbol == symbol_upper
    ).first()

    if tx_data.type == models.TransactionType.BUY:
        if not asset:
            asset = models.Asset(
                portfolio_id=portfolio_id, 
                symbol=symbol_upper, 
                quantity=tx_data.quantity, 
                average_price=tx_data.price
            )
            db.add(asset)
        else:
            total_cost = (asset.quantity * asset.average_price) + (tx_data.quantity * tx_data.price)
            asset.quantity += tx_data.quantity
            asset.average_price = total_cost / asset.quantity
            
    elif tx_data.type == models.TransactionType.SELL:
        if not asset or asset.quantity < tx_data.quantity:
            raise HTTPException(status_code=400, detail="Insufficient shares to complete the sale.")
        
        asset.quantity -= tx_data.quantity

    db.commit()
    db.refresh(asset)

    new_tx = models.Transaction(
        asset_id=asset.id,
        type=tx_data.type,
        quantity=tx_data.quantity,
        price=tx_data.price
    )
    db.add(new_tx)
    db.commit()
    db.refresh(asset)
    
    return asset