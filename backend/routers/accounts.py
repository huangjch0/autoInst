from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel
from backend.database import get_db, Account, Transaction, Asset, MarketData, PortfolioSnapshot

router = APIRouter(prefix="/api/accounts", tags=["accounts"])

class AccountCreate(BaseModel):
    name: str
    description: Optional[str] = None
    initial_capital: float = 0

class AccountUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    initial_capital: Optional[float] = None

class AccountResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    initial_capital: float
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class HoldingItem(BaseModel):
    symbol: str
    name: str
    quantity: float
    avg_cost: float
    current_price: Optional[float]
    market_value: Optional[float]
    profit_loss: Optional[float]
    profit_loss_pct: Optional[float]

class AccountSummary(BaseModel):
    id: int
    name: str
    description: Optional[str]
    initial_capital: float
    current_value: float
    cash: float
    position_value: float
    total_profit_loss: float
    total_profit_loss_pct: float
    holdings: List[HoldingItem]
    transaction_count: int
    last_updated: Optional[datetime]

class TransactionResponse(BaseModel):
    id: int
    asset_id: int
    symbol: str
    name: str
    type: str
    date: datetime
    quantity: float
    price: float
    fee: float
    notes: Optional[str]
    
    class Config:
        from_attributes = True

class PortfolioSnapshotCreate(BaseModel):
    total_value: float
    cash: float
    position_value: float
    daily_return: float
    notes: Optional[str] = None

class PortfolioSnapshotResponse(BaseModel):
    id: int
    date: datetime
    total_value: float
    cash: float
    position_value: float
    daily_return: float
    notes: Optional[str]
    
    class Config:
        from_attributes = True

@router.get("/", response_model=List[AccountResponse])
def get_accounts(db: Session = Depends(get_db)):
    return db.query(Account).all()

@router.get("/{account_id}", response_model=AccountResponse)
def get_account(account_id: int, db: Session = Depends(get_db)):
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="账户未找到")
    return account

@router.post("/", response_model=AccountResponse)
def create_account(account: AccountCreate, db: Session = Depends(get_db)):
    db_account = Account(**account.model_dump())
    db.add(db_account)
    db.commit()
    db.refresh(db_account)
    return db_account

@router.put("/{account_id}", response_model=AccountResponse)
def update_account(account_id: int, account: AccountUpdate, db: Session = Depends(get_db)):
    db_account = db.query(Account).filter(Account.id == account_id).first()
    if not db_account:
        raise HTTPException(status_code=404, detail="账户未找到")
    
    update_data = account.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_account, key, value)
    
    db.commit()
    db.refresh(db_account)
    return db_account

@router.delete("/{account_id}")
def delete_account(account_id: int, db: Session = Depends(get_db)):
    db_account = db.query(Account).filter(Account.id == account_id).first()
    if not db_account:
        raise HTTPException(status_code=404, detail="账户未找到")
    
    db.query(Transaction).filter(Transaction.account_id == account_id).delete()
    db.query(PortfolioSnapshot).filter(PortfolioSnapshot.account_id == account_id).delete()
    
    db.delete(db_account)
    db.commit()
    return {"message": "账户已删除"}

@router.get("/{account_id}/summary", response_model=AccountSummary)
def get_account_summary(account_id: int, db: Session = Depends(get_db)):
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="账户未找到")
    
    transactions = db.query(Transaction).filter(
        Transaction.account_id == account_id
    ).order_by(Transaction.date).all()
    
    holdings = {}
    cash_flow = account.initial_capital
    
    for t in transactions:
        if t.type == 'buy':
            cash_flow -= t.quantity * t.price + t.fee
            if t.asset_id not in holdings:
                holdings[t.asset_id] = {'quantity': 0, 'total_cost': 0}
            holdings[t.asset_id]['quantity'] += t.quantity
            holdings[t.asset_id]['total_cost'] += t.quantity * t.price
        elif t.type == 'sell':
            cash_flow += t.quantity * t.price - t.fee
            if t.asset_id in holdings:
                avg_cost = holdings[t.asset_id]['total_cost'] / holdings[t.asset_id]['quantity'] if holdings[t.asset_id]['quantity'] > 0 else 0
                holdings[t.asset_id]['quantity'] -= t.quantity
                holdings[t.asset_id]['total_cost'] -= t.quantity * avg_cost
    
    holding_items = []
    position_value = 0
    
    for asset_id, holding in holdings.items():
        if holding['quantity'] > 0:
            asset = db.query(Asset).filter(Asset.id == asset_id).first()
            if asset:
                avg_cost = holding['total_cost'] / holding['quantity']
                
                latest_price = db.query(MarketData).filter(
                    MarketData.symbol == asset.symbol
                ).order_by(MarketData.date.desc()).first()
                
                current_price = latest_price.close if latest_price else None
                market_value = current_price * holding['quantity'] if current_price else None
                profit_loss = (current_price - avg_cost) * holding['quantity'] if current_price else None
                profit_loss_pct = ((current_price - avg_cost) / avg_cost * 100) if current_price and avg_cost > 0 else None
                
                if market_value:
                    position_value += market_value
                
                holding_items.append(HoldingItem(
                    symbol=asset.symbol,
                    name=asset.name,
                    quantity=round(holding['quantity'], 2),
                    avg_cost=round(avg_cost, 2),
                    current_price=round(current_price, 2) if current_price else None,
                    market_value=round(market_value, 2) if market_value else None,
                    profit_loss=round(profit_loss, 2) if profit_loss else None,
                    profit_loss_pct=round(profit_loss_pct, 2) if profit_loss_pct else None
                ))
    
    current_value = cash_flow + position_value
    total_profit_loss = current_value - account.initial_capital
    total_profit_loss_pct = (total_profit_loss / account.initial_capital * 100) if account.initial_capital > 0 else 0
    
    last_snapshot = db.query(PortfolioSnapshot).filter(
        PortfolioSnapshot.account_id == account_id
    ).order_by(PortfolioSnapshot.date.desc()).first()
    
    return AccountSummary(
        id=account.id,
        name=account.name,
        description=account.description,
        initial_capital=account.initial_capital,
        current_value=round(current_value, 2),
        cash=round(cash_flow, 2),
        position_value=round(position_value, 2),
        total_profit_loss=round(total_profit_loss, 2),
        total_profit_loss_pct=round(total_profit_loss_pct, 2),
        holdings=holding_items,
        transaction_count=len(transactions),
        last_updated=last_snapshot.date if last_snapshot else None
    )

@router.get("/{account_id}/transactions", response_model=List[TransactionResponse])
def get_account_transactions(
    account_id: int, 
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    transaction_type: Optional[str] = None,
    db: Session = Depends(get_db)
):
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="账户未找到")
    
    query = db.query(Transaction).filter(Transaction.account_id == account_id)
    
    if start_date:
        query = query.filter(Transaction.date >= start_date)
    if end_date:
        query = query.filter(Transaction.date <= end_date)
    if transaction_type:
        query = query.filter(Transaction.type == transaction_type)
    
    transactions = query.order_by(Transaction.date.desc()).all()
    
    result = []
    for t in transactions:
        asset = db.query(Asset).filter(Asset.id == t.asset_id).first()
        result.append(TransactionResponse(
            id=t.id,
            asset_id=t.asset_id,
            symbol=asset.symbol if asset else '',
            name=asset.name if asset else '',
            type=t.type,
            date=t.date,
            quantity=t.quantity,
            price=t.price,
            fee=t.fee,
            notes=t.notes
        ))
    
    return result

@router.get("/{account_id}/snapshots", response_model=List[PortfolioSnapshotResponse])
def get_account_snapshots(
    account_id: int,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    db: Session = Depends(get_db)
):
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="账户未找到")
    
    query = db.query(PortfolioSnapshot).filter(PortfolioSnapshot.account_id == account_id)
    
    if start_date:
        query = query.filter(PortfolioSnapshot.date >= start_date)
    if end_date:
        query = query.filter(PortfolioSnapshot.date <= end_date)
    
    return query.order_by(PortfolioSnapshot.date).all()

@router.post("/{account_id}/snapshots", response_model=PortfolioSnapshotResponse)
def create_snapshot(
    account_id: int, 
    snapshot: PortfolioSnapshotCreate,
    db: Session = Depends(get_db)
):
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="账户未找到")
    
    db_snapshot = PortfolioSnapshot(
        account_id=account_id,
        date=datetime.now(),
        total_value=snapshot.total_value,
        cash=snapshot.cash,
        position_value=snapshot.position_value,
        daily_return=snapshot.daily_return,
        notes=snapshot.notes
    )
    db.add(db_snapshot)
    db.commit()
    db.refresh(db_snapshot)
    return db_snapshot

@router.post("/{account_id}/snapshot-daily")
def create_daily_snapshot(account_id: int, db: Session = Depends(get_db)):
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="账户未找到")
    
    summary = get_account_summary(account_id, db)
    
    today = datetime.now().date()
    existing = db.query(PortfolioSnapshot).filter(
        PortfolioSnapshot.account_id == account_id,
        func.date(PortfolioSnapshot.date) == today
    ).first()
    
    if existing:
        existing.total_value = summary.current_value
        existing.cash = summary.cash
        existing.position_value = summary.position_value
        db.commit()
        return {"message": "快照已更新", "snapshot_id": existing.id}
    
    yesterday_snapshot = db.query(PortfolioSnapshot).filter(
        PortfolioSnapshot.account_id == account_id
    ).order_by(PortfolioSnapshot.date.desc()).first()
    
    daily_return = 0
    if yesterday_snapshot and yesterday_snapshot.total_value > 0:
        daily_return = (summary.current_value - yesterday_snapshot.total_value) / yesterday_snapshot.total_value * 100
    
    db_snapshot = PortfolioSnapshot(
        account_id=account_id,
        date=datetime.now(),
        total_value=summary.current_value,
        cash=summary.cash,
        position_value=summary.position_value,
        daily_return=round(daily_return, 4)
    )
    db.add(db_snapshot)
    db.commit()
    db.refresh(db_snapshot)
    
    return {"message": "快照已创建", "snapshot_id": db_snapshot.id}

@router.get("/{account_id}/performance")
def get_account_performance(account_id: int, days: int = 30, db: Session = Depends(get_db)):
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="账户未找到")
    
    start_date = datetime.now() - timedelta(days=days)
    
    snapshots = db.query(PortfolioSnapshot).filter(
        PortfolioSnapshot.account_id == account_id,
        PortfolioSnapshot.date >= start_date
    ).order_by(PortfolioSnapshot.date).all()
    
    if len(snapshots) < 2:
        return {
            "total_return": 0,
            "annualized_return": 0,
            "max_drawdown": 0,
            "volatility": 0,
            "sharpe_ratio": 0,
            "daily_returns": []
        }
    
    values = [s.total_value for s in snapshots]
    returns = [(values[i] - values[i-1]) / values[i-1] * 100 for i in range(1, len(values))]
    
    total_return = (values[-1] - values[0]) / values[0] * 100
    
    days_actual = (snapshots[-1].date - snapshots[0].date).days
    annualized_return = ((values[-1] / values[0]) ** (365 / max(days_actual, 1)) - 1) * 100 if days_actual > 0 else 0
    
    peak = values[0]
    max_drawdown = 0
    for v in values:
        if v > peak:
            peak = v
        drawdown = (peak - v) / peak * 100
        if drawdown > max_drawdown:
            max_drawdown = drawdown
    
    import numpy as np
    volatility = np.std(returns) * np.sqrt(252) if returns else 0
    sharpe_ratio = (np.mean(returns) * 252 / volatility) if volatility > 0 else 0
    
    return {
        "total_return": round(total_return, 2),
        "annualized_return": round(annualized_return, 2),
        "max_drawdown": round(max_drawdown, 2),
        "volatility": round(volatility, 2),
        "sharpe_ratio": round(sharpe_ratio, 2),
        "daily_returns": [
            {
                "date": snapshots[i+1].date.isoformat(),
                "return": round(returns[i], 4)
            } for i in range(len(returns))
        ]
    }
