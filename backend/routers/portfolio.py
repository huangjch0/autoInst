from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel
from backend.database import get_db, Portfolio

router = APIRouter(prefix="/api/portfolio", tags=["portfolio"])

class PortfolioCreate(BaseModel):
    date: datetime
    total_value: float
    cash: float = 0
    notes: Optional[str] = None

class PortfolioResponse(BaseModel):
    id: int
    date: datetime
    total_value: float
    cash: float
    notes: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True

@router.get("/", response_model=List[PortfolioResponse])
def get_portfolios(db: Session = Depends(get_db)):
    return db.query(Portfolio).order_by(Portfolio.date.desc()).all()

@router.post("/", response_model=PortfolioResponse)
def create_portfolio(portfolio: PortfolioCreate, db: Session = Depends(get_db)):
    db_portfolio = Portfolio(**portfolio.model_dump())
    db.add(db_portfolio)
    db.commit()
    db.refresh(db_portfolio)
    return db_portfolio

@router.get("/summary")
def get_portfolio_summary(db: Session = Depends(get_db)):
    from backend.database import Asset, Transaction, MarketData
    from sqlalchemy import func
    
    assets = db.query(Asset).all()
    result = {
        "total_value": 0,
        "total_cost": 0,
        "total_profit": 0,
        "holdings": []
    }
    
    for asset in assets:
        transactions = db.query(Transaction).filter(Transaction.asset_id == asset.id).all()
        buy_qty = sum(t.quantity for t in transactions if t.type == "buy")
        sell_qty = sum(t.quantity for t in transactions if t.type == "sell")
        quantity = buy_qty - sell_qty
        
        if quantity > 0:
            buy_amount = sum(t.quantity * t.price for t in transactions if t.type == "buy")
            sell_amount = sum(t.quantity * t.price for t in transactions if t.type == "sell")
            avg_cost = (buy_amount - sell_amount) / quantity
            
            latest_data = db.query(MarketData).filter(
                MarketData.symbol == asset.symbol
            ).order_by(MarketData.date.desc()).first()
            
            current_price = latest_data.close if latest_data else avg_cost
            market_value = quantity * current_price
            profit = market_value - (quantity * avg_cost)
            
            result["holdings"].append({
                "symbol": asset.symbol,
                "name": asset.name,
                "type": asset.type,
                "quantity": quantity,
                "avg_cost": avg_cost,
                "current_price": current_price,
                "market_value": market_value,
                "profit": profit,
                "profit_percent": (profit / (quantity * avg_cost) * 100) if avg_cost > 0 else 0
            })
            result["total_value"] += market_value
            result["total_cost"] += quantity * avg_cost
    
    result["total_profit"] = result["total_value"] - result["total_cost"]
    result["total_profit_percent"] = (result["total_profit"] / result["total_cost"] * 100) if result["total_cost"] > 0 else 0
    
    return result

@router.get("/chart/distribution")
def get_distribution_chart(db: Session = Depends(get_db)):
    from backend.database import Asset, Transaction, MarketData
    
    assets = db.query(Asset).all()
    distribution = {"stock": 0, "fund": 0, "crypto": 0, "other": 0}
    
    for asset in assets:
        transactions = db.query(Transaction).filter(Transaction.asset_id == asset.id).all()
        buy_qty = sum(t.quantity for t in transactions if t.type == "buy")
        sell_qty = sum(t.quantity for t in transactions if t.type == "sell")
        quantity = buy_qty - sell_qty
        
        if quantity > 0:
            latest_data = db.query(MarketData).filter(
                MarketData.symbol == asset.symbol
            ).order_by(MarketData.date.desc()).first()
            
            if latest_data:
                value = quantity * latest_data.close
                asset_type = asset.type if asset.type in distribution else "other"
                distribution[asset_type] += value
    
    total = sum(distribution.values())
    if total > 0:
        for key in distribution:
            distribution[key] = round(distribution[key] / total * 100, 2)
    
    return distribution
