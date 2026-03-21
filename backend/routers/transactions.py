from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel
from backend.database import get_db, Transaction, Asset, Account

router = APIRouter(prefix="/api/transactions", tags=["transactions"])

class TransactionCreate(BaseModel):
    account_id: Optional[int] = None
    asset_id: int
    type: str
    date: datetime
    quantity: float
    price: float
    fee: float = 0
    notes: Optional[str] = None

class TransactionResponse(BaseModel):
    id: int
    account_id: Optional[int]
    asset_id: int
    type: str
    date: datetime
    quantity: float
    price: float
    fee: float
    notes: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True

class TransactionUpdate(BaseModel):
    type: Optional[str] = None
    date: Optional[datetime] = None
    quantity: Optional[float] = None
    price: Optional[float] = None
    fee: Optional[float] = None
    notes: Optional[str] = None

@router.get("/", response_model=List[TransactionResponse])
def get_transactions(
    account_id: Optional[int] = None,
    asset_id: Optional[int] = None,
    transaction_type: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db: Session = Depends(get_db)
):
    query = db.query(Transaction)
    if account_id:
        query = query.filter(Transaction.account_id == account_id)
    if asset_id:
        query = query.filter(Transaction.asset_id == asset_id)
    if transaction_type:
        query = query.filter(Transaction.type == transaction_type)
    if start_date:
        query = query.filter(Transaction.date >= start_date)
    if end_date:
        query = query.filter(Transaction.date <= end_date)
    return query.order_by(Transaction.date.desc()).all()

@router.get("/{transaction_id}", response_model=TransactionResponse)
def get_transaction(transaction_id: int, db: Session = Depends(get_db)):
    transaction = db.query(Transaction).filter(Transaction.id == transaction_id).first()
    if not transaction:
        raise HTTPException(status_code=404, detail="交易记录未找到")
    return transaction

@router.post("/", response_model=TransactionResponse)
def create_transaction(transaction: TransactionCreate, db: Session = Depends(get_db)):
    asset = db.query(Asset).filter(Asset.id == transaction.asset_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="资产未找到")
    if transaction.type not in ["buy", "sell"]:
        raise HTTPException(status_code=400, detail="交易类型必须是 buy 或 sell")
    
    if transaction.account_id:
        account = db.query(Account).filter(Account.id == transaction.account_id).first()
        if not account:
            raise HTTPException(status_code=404, detail="账户未找到")
    
    db_transaction = Transaction(**transaction.model_dump())
    db.add(db_transaction)
    db.commit()
    db.refresh(db_transaction)
    return db_transaction

@router.put("/{transaction_id}", response_model=TransactionResponse)
def update_transaction(transaction_id: int, transaction: TransactionUpdate, db: Session = Depends(get_db)):
    db_transaction = db.query(Transaction).filter(Transaction.id == transaction_id).first()
    if not db_transaction:
        raise HTTPException(status_code=404, detail="交易记录未找到")
    for key, value in transaction.model_dump(exclude_unset=True).items():
        setattr(db_transaction, key, value)
    db.commit()
    db.refresh(db_transaction)
    return db_transaction

@router.delete("/{transaction_id}")
def delete_transaction(transaction_id: int, db: Session = Depends(get_db)):
    db_transaction = db.query(Transaction).filter(Transaction.id == transaction_id).first()
    if not db_transaction:
        raise HTTPException(status_code=404, detail="交易记录未找到")
    db.delete(db_transaction)
    db.commit()
    return {"message": "交易记录已删除"}

@router.get("/holdings/summary")
def get_holdings_summary(account_id: Optional[int] = None, db: Session = Depends(get_db)):
    from sqlalchemy import func, case
    
    query = db.query(
        Asset.id,
        Asset.symbol,
        Asset.name,
        Asset.type,
        func.sum(case((Transaction.type == "buy", Transaction.quantity), else_=0)).label("buy_qty"),
        func.sum(case((Transaction.type == "sell", Transaction.quantity), else_=0)).label("sell_qty"),
        func.sum(case((Transaction.type == "buy", Transaction.quantity * Transaction.price), else_=0)).label("buy_amount"),
        func.sum(case((Transaction.type == "sell", Transaction.quantity * Transaction.price), else_=0)).label("sell_amount"),
        func.sum(Transaction.fee).label("total_fee")
    ).join(Transaction).group_by(Asset.id)
    
    if account_id:
        query = query.filter(Transaction.account_id == account_id)
    
    holdings = query.all()
    
    result = []
    for h in holdings:
        quantity = h.buy_qty - h.sell_qty
        if quantity > 0:
            avg_cost = (h.buy_amount - h.sell_amount) / quantity
            result.append({
                "asset_id": h.id,
                "symbol": h.symbol,
                "name": h.name,
                "type": h.type,
                "quantity": quantity,
                "avg_cost": avg_cost,
                "total_fee": h.total_fee or 0
            })
    return result
