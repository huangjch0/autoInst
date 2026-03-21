from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime
from pydantic import BaseModel
from backend.database import get_db
from backend.services.backtest_service import BacktestService

router = APIRouter(prefix="/api/backtest", tags=["backtest"])

class BacktestRequest(BaseModel):
    symbol: str
    strategy_name: str
    strategy_params: dict
    start_date: str
    end_date: str
    initial_capital: float = 100000

class BacktestResult(BaseModel):
    total_return: float
    annual_return: float
    max_drawdown: float
    sharpe_ratio: float
    win_rate: float
    total_trades: int
    profit_trades: int
    loss_trades: int
    trades: list
    portfolio_values: list = []
    benchmark_values: list = []
    buy_points: list = []
    sell_points: list = []
    benchmark_return: float = 0
    initial_capital: float = 100000
    final_value: float = 0

@router.post("/run", response_model=BacktestResult)
def run_backtest(request: BacktestRequest, db: Session = Depends(get_db)):
    service = BacktestService()
    result = service.run_backtest(
        symbol=request.symbol,
        strategy_name=request.strategy_name,
        strategy_params=request.strategy_params,
        start_date=request.start_date,
        end_date=request.end_date,
        initial_capital=request.initial_capital,
        db=db
    )
    return result
