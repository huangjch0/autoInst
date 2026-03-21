from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel
from backend.database import get_db, MarketData, Asset
from backend.services.market_service import MarketService
import pandas as pd
import asyncio

router = APIRouter(prefix="/api/market", tags=["market"])

class MarketDataResponse(BaseModel):
    id: int
    symbol: str
    date: datetime
    open: Optional[float]
    high: Optional[float]
    low: Optional[float]
    close: Optional[float]
    volume: Optional[float]
    
    class Config:
        from_attributes = True

class RealtimeQuote(BaseModel):
    symbol: str
    name: str
    price: float
    change: float
    change_percent: float
    volume: Optional[float]
    timestamp: datetime

class PredictionResponse(BaseModel):
    direction: str
    confidence: float
    predicted_price: Optional[float]
    reason: str
    strategy: str
    indicators: Optional[dict] = None
    vote_summary: Optional[dict] = None
    individual_predictions: Optional[List[dict]] = None

class StrategyInfo(BaseModel):
    name: str
    description: str

class BatchUpdateResult(BaseModel):
    symbol: str
    name: str
    success: bool
    count: int
    message: str

class BatchUpdateResponse(BaseModel):
    total: int
    success: int
    failed: int
    results: List[BatchUpdateResult]

@router.get("/quote/{symbol}", response_model=RealtimeQuote)
def get_realtime_quote(symbol: str):
    try:
        service = MarketService()
        quote = service.get_realtime_quote(symbol)
        if not quote:
            raise HTTPException(status_code=404, detail="无法获取行情数据")
        return quote
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/history/{symbol}", response_model=List[MarketDataResponse])
def get_history_data(
    symbol: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(MarketData).filter(MarketData.symbol == symbol)
    if start_date:
        query = query.filter(MarketData.date >= start_date)
    if end_date:
        query = query.filter(MarketData.date <= end_date)
    return query.order_by(MarketData.date).all()

@router.post("/fetch/{symbol}")
def fetch_and_save_market_data(
    symbol: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    datasource: str = "tencent",
    db: Session = Depends(get_db)
):
    try:
        service = MarketService()
        data = service.fetch_history_data(symbol, start_date, end_date, datasource)
        if not data:
            raise HTTPException(status_code=404, detail="无法获取历史数据")
        
        saved_count = 0
        for item in data:
            existing = db.query(MarketData).filter(
                MarketData.symbol == symbol,
                MarketData.date == item["date"]
            ).first()
            if existing:
                existing.open = item.get("open")
                existing.high = item.get("high")
                existing.low = item.get("low")
                existing.close = item.get("close")
                existing.volume = item.get("volume")
            else:
                db_data = MarketData(
                    symbol=symbol,
                    date=item["date"],
                    open=item.get("open"),
                    high=item.get("high"),
                    low=item.get("low"),
                    close=item.get("close"),
                    volume=item.get("volume")
                )
                db.add(db_data)
            saved_count += 1
        db.commit()
        return {"message": f"成功保存 {saved_count} 条数据", "count": saved_count}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/fetch-all", response_model=BatchUpdateResponse)
def fetch_all_market_data(
    background_tasks: BackgroundTasks,
    datasource: str = "tencent",
    db: Session = Depends(get_db)
):
    assets = db.query(Asset).all()
    
    if not assets:
        return BatchUpdateResponse(total=0, success=0, failed=0, results=[])
    
    results = []
    service = MarketService()
    
    for asset in assets:
        try:
            data = service.fetch_history_data(asset.symbol, datasource=datasource)
            if data:
                saved_count = 0
                for item in data:
                    existing = db.query(MarketData).filter(
                        MarketData.symbol == asset.symbol,
                        MarketData.date == item["date"]
                    ).first()
                    if existing:
                        existing.open = item.get("open")
                        existing.high = item.get("high")
                        existing.low = item.get("low")
                        existing.close = item.get("close")
                        existing.volume = item.get("volume")
                    else:
                        db_data = MarketData(
                            symbol=asset.symbol,
                            date=item["date"],
                            open=item.get("open"),
                            high=item.get("high"),
                            low=item.get("low"),
                            close=item.get("close"),
                            volume=item.get("volume")
                        )
                        db.add(db_data)
                    saved_count += 1
                db.commit()
                results.append(BatchUpdateResult(
                    symbol=asset.symbol,
                    name=asset.name,
                    success=True,
                    count=saved_count,
                    message=f"成功更新 {saved_count} 条数据"
                ))
            else:
                results.append(BatchUpdateResult(
                    symbol=asset.symbol,
                    name=asset.name,
                    success=False,
                    count=0,
                    message="无法获取数据"
                ))
        except Exception as e:
            results.append(BatchUpdateResult(
                symbol=asset.symbol,
                name=asset.name,
                success=False,
                count=0,
                message=str(e)
            ))
    
    success_count = sum(1 for r in results if r.success)
    failed_count = len(results) - success_count
    
    return BatchUpdateResponse(
        total=len(results),
        success=success_count,
        failed=failed_count,
        results=results
    )

@router.get("/predict/{symbol}", response_model=PredictionResponse)
def predict_stock(
    symbol: str, 
    strategy: str = "ensemble",
    db: Session = Depends(get_db)
):
    try:
        market_data = db.query(MarketData).filter(
            MarketData.symbol == symbol
        ).order_by(MarketData.date).all()
        
        if len(market_data) < 30:
            raise HTTPException(status_code=400, detail="数据不足，至少需要30条数据才能预测")
        
        df = pd.DataFrame([{
            "date": m.date,
            "open": m.open,
            "high": m.high,
            "low": m.low,
            "close": m.close,
            "volume": m.volume
        } for m in market_data])
        
        from backend.services.prediction_service import PredictionService
        service = PredictionService()
        prediction = service.predict(df, strategy)
        
        return prediction
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/search")
def search_stock(keyword: str):
    try:
        service = MarketService()
        results = service.search_stock(keyword)
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/predict-strategies", response_model=List[StrategyInfo])
def get_prediction_strategies():
    from backend.services.prediction_service import PredictionService
    service = PredictionService()
    return service.get_available_strategies()

@router.get("/history-with-indicators/{symbol}")
def get_history_with_indicators(
    symbol: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(MarketData).filter(MarketData.symbol == symbol)
    if start_date:
        query = query.filter(MarketData.date >= start_date)
    if end_date:
        query = query.filter(MarketData.date <= end_date)
    
    market_data = query.order_by(MarketData.date).all()
    
    if not market_data:
        return []
    
    df = pd.DataFrame([{
        "date": m.date,
        "open": m.open,
        "high": m.high,
        "low": m.low,
        "close": m.close,
        "volume": m.volume
    } for m in market_data])
    
    df['ma_5'] = df['close'].rolling(window=5).mean()
    df['ma_10'] = df['close'].rolling(window=10).mean()
    df['ma_20'] = df['close'].rolling(window=20).mean()
    df['ma_60'] = df['close'].rolling(window=60).mean()
    
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['rsi'] = 100 - (100 / (1 + rs))
    
    ema_12 = df['close'].ewm(span=12, adjust=False).mean()
    ema_26 = df['close'].ewm(span=26, adjust=False).mean()
    df['macd'] = ema_12 - ema_26
    df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
    df['macd_hist'] = df['macd'] - df['macd_signal']
    
    bb_middle = df['close'].rolling(window=20).mean()
    bb_std = df['close'].rolling(window=20).std()
    df['bb_upper'] = bb_middle + 2 * bb_std
    df['bb_lower'] = bb_middle - 2 * bb_std
    
    result = []
    for _, row in df.iterrows():
        item = {
            "date": row['date'].isoformat() if pd.notna(row['date']) else None,
            "open": round(row['open'], 2) if pd.notna(row['open']) else None,
            "high": round(row['high'], 2) if pd.notna(row['high']) else None,
            "low": round(row['low'], 2) if pd.notna(row['low']) else None,
            "close": round(row['close'], 2) if pd.notna(row['close']) else None,
            "volume": int(row['volume']) if pd.notna(row['volume']) else None,
            "ma_5": round(row['ma_5'], 2) if pd.notna(row['ma_5']) else None,
            "ma_10": round(row['ma_10'], 2) if pd.notna(row['ma_10']) else None,
            "ma_20": round(row['ma_20'], 2) if pd.notna(row['ma_20']) else None,
            "ma_60": round(row['ma_60'], 2) if pd.notna(row['ma_60']) else None,
            "rsi": round(row['rsi'], 2) if pd.notna(row['rsi']) else None,
            "macd": round(row['macd'], 4) if pd.notna(row['macd']) else None,
            "macd_signal": round(row['macd_signal'], 4) if pd.notna(row['macd_signal']) else None,
            "macd_hist": round(row['macd_hist'], 4) if pd.notna(row['macd_hist']) else None,
            "bb_upper": round(row['bb_upper'], 2) if pd.notna(row['bb_upper']) else None,
            "bb_lower": round(row['bb_lower'], 2) if pd.notna(row['bb_lower']) else None,
        }
        result.append(item)
    
    return result
