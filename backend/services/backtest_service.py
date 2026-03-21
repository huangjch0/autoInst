import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from .strategy_service import TechnicalIndicators

class BacktestService:
    def __init__(self):
        self.indicators = TechnicalIndicators()
    
    def run_backtest(self, symbol: str, strategy_name: str, strategy_params: dict,
                    start_date: str, end_date: str, initial_capital: float,
                    db: Session) -> Dict:
        from backend.database import MarketData
        
        market_data = db.query(MarketData).filter(
            MarketData.symbol == symbol,
            MarketData.date >= start_date,
            MarketData.date <= end_date
        ).order_by(MarketData.date).all()
        
        if not market_data:
            return {
                "total_return": 0,
                "annual_return": 0,
                "max_drawdown": 0,
                "sharpe_ratio": 0,
                "win_rate": 0,
                "total_trades": 0,
                "profit_trades": 0,
                "loss_trades": 0,
                "trades": [],
                "portfolio_values": [],
                "benchmark_values": []
            }
        
        df = pd.DataFrame([{
            "date": m.date,
            "open": m.open,
            "high": m.high,
            "low": m.low,
            "close": m.close,
            "volume": m.volume
        } for m in market_data])
        
        signals = self._generate_signals(strategy_name, df, strategy_params)
        
        result = self._simulate_trading(df, signals, initial_capital)
        
        return result
    
    def _generate_signals(self, strategy_name: str, df: pd.DataFrame, params: dict) -> pd.DataFrame:
        signals = pd.DataFrame(index=df.index)
        signals["signal"] = 0
        signals["signal_strength"] = 0
        
        if strategy_name == "ma_cross":
            short_period = params.get("short_period", 5)
            long_period = params.get("long_period", 20)
            df["ma_short"] = self.indicators.sma(df["close"], short_period)
            df["ma_long"] = self.indicators.sma(df["close"], long_period)
            
            signals.loc[(df["ma_short"] > df["ma_long"]) & 
                       (df["ma_short"].shift(1) <= df["ma_long"].shift(1)), "signal"] = 1
            signals.loc[(df["ma_short"] < df["ma_long"]) & 
                       (df["ma_short"].shift(1) >= df["ma_long"].shift(1)), "signal"] = -1
        
        elif strategy_name == "rsi":
            period = params.get("period", 14)
            oversold = params.get("oversold", 30)
            overbought = params.get("overbought", 70)
            df["rsi"] = self.indicators.rsi(df["close"], period)
            
            signals.loc[df["rsi"] < oversold, "signal"] = 1
            signals.loc[df["rsi"] > overbought, "signal"] = -1
        
        elif strategy_name == "macd":
            macd_data = self.indicators.macd(df["close"])
            df["histogram"] = macd_data["histogram"]
            
            signals.loc[(df["histogram"] > 0) & (df["histogram"].shift(1) <= 0), "signal"] = 1
            signals.loc[(df["histogram"] < 0) & (df["histogram"].shift(1) >= 0), "signal"] = -1
        
        elif strategy_name == "bollinger":
            period = params.get("period", 20)
            std_dev = params.get("std_dev", 2)
            
            bb = self.indicators.bollinger_bands(df["close"], period, std_dev)
            df["bb_upper"] = bb["upper"]
            df["bb_lower"] = bb["lower"]
            
            signals.loc[df["close"] <= df["bb_lower"], "signal"] = 1
            signals.loc[df["close"] >= df["bb_upper"], "signal"] = -1
        
        elif strategy_name == "kdj":
            n = params.get("n", 9)
            m1 = params.get("m1", 3)
            m2 = params.get("m2", 3)
            
            kdj = self.indicators.kdj(df["high"], df["low"], df["close"], n, m1, m2)
            df["k"] = kdj["k"]
            df["d"] = kdj["d"]
            
            signals.loc[(df["k"] > df["d"]) & (df["k"].shift(1) <= df["d"].shift(1)), "signal"] = 1
            signals.loc[(df["k"] < df["d"]) & (df["k"].shift(1) >= df["d"].shift(1)), "signal"] = -1
        
        elif strategy_name == "time_series":
            signals = self._time_series_signals(df, params)
        
        return signals
    
    def _time_series_signals(self, df: pd.DataFrame, params: dict) -> pd.DataFrame:
        signals = pd.DataFrame(index=df.index)
        signals["signal"] = 0
        
        lookback = params.get("lookback", 20)
        threshold = params.get("threshold", 0.02)
        
        df["trend"] = df["close"].rolling(window=lookback).apply(
            lambda x: np.polyfit(np.arange(len(x)), x, 1)[0] if len(x) == lookback else 0
        )
        
        df["trend_pct"] = df["trend"] / df["close"]
        
        signals.loc[df["trend_pct"] > threshold / lookback, "signal"] = 1
        signals.loc[df["trend_pct"] < -threshold / lookback, "signal"] = -1
        
        signals["signal"] = signals["signal"].diff().fillna(0)
        signals.loc[signals["signal"] == 0, "signal"] = 0
        
        return signals
    
    def _simulate_trading(self, df: pd.DataFrame, signals: pd.DataFrame, 
                         initial_capital: float) -> Dict:
        capital = initial_capital
        position = 0
        trades = []
        portfolio_values = []
        benchmark_values = []
        benchmark_shares = initial_capital / df["close"].iloc[0]
        
        buy_points = []
        sell_points = []
        
        for i in range(len(df)):
            date = df["date"].iloc[i]
            close = df["close"].iloc[i]
            signal = signals["signal"].iloc[i]
            
            if signal == 1 and position == 0:
                shares = int(capital / close)
                if shares > 0:
                    position = shares
                    cost = shares * close
                    capital -= cost
                    trades.append({
                        "date": str(date),
                        "type": "buy",
                        "price": float(close),
                        "quantity": shares,
                        "value": float(cost)
                    })
                    buy_points.append({
                        "date": str(date),
                        "price": float(close),
                        "index": i
                    })
            
            elif signal == -1 and position > 0:
                revenue = position * close
                capital += revenue
                trades.append({
                    "date": str(date),
                    "type": "sell",
                    "price": float(close),
                    "quantity": position,
                    "value": float(revenue)
                })
                sell_points.append({
                    "date": str(date),
                    "price": float(close),
                    "index": i
                })
                position = 0
            
            portfolio_value = float(capital + position * close)
            benchmark_value = float(benchmark_shares * close)
            
            portfolio_values.append({
                "date": str(date),
                "value": portfolio_value,
                "cash": float(capital),
                "position_value": float(position * close),
                "close": float(close)
            })
            
            benchmark_values.append({
                "date": str(date),
                "value": benchmark_value
            })
        
        if position > 0:
            capital += position * df["close"].iloc[-1]
            position = 0
        
        final_value = capital
        total_return = (final_value - initial_capital) / initial_capital * 100
        
        days = (df["date"].iloc[-1] - df["date"].iloc[0]).days
        annual_return = ((final_value / initial_capital) ** (365 / max(days, 1)) - 1) * 100 if days > 0 else 0
        
        portfolio_series = pd.Series([v["value"] for v in portfolio_values])
        rolling_max = portfolio_series.cummax()
        drawdown = (portfolio_series - rolling_max) / rolling_max
        max_drawdown = drawdown.min() * 100
        
        returns = portfolio_series.pct_change().dropna()
        sharpe_ratio = (returns.mean() / returns.std() * np.sqrt(252)) * 100 if returns.std() > 0 else 0
        
        profit_trades = 0
        loss_trades = 0
        for i in range(0, len(trades) - 1, 2):
            if i + 1 < len(trades):
                buy_trade = trades[i]
                sell_trade = trades[i + 1]
                if buy_trade["type"] == "buy" and sell_trade["type"] == "sell":
                    profit = (sell_trade["price"] - buy_trade["price"]) * buy_trade["quantity"]
                    if profit > 0:
                        profit_trades += 1
                    else:
                        loss_trades += 1
        
        total_trades = profit_trades + loss_trades
        win_rate = (profit_trades / total_trades * 100) if total_trades > 0 else 0
        
        benchmark_return = (benchmark_values[-1]["value"] - initial_capital) / initial_capital * 100
        
        return {
            "total_return": round(total_return, 2),
            "annual_return": round(annual_return, 2),
            "max_drawdown": round(max_drawdown, 2),
            "sharpe_ratio": round(sharpe_ratio, 2),
            "win_rate": round(win_rate, 2),
            "total_trades": total_trades,
            "profit_trades": profit_trades,
            "loss_trades": loss_trades,
            "trades": trades,
            "portfolio_values": portfolio_values,
            "benchmark_values": benchmark_values,
            "buy_points": buy_points,
            "sell_points": sell_points,
            "benchmark_return": round(benchmark_return, 2),
            "initial_capital": initial_capital,
            "final_value": round(final_value, 2)
        }
