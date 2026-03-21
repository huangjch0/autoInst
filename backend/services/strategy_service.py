import pandas as pd
import numpy as np
from typing import List, Dict, Optional
from datetime import datetime
import json
import logging
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

class TechnicalIndicators:
    @staticmethod
    def sma(data: pd.Series, period: int) -> pd.Series:
        return data.rolling(window=period).mean()
    
    @staticmethod
    def ema(data: pd.Series, period: int) -> pd.Series:
        return data.ewm(span=period, adjust=False).mean()
    
    @staticmethod
    def rsi(data: pd.Series, period: int = 14) -> pd.Series:
        delta = data.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))
    
    @staticmethod
    def macd(data: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> Dict:
        ema_fast = data.ewm(span=fast, adjust=False).mean()
        ema_slow = data.ewm(span=slow, adjust=False).mean()
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal, adjust=False).mean()
        histogram = macd_line - signal_line
        return {
            "macd": macd_line,
            "signal": signal_line,
            "histogram": histogram
        }
    
    @staticmethod
    def bollinger_bands(data: pd.Series, period: int = 20, std_dev: float = 2) -> Dict:
        middle = data.rolling(window=period).mean()
        std = data.rolling(window=period).std()
        upper = middle + (std * std_dev)
        lower = middle - (std * std_dev)
        return {
            "upper": upper,
            "middle": middle,
            "lower": lower
        }
    
    @staticmethod
    def kdj(high: pd.Series, low: pd.Series, close: pd.Series, 
            n: int = 9, m1: int = 3, m2: int = 3) -> Dict:
        low_min = low.rolling(window=n).min()
        high_max = high.rolling(window=n).max()
        rsv = (close - low_min) / (high_max - low_min) * 100
        k = rsv.ewm(alpha=1/m1, adjust=False).mean()
        d = k.ewm(alpha=1/m2, adjust=False).mean()
        j = 3 * k - 2 * d
        return {"k": k, "d": d, "j": j}

class StrategyService:
    def __init__(self):
        self.indicators = TechnicalIndicators()
    
    def _calculate_suggested_quantity(self, signal_type: str, price: float, account_id: int, db: Session) -> int:
        from backend.database import Account, Transaction, Asset
        
        if signal_type == "sell":
            return 0
        
        account = db.query(Account).filter(Account.id == account_id).first()
        if not account:
            return 100
        
        transactions = db.query(Transaction).filter(
            Transaction.account_id == account_id
        ).all()
        
        total_buy = sum(t.quantity * t.price for t in transactions if t.type == "buy")
        total_sell = sum(t.quantity * t.price for t in transactions if t.type == "sell")
        position_value = total_buy - total_sell
        
        cash = account.initial_capital - position_value
        
        position_ratio = 0.1
        available_for_trade = cash * position_ratio
        
        if price <= 0:
            return 100
        
        quantity = int(available_for_trade / price / 100) * 100
        
        return max(quantity, 100)
    
    def run_strategy(self, strategy, db: Session) -> List[Dict]:
        params = json.loads(strategy.params_json) if isinstance(strategy.params_json, str) else strategy.params_json
        strategy_name = params.get("name", "ma_cross")
        
        from backend.database import Asset, MarketData, Signal
        
        assets = db.query(Asset).all()
        signals = []
        
        for asset in assets:
            existing_pending = db.query(Signal).filter(
                Signal.strategy_id == strategy.id,
                Signal.asset_id == asset.id,
                Signal.status == "pending"
            ).first()
            
            if existing_pending:
                signals.append({
                    "id": existing_pending.id,
                    "symbol": asset.symbol,
                    "name": asset.name,
                    "signal_type": existing_pending.signal_type,
                    "price": existing_pending.price,
                    "suggested_quantity": existing_pending.suggested_quantity,
                    "reason": f"[已存在待处理信号] {existing_pending.reason}"
                })
                continue
            
            market_data = db.query(MarketData).filter(
                MarketData.symbol == asset.symbol
            ).order_by(MarketData.date).all()
            
            if len(market_data) < 30:
                continue
            
            df = pd.DataFrame([{
                "date": m.date,
                "open": m.open,
                "high": m.high,
                "low": m.low,
                "close": m.close,
                "volume": m.volume
            } for m in market_data])
            
            signal = self._generate_signal(strategy_name, df, params)
            
            if signal:
                signal_type = signal["type"]
                current_price = df["close"].iloc[-1]
                signal_info = {
                    "symbol": asset.symbol,
                    "name": asset.name,
                    "signal_type": signal_type,
                    "price": current_price,
                    "reason": signal["reason"],
                    "analysis": signal.get("analysis", {})
                }
                
                if signal_type in ["buy", "sell"]:
                    suggested_qty = self._calculate_suggested_quantity(
                        signal_type, current_price, strategy.account_id, db
                    )
                    
                    db_signal = Signal(
                        strategy_id=strategy.id,
                        asset_id=asset.id,
                        signal_type=signal_type,
                        price=current_price,
                        suggested_quantity=suggested_qty,
                        reason=signal["reason"]
                    )
                    db.add(db_signal)
                    db.commit()
                    db.refresh(db_signal)
                    signal_info["id"] = db_signal.id
                    signal_info["suggested_quantity"] = suggested_qty
                    logger.info(f"[审批请求] {asset.symbol} {signal_type.upper()} 信号: {signal['reason']}")
                else:
                    logger.info(f"[观望信号] {asset.symbol}: {signal['reason']}")
                
                signals.append(signal_info)
        
        return signals
    
    def _generate_signal(self, strategy_name: str, df: pd.DataFrame, params: dict) -> Optional[Dict]:
        strategy_map = {
            "ma_cross": self._ma_cross_strategy,
            "rsi": self._rsi_strategy,
            "macd": self._macd_strategy,
            "bollinger": self._bollinger_strategy,
            "kdj": self._kdj_strategy,
            "time_series": self._time_series_strategy,
            "prediction_ensemble": self._prediction_ensemble_strategy
        }
        
        if strategy_name in strategy_map:
            return strategy_map[strategy_name](df, params)
        return None
    
    def _ma_cross_strategy(self, df: pd.DataFrame, params: dict) -> Optional[Dict]:
        short_period = params.get("short_period", 5)
        long_period = params.get("long_period", 20)
        
        df["ma_short"] = self.indicators.sma(df["close"], short_period)
        df["ma_long"] = self.indicators.sma(df["close"], long_period)
        
        if len(df) < 2:
            return None
        
        prev_short = df["ma_short"].iloc[-2]
        prev_long = df["ma_long"].iloc[-2]
        curr_short = df["ma_short"].iloc[-1]
        curr_long = df["ma_long"].iloc[-1]
        curr_close = df["close"].iloc[-1]
        
        if pd.isna(prev_short) or pd.isna(prev_long) or pd.isna(curr_short) or pd.isna(curr_long):
            return None
        
        ma_diff = ((curr_short - curr_long) / curr_long) * 100
        
        if prev_short <= prev_long and curr_short > curr_long:
            return {"type": "buy", "reason": f"MA{short_period}上穿MA{long_period}，金叉买入信号，当前价{curr_close:.2f}"}
        elif prev_short >= prev_long and curr_short < curr_long:
            return {"type": "sell", "reason": f"MA{short_period}下穿MA{long_period}，死叉卖出信号，当前价{curr_close:.2f}"}
        elif curr_short > curr_long:
            return {"type": "hold", "reason": f"多头排列，短期均线在长期均线上方{ma_diff:.2f}%，趋势看涨，建议持有或逢低买入"}
        else:
            return {"type": "hold", "reason": f"空头排列，短期均线在长期均线下方{abs(ma_diff):.2f}%，趋势看跌，建议观望或减仓"}
    
    def _rsi_strategy(self, df: pd.DataFrame, params: dict) -> Optional[Dict]:
        period = params.get("period", 14)
        oversold = params.get("oversold", 30)
        overbought = params.get("overbought", 70)
        
        df["rsi"] = self.indicators.rsi(df["close"], period)
        
        if len(df) < 2:
            return None
        
        curr_rsi = df["rsi"].iloc[-1]
        prev_rsi = df["rsi"].iloc[-2] if len(df) > 1 else curr_rsi
        
        if pd.isna(curr_rsi):
            return None
        
        if curr_rsi < oversold:
            return {"type": "buy", "reason": f"RSI={curr_rsi:.1f}处于超卖区域(<{oversold})，反弹概率大，买入信号"}
        elif curr_rsi > overbought:
            return {"type": "sell", "reason": f"RSI={curr_rsi:.1f}处于超买区域(>{overbought})，回调风险高，卖出信号"}
        elif curr_rsi < 40:
            return {"type": "hold", "reason": f"RSI={curr_rsi:.1f}偏弱，接近超卖区，可关注买入机会"}
        elif curr_rsi > 60:
            return {"type": "hold", "reason": f"RSI={curr_rsi:.1f}偏强，接近超买区，注意回调风险"}
        else:
            rsi_trend = "上升" if curr_rsi > prev_rsi else "下降"
            return {"type": "hold", "reason": f"RSI={curr_rsi:.1f}处于中性区域，趋势{rsi_trend}，建议观望"}
    
    def _macd_strategy(self, df: pd.DataFrame, params: dict) -> Optional[Dict]:
        fast = params.get("fast", 12)
        slow = params.get("slow", 26)
        signal = params.get("signal", 9)
        
        macd_data = self.indicators.macd(df["close"], fast, slow, signal)
        df["macd"] = macd_data["macd"]
        df["signal_line"] = macd_data["signal"]
        df["histogram"] = macd_data["histogram"]
        
        if len(df) < 2:
            return None
        
        prev_hist = df["histogram"].iloc[-2]
        curr_hist = df["histogram"].iloc[-1]
        curr_macd = df["macd"].iloc[-1]
        curr_signal = df["signal_line"].iloc[-1]
        
        if pd.isna(prev_hist) or pd.isna(curr_hist):
            return None
        
        if prev_hist <= 0 and curr_hist > 0:
            return {"type": "buy", "reason": f"MACD柱状图由负转正，金叉买入信号，MACD={curr_macd:.3f}"}
        elif prev_hist >= 0 and curr_hist < 0:
            return {"type": "sell", "reason": f"MACD柱状图由正转负，死叉卖出信号，MACD={curr_macd:.3f}"}
        elif curr_macd > curr_signal and curr_hist > 0:
            return {"type": "hold", "reason": f"MACD在零轴上方运行，多头趋势，柱状图={curr_hist:.3f}，建议持有"}
        elif curr_macd < curr_signal and curr_hist < 0:
            return {"type": "hold", "reason": f"MACD在零轴下方运行，空头趋势，柱状图={curr_hist:.3f}，建议观望"}
        else:
            hist_trend = "增强" if curr_hist > prev_hist else "减弱"
            return {"type": "hold", "reason": f"MACD动能{hist_trend}，柱状图={curr_hist:.3f}，等待明确信号"}
    
    def _bollinger_strategy(self, df: pd.DataFrame, params: dict) -> Optional[Dict]:
        period = params.get("period", 20)
        std_dev = params.get("std_dev", 2)
        
        bb = self.indicators.bollinger_bands(df["close"], period, std_dev)
        df["bb_upper"] = bb["upper"]
        df["bb_lower"] = bb["lower"]
        df["bb_middle"] = bb["middle"]
        
        if len(df) < 1:
            return None
        
        curr_close = df["close"].iloc[-1]
        curr_upper = df["bb_upper"].iloc[-1]
        curr_lower = df["bb_lower"].iloc[-1]
        curr_middle = df["bb_middle"].iloc[-1]
        
        if pd.isna(curr_upper) or pd.isna(curr_lower):
            return None
        
        bb_width = ((curr_upper - curr_lower) / curr_middle) * 100
        bb_position = ((curr_close - curr_lower) / (curr_upper - curr_lower)) * 100
        
        if curr_close <= curr_lower:
            return {"type": "buy", "reason": f"价格触及布林带下轨{curr_lower:.2f}，超卖反弹信号，当前价{curr_close:.2f}"}
        elif curr_close >= curr_upper:
            return {"type": "sell", "reason": f"价格触及布林带上轨{curr_upper:.2f}，超买回调信号，当前价{curr_close:.2f}"}
        elif curr_close > curr_middle:
            return {"type": "hold", "reason": f"价格在中轨上方，多头区域，布林位置{bb_position:.1f}%，建议持有"}
        else:
            return {"type": "hold", "reason": f"价格在中轨下方，空头区域，布林位置{bb_position:.1f}%，建议观望"}
    
    def _kdj_strategy(self, df: pd.DataFrame, params: dict) -> Optional[Dict]:
        n = params.get("n", 9)
        m1 = params.get("m1", 3)
        m2 = params.get("m2", 3)
        
        kdj = self.indicators.kdj(df["high"], df["low"], df["close"], n, m1, m2)
        df["k"] = kdj["k"]
        df["d"] = kdj["d"]
        df["j"] = kdj["j"]
        
        if len(df) < 2:
            return None
        
        prev_k = df["k"].iloc[-2]
        prev_d = df["d"].iloc[-2]
        curr_k = df["k"].iloc[-1]
        curr_d = df["d"].iloc[-1]
        curr_j = df["j"].iloc[-1]
        
        if pd.isna(prev_k) or pd.isna(prev_d) or pd.isna(curr_k) or pd.isna(curr_d):
            return None
        
        if prev_k <= prev_d and curr_k > curr_d and curr_k < 20:
            return {"type": "buy", "reason": f"KDJ金叉且K值={curr_k:.1f}在超卖区(<20)，强烈买入信号"}
        elif prev_k >= prev_d and curr_k < curr_d and curr_k > 80:
            return {"type": "sell", "reason": f"KDJ死叉且K值={curr_k:.1f}在超买区(>80)，强烈卖出信号"}
        elif curr_k > curr_d:
            if curr_k < 30:
                return {"type": "hold", "reason": f"KDJ金叉形成中，K={curr_k:.1f}在低位，可关注买入机会"}
            else:
                return {"type": "hold", "reason": f"KDJ多头排列，K={curr_k:.1f}>D={curr_d:.1f}，趋势向上，建议持有"}
        else:
            if curr_k > 70:
                return {"type": "hold", "reason": f"KDJ死叉形成中，K={curr_k:.1f}在高位，注意卖出信号"}
            else:
                return {"type": "hold", "reason": f"KDJ空头排列，K={curr_k:.1f}<D={curr_d:.1f}，趋势向下，建议观望"}
    
    def _time_series_strategy(self, df: pd.DataFrame, params: dict) -> Optional[Dict]:
        lookback = params.get("lookback", 20)
        threshold = params.get("threshold", 0.02)
        
        if len(df) < lookback:
            return {"type": "hold", "reason": "数据不足"}
        
        prices = df['close'].values[-lookback:]
        
        trend = np.polyfit(np.arange(len(prices)), prices, 1)[0]
        trend_pct = trend / prices[-1]
        
        log_returns = np.diff(np.log(prices))
        volatility = np.std(log_returns)
        
        weights = np.exp(np.linspace(0, 1, len(log_returns)))
        weights = weights / weights.sum()
        weighted_return = np.sum(log_returns * weights)
        
        signal = "hold"
        reason_parts = []
        
        if trend_pct > threshold / lookback:
            signal = "buy"
            reason_parts.append(f"上升趋势(斜率={trend_pct*100:.3f}%/天)")
        elif trend_pct < -threshold / lookback:
            signal = "sell"
            reason_parts.append(f"下降趋势(斜率={trend_pct*100:.3f}%/天)")
        
        if weighted_return > 0.005:
            reason_parts.append(f"加权收益率为正({weighted_return*100:.2f}%)")
        elif weighted_return < -0.005:
            reason_parts.append(f"加权收益率为负({weighted_return*100:.2f}%)")
        
        if volatility > 0.03:
            reason_parts.append(f"高波动率({volatility*100:.2f}%)")
        
        if not reason_parts:
            reason_parts.append("时序分析无明确信号")
        
        return {"type": signal, "reason": " | ".join(reason_parts)}
    
    def _prediction_ensemble_strategy(self, df: pd.DataFrame, params: dict) -> Optional[Dict]:
        try:
            from backend.services.prediction_service import PredictionService
            
            prediction_service = PredictionService()
            prediction = prediction_service.predict(df, "ensemble")
            
            signal = "hold"
            if prediction["direction"] == "up" and prediction["confidence"] > 0.6:
                signal = "buy"
            elif prediction["direction"] == "down" and prediction["confidence"] > 0.6:
                signal = "sell"
            
            return {
                "type": signal,
                "reason": f"综合预测: {prediction['direction']} (置信度: {prediction['confidence']*100:.1f}%) - {prediction['reason'][:100]}"
            }
        except Exception as e:
            return {"type": "hold", "reason": f"预测失败: {str(e)}"}
    
    def get_available_strategies(self) -> List[Dict]:
        return [
            {
                "name": "ma_cross",
                "description": "均线交叉策略",
                "params": {
                    "name": "ma_cross",
                    "short_period": 5,
                    "long_period": 20
                }
            },
            {
                "name": "rsi",
                "description": "RSI超买超卖策略",
                "params": {
                    "name": "rsi",
                    "period": 14,
                    "oversold": 30,
                    "overbought": 70
                }
            },
            {
                "name": "macd",
                "description": "MACD动量策略",
                "params": {
                    "name": "macd",
                    "fast": 12,
                    "slow": 26,
                    "signal": 9
                }
            },
            {
                "name": "bollinger",
                "description": "布林带策略",
                "params": {
                    "name": "bollinger",
                    "period": 20,
                    "std_dev": 2
                }
            },
            {
                "name": "kdj",
                "description": "KDJ指标策略",
                "params": {
                    "name": "kdj",
                    "n": 9,
                    "m1": 3,
                    "m2": 3
                }
            },
            {
                "name": "time_series",
                "description": "时序预测策略",
                "params": {
                    "name": "time_series",
                    "lookback": 20,
                    "threshold": 0.02
                }
            },
            {
                "name": "prediction_ensemble",
                "description": "综合预测策略(多策略投票)",
                "params": {
                    "name": "prediction_ensemble"
                }
            }
        ]
