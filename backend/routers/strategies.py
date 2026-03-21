from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel
import json
from backend.database import get_db, Strategy, Signal, Asset, Account

router = APIRouter(prefix="/api/strategies", tags=["strategies"])

class StrategyCreate(BaseModel):
    account_id: Optional[int] = None
    name: str
    description: Optional[str] = None
    params: dict

class StrategyResponse(BaseModel):
    id: int
    account_id: Optional[int]
    name: str
    description: Optional[str]
    params_json: str
    is_active: int
    auto_run: int = 0
    run_interval_minutes: int = 60
    last_run_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class StrategyUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    params: Optional[dict] = None
    is_active: Optional[int] = None
    auto_run: Optional[int] = None
    run_interval_minutes: Optional[int] = None

class SignalCreate(BaseModel):
    strategy_id: int
    asset_id: int
    signal_type: str
    price: Optional[float] = None
    reason: Optional[str] = None

class SignalResponse(BaseModel):
    id: int
    strategy_id: Optional[int]
    asset_id: Optional[int]
    symbol: Optional[str] = None
    asset_name: Optional[str] = None
    signal_type: str
    price: Optional[float]
    reason: Optional[str]
    status: str
    user_response: Optional[str]
    response_time: Optional[datetime]
    created_at: datetime
    
    class Config:
        from_attributes = True

class SignalApproval(BaseModel):
    approved: bool
    notes: Optional[str] = None
    quantity: Optional[int] = None

@router.get("/", response_model=List[StrategyResponse])
def get_strategies(account_id: Optional[int] = None, db: Session = Depends(get_db)):
    query = db.query(Strategy)
    if account_id:
        query = query.filter(Strategy.account_id == account_id)
    return query.all()

@router.get("/list/signals")
def get_signals(
    status: Optional[str] = None,
    strategy_id: Optional[int] = None,
    account_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    query = db.query(Signal)
    if status:
        query = query.filter(Signal.status == status)
    if strategy_id:
        query = query.filter(Signal.strategy_id == strategy_id)
    if account_id:
        strategy_ids = [s.id for s in db.query(Strategy).filter(Strategy.account_id == account_id).all()]
        query = query.filter(Signal.strategy_id.in_(strategy_ids))
    
    signals = query.order_by(Signal.created_at.desc()).all()
    result = []
    for s in signals:
        asset = db.query(Asset).filter(Asset.id == s.asset_id).first() if s.asset_id else None
        result.append({
            "id": s.id,
            "strategy_id": s.strategy_id,
            "asset_id": s.asset_id,
            "symbol": asset.symbol if asset else None,
            "asset_name": asset.name if asset else None,
            "signal_type": s.signal_type,
            "price": s.price,
            "suggested_quantity": s.suggested_quantity,
            "reason": s.reason,
            "status": s.status,
            "user_response": s.user_response,
            "response_time": s.response_time,
            "created_at": s.created_at
        })
    return result

@router.get("/{strategy_id}", response_model=StrategyResponse)
def get_strategy(strategy_id: int, db: Session = Depends(get_db)):
    strategy = db.query(Strategy).filter(Strategy.id == strategy_id).first()
    if not strategy:
        raise HTTPException(status_code=404, detail="策略未找到")
    return strategy

@router.post("/", response_model=StrategyResponse)
def create_strategy(strategy: StrategyCreate, db: Session = Depends(get_db)):
    if strategy.account_id:
        account = db.query(Account).filter(Account.id == strategy.account_id).first()
        if not account:
            raise HTTPException(status_code=404, detail="账户未找到")
    
    db_strategy = Strategy(
        account_id=strategy.account_id,
        name=strategy.name,
        description=strategy.description,
        params_json=json.dumps(strategy.params, ensure_ascii=False)
    )
    db.add(db_strategy)
    db.commit()
    db.refresh(db_strategy)
    return db_strategy

@router.put("/{strategy_id}", response_model=StrategyResponse)
def update_strategy(strategy_id: int, strategy: StrategyUpdate, db: Session = Depends(get_db)):
    db_strategy = db.query(Strategy).filter(Strategy.id == strategy_id).first()
    if not db_strategy:
        raise HTTPException(status_code=404, detail="策略未找到")
    if strategy.name:
        db_strategy.name = strategy.name
    if strategy.description is not None:
        db_strategy.description = strategy.description
    if strategy.params:
        db_strategy.params_json = json.dumps(strategy.params, ensure_ascii=False)
    if strategy.is_active is not None:
        db_strategy.is_active = strategy.is_active
    if strategy.auto_run is not None:
        db_strategy.auto_run = strategy.auto_run
    if strategy.run_interval_minutes is not None:
        db_strategy.run_interval_minutes = strategy.run_interval_minutes
    db.commit()
    db.refresh(db_strategy)
    return db_strategy

@router.delete("/{strategy_id}")
def delete_strategy(strategy_id: int, db: Session = Depends(get_db)):
    db_strategy = db.query(Strategy).filter(Strategy.id == strategy_id).first()
    if not db_strategy:
        raise HTTPException(status_code=404, detail="策略未找到")
    db.delete(db_strategy)
    db.commit()
    return {"message": "策略已删除"}

@router.post("/{strategy_id}/run")
def run_strategy(strategy_id: int, db: Session = Depends(get_db)):
    from backend.services.strategy_service import StrategyService
    strategy = db.query(Strategy).filter(Strategy.id == strategy_id).first()
    if not strategy:
        raise HTTPException(status_code=404, detail="策略未找到")
    
    service = StrategyService()
    signals = service.run_strategy(strategy, db)
    return {"message": f"策略执行完成，生成 {len(signals)} 个信号", "signals": signals}

@router.post("/signals/{signal_id}/approve")
def approve_signal(signal_id: int, approval: SignalApproval, db: Session = Depends(get_db)):
    signal = db.query(Signal).filter(Signal.id == signal_id).first()
    if not signal:
        raise HTTPException(status_code=404, detail="信号未找到")
    
    signal.status = "approved" if approval.approved else "rejected"
    signal.user_response = approval.notes
    signal.response_time = datetime.now()
    
    if approval.approved and signal.signal_type in ["buy", "sell"]:
        from backend.database import Transaction, Account
        asset = db.query(Asset).filter(Asset.id == signal.asset_id).first()
        strategy = db.query(Strategy).filter(Strategy.id == signal.strategy_id).first() if signal.strategy_id else None
        if asset:
            if approval.quantity is not None:
                final_qty = approval.quantity
            elif signal.suggested_quantity:
                final_qty = signal.suggested_quantity
            else:
                final_qty = 100 if signal.signal_type == "buy" else 0
            
            if signal.signal_type == "buy" and strategy and strategy.account_id:
                account = db.query(Account).filter(Account.id == strategy.account_id).first()
                if account:
                    transactions = db.query(Transaction).filter(
                        Transaction.account_id == strategy.account_id
                    ).all()
                    
                    cash = account.initial_capital
                    for t in transactions:
                        if t.type == "buy":
                            cash -= t.quantity * t.price + t.fee
                        elif t.type == "sell":
                            cash += t.quantity * t.price - t.fee
                    
                    required_amount = final_qty * (signal.price or 0)
                    if cash < required_amount:
                        signal.status = "rejected"
                        signal.user_response = f"资金不足: 需要 ¥{required_amount:.2f}，可用 ¥{cash:.2f}"
                        db.commit()
                        raise HTTPException(
                            status_code=400, 
                            detail=f"资金不足: 需要 ¥{required_amount:.2f}，可用 ¥{cash:.2f}"
                        )
            
            transaction = Transaction(
                account_id=strategy.account_id if strategy else None,
                asset_id=signal.asset_id,
                type=signal.signal_type,
                date=datetime.now(),
                quantity=final_qty,
                price=signal.price or 0,
                fee=0,
                notes=f"由策略信号自动创建: {signal.reason}"
            )
            db.add(transaction)
    
    db.commit()
    return {"message": "信号已处理", "status": signal.status}
