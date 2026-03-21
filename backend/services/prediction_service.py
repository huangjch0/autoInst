import numpy as np
import pandas as pd
from typing import Dict, Optional, List
from datetime import datetime
import warnings

warnings.filterwarnings('ignore')

class PredictionService:
    def __init__(self):
        self.strategies = {
            "ma_trend": self._ma_trend_prediction,
            "rsi_reversal": self._rsi_reversal_prediction,
            "macd_momentum": self._macd_momentum_prediction,
            "bollinger_band": self._bollinger_prediction,
            "kdj_signal": self._kdj_prediction,
            "linear_regression": self._linear_regression_prediction,
            "time_series": self._time_series_prediction,
            "ensemble": self._ensemble_prediction
        }
    
    def predict(self, df: pd.DataFrame, strategy: str = "ensemble") -> Dict:
        if len(df) < 30:
            return {
                "direction": "hold",
                "confidence": 0.5,
                "predicted_price": df['close'].iloc[-1] if len(df) > 0 else 0,
                "reason": "数据不足，至少需要30条数据",
                "strategy": strategy
            }
        
        df = df.copy()
        df = df.sort_values('date').reset_index(drop=True)
        
        df = self._calculate_features(df)
        
        if strategy in self.strategies:
            return self.strategies[strategy](df)
        
        return self._ensemble_prediction(df)
    
    def _calculate_features(self, df: pd.DataFrame) -> pd.DataFrame:
        df['ma_5'] = df['close'].rolling(window=5).mean()
        df['ma_10'] = df['close'].rolling(window=10).mean()
        df['ma_20'] = df['close'].rolling(window=20).mean()
        df['ma_60'] = df['close'].rolling(window=60).mean()
        
        df['return_1d'] = df['close'].pct_change()
        df['return_5d'] = df['close'].pct_change(5)
        df['return_10d'] = df['close'].pct_change(10)
        
        df['volatility_5d'] = df['return_1d'].rolling(window=5).std()
        df['volatility_20d'] = df['return_1d'].rolling(window=20).std()
        
        df['momentum_5d'] = df['close'].pct_change(5)
        df['momentum_10d'] = df['close'].pct_change(10)
        
        df['price_position_ma20'] = (df['close'] - df['ma_20']) / df['ma_20'] * 100
        df['price_position_ma60'] = (df['close'] - df['ma_60']) / df['ma_60'] * 100
        
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
        
        df['bb_middle'] = df['close'].rolling(window=20).mean()
        bb_std = df['close'].rolling(window=20).std()
        df['bb_upper'] = df['bb_middle'] + 2 * bb_std
        df['bb_lower'] = df['bb_middle'] - 2 * bb_std
        df['bb_position'] = (df['close'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'])
        
        low_min = df['low'].rolling(window=9).min()
        high_max = df['high'].rolling(window=9).max()
        rsv = (df['close'] - low_min) / (high_max - low_min) * 100
        df['k'] = rsv.ewm(alpha=1/3, adjust=False).mean()
        df['d'] = df['k'].ewm(alpha=1/3, adjust=False).mean()
        df['j'] = 3 * df['k'] - 2 * df['d']
        
        df['volume_ma_5'] = df['volume'].rolling(window=5).mean()
        df['volume_ratio'] = df['volume'] / df['volume_ma_5']
        
        return df
    
    def _ma_trend_prediction(self, df: pd.DataFrame) -> Dict:
        last = df.iloc[-1]
        prev = df.iloc[-2]
        
        ma_5, ma_10, ma_20, ma_60 = last['ma_5'], last['ma_10'], last['ma_20'], last['ma_60']
        prev_ma_5, prev_ma_10 = prev['ma_5'], prev['ma_10']
        close = last['close']
        
        if pd.isna(ma_5) or pd.isna(ma_10) or pd.isna(ma_20):
            return self._hold_prediction(df, "均线数据不足")
        
        signals = []
        confidence = 0.5
        
        if prev_ma_5 <= prev_ma_10 and ma_5 > ma_10:
            signals.append("MA5上穿MA10金叉")
            confidence += 0.15
        elif prev_ma_5 >= prev_ma_10 and ma_5 < ma_10:
            signals.append("MA5下穿MA10死叉")
            confidence -= 0.15
        
        if ma_5 > ma_10 > ma_20:
            signals.append("均线多头排列")
            confidence += 0.1
        elif ma_5 < ma_10 < ma_20:
            signals.append("均线空头排列")
            confidence -= 0.1
        
        if close > ma_20:
            signals.append("价格站上MA20")
            confidence += 0.05
        else:
            signals.append("价格跌破MA20")
            confidence -= 0.05
        
        direction = "up" if confidence > 0.55 else "down" if confidence < 0.45 else "hold"
        confidence = max(0.3, min(0.8, confidence))
        
        predicted_price = close * (1 + (confidence - 0.5) * 0.05)
        
        return {
            "direction": direction,
            "confidence": round(confidence, 3),
            "predicted_price": round(predicted_price, 2),
            "reason": " | ".join(signals),
            "strategy": "ma_trend",
            "indicators": {
                "MA5": round(ma_5, 2),
                "MA10": round(ma_10, 2),
                "MA20": round(ma_20, 2),
                "MA60": round(ma_60, 2) if not pd.isna(ma_60) else None
            }
        }
    
    def _rsi_reversal_prediction(self, df: pd.DataFrame) -> Dict:
        last = df.iloc[-1]
        prev = df.iloc[-2]
        
        rsi = last['rsi']
        prev_rsi = prev['rsi']
        close = last['close']
        
        if pd.isna(rsi):
            return self._hold_prediction(df, "RSI数据不足")
        
        signals = []
        confidence = 0.5
        
        if rsi < 30:
            signals.append(f"RSI={rsi:.1f}超卖区域")
            confidence += 0.2
            if rsi > prev_rsi:
                signals.append("RSI开始回升")
                confidence += 0.1
        elif rsi > 70:
            signals.append(f"RSI={rsi:.1f}超买区域")
            confidence -= 0.2
            if rsi < prev_rsi:
                signals.append("RSI开始回落")
                confidence -= 0.1
        else:
            signals.append(f"RSI={rsi:.1f}正常区域")
            if rsi > 50:
                confidence += 0.05
            else:
                confidence -= 0.05
        
        direction = "up" if confidence > 0.55 else "down" if confidence < 0.45 else "hold"
        confidence = max(0.3, min(0.8, confidence))
        
        predicted_price = close * (1 + (confidence - 0.5) * 0.04)
        
        return {
            "direction": direction,
            "confidence": round(confidence, 3),
            "predicted_price": round(predicted_price, 2),
            "reason": " | ".join(signals),
            "strategy": "rsi_reversal",
            "indicators": {
                "RSI": round(rsi, 2)
            }
        }
    
    def _macd_momentum_prediction(self, df: pd.DataFrame) -> Dict:
        last = df.iloc[-1]
        prev = df.iloc[-2]
        
        macd = last['macd']
        macd_signal = last['macd_signal']
        macd_hist = last['macd_hist']
        prev_hist = prev['macd_hist']
        close = last['close']
        
        if pd.isna(macd) or pd.isna(macd_signal):
            return self._hold_prediction(df, "MACD数据不足")
        
        signals = []
        confidence = 0.5
        
        if prev_hist <= 0 and macd_hist > 0:
            signals.append("MACD柱状图由负转正(金叉)")
            confidence += 0.2
        elif prev_hist >= 0 and macd_hist < 0:
            signals.append("MACD柱状图由正转负(死叉)")
            confidence -= 0.2
        
        if macd > macd_signal:
            signals.append("MACD在信号线上方")
            confidence += 0.05
        else:
            signals.append("MACD在信号线下方")
            confidence -= 0.05
        
        if macd_hist > prev_hist and macd_hist > 0:
            signals.append("多头动能增强")
            confidence += 0.1
        elif macd_hist < prev_hist and macd_hist < 0:
            signals.append("空头动能增强")
            confidence -= 0.1
        
        direction = "up" if confidence > 0.55 else "down" if confidence < 0.45 else "hold"
        confidence = max(0.3, min(0.8, confidence))
        
        predicted_price = close * (1 + (confidence - 0.5) * 0.04)
        
        return {
            "direction": direction,
            "confidence": round(confidence, 3),
            "predicted_price": round(predicted_price, 2),
            "reason": " | ".join(signals),
            "strategy": "macd_momentum",
            "indicators": {
                "MACD": round(macd, 4),
                "Signal": round(macd_signal, 4),
                "Histogram": round(macd_hist, 4)
            }
        }
    
    def _bollinger_prediction(self, df: pd.DataFrame) -> Dict:
        last = df.iloc[-1]
        
        close = last['close']
        bb_upper = last['bb_upper']
        bb_lower = last['bb_lower']
        bb_middle = last['bb_middle']
        bb_position = last['bb_position']
        
        if pd.isna(bb_upper) or pd.isna(bb_lower):
            return self._hold_prediction(df, "布林带数据不足")
        
        signals = []
        confidence = 0.5
        
        if close <= bb_lower:
            signals.append("价格触及布林带下轨")
            confidence += 0.2
        elif close >= bb_upper:
            signals.append("价格触及布林带上轨")
            confidence -= 0.2
        elif bb_position < 0.2:
            signals.append(f"价格接近下轨(位置={bb_position:.2f})")
            confidence += 0.1
        elif bb_position > 0.8:
            signals.append(f"价格接近上轨(位置={bb_position:.2f})")
            confidence -= 0.1
        else:
            signals.append(f"价格在布林带中轨附近(位置={bb_position:.2f})")
        
        bb_width = (bb_upper - bb_lower) / bb_middle
        if bb_width < 0.1:
            signals.append("布林带收窄，可能突破")
        
        direction = "up" if confidence > 0.55 else "down" if confidence < 0.45 else "hold"
        confidence = max(0.3, min(0.8, confidence))
        
        predicted_price = close * (1 + (confidence - 0.5) * 0.03)
        
        return {
            "direction": direction,
            "confidence": round(confidence, 3),
            "predicted_price": round(predicted_price, 2),
            "reason": " | ".join(signals),
            "strategy": "bollinger_band",
            "indicators": {
                "Upper": round(bb_upper, 2),
                "Middle": round(bb_middle, 2),
                "Lower": round(bb_lower, 2),
                "Position": round(bb_position, 3)
            }
        }
    
    def _kdj_prediction(self, df: pd.DataFrame) -> Dict:
        last = df.iloc[-1]
        prev = df.iloc[-2]
        
        k = last['k']
        d = last['d']
        j = last['j']
        prev_k = prev['k']
        prev_d = prev['d']
        close = last['close']
        
        if pd.isna(k) or pd.isna(d):
            return self._hold_prediction(df, "KDJ数据不足")
        
        signals = []
        confidence = 0.5
        
        if prev_k <= prev_d and k > d:
            signals.append(f"KDJ金叉(K={k:.1f}, D={d:.1f})")
            if k < 20:
                signals.append("低位金叉，买入信号强")
                confidence += 0.25
            else:
                confidence += 0.15
        elif prev_k >= prev_d and k < d:
            signals.append(f"KDJ死叉(K={k:.1f}, D={d:.1f})")
            if k > 80:
                signals.append("高位死叉，卖出信号强")
                confidence -= 0.25
            else:
                confidence -= 0.15
        
        if j < 0:
            signals.append(f"J值={j:.1f}超卖")
            confidence += 0.1
        elif j > 100:
            signals.append(f"J值={j:.1f}超买")
            confidence -= 0.1
        
        direction = "up" if confidence > 0.55 else "down" if confidence < 0.45 else "hold"
        confidence = max(0.3, min(0.8, confidence))
        
        predicted_price = close * (1 + (confidence - 0.5) * 0.04)
        
        return {
            "direction": direction,
            "confidence": round(confidence, 3),
            "predicted_price": round(predicted_price, 2),
            "reason": " | ".join(signals),
            "strategy": "kdj_signal",
            "indicators": {
                "K": round(k, 2),
                "D": round(d, 2),
                "J": round(j, 2)
            }
        }
    
    def _linear_regression_prediction(self, df: pd.DataFrame) -> Dict:
        try:
            from sklearn.linear_model import LinearRegression
            
            df_clean = df.dropna(subset=['ma_5', 'ma_10', 'ma_20', 'return_1d', 'volatility_5d'])
            
            if len(df_clean) < 20:
                return self._hold_prediction(df, "数据不足进行回归分析")
            
            feature_cols = ['ma_5', 'ma_10', 'ma_20', 'return_1d', 'return_5d', 
                           'volatility_5d', 'momentum_5d', 'rsi', 'macd_hist']
            
            X = df_clean[feature_cols].iloc[:-1].values
            y = df_clean['close'].iloc[1:].values
            
            valid_idx = ~(np.isnan(X).any(axis=1) | np.isnan(y))
            X = X[valid_idx]
            y = y[valid_idx]
            
            if len(X) < 15:
                return self._hold_prediction(df, "有效数据不足")
            
            model = LinearRegression()
            model.fit(X, y)
            
            last_features = df_clean[feature_cols].iloc[-1].values
            if np.isnan(last_features).any():
                return self._hold_prediction(df, "最新特征数据缺失")
            
            predicted_price = model.predict([last_features])[0]
            close = df['close'].iloc[-1]
            
            change_pct = (predicted_price - close) / close
            
            direction = "up" if change_pct > 0.01 else "down" if change_pct < -0.01 else "hold"
            
            confidence = min(0.75, 0.5 + abs(change_pct) * 10)
            
            return {
                "direction": direction,
                "confidence": round(confidence, 3),
                "predicted_price": round(predicted_price, 2),
                "reason": f"线性回归预测价格: ¥{predicted_price:.2f}, 预期变化: {change_pct*100:.2f}%",
                "strategy": "linear_regression",
                "indicators": {
                    "PredictedChange": round(change_pct * 100, 2)
                }
            }
        except Exception as e:
            return self._hold_prediction(df, f"回归分析失败: {str(e)}")
    
    def _time_series_prediction(self, df: pd.DataFrame) -> Dict:
        try:
            close_series = df['close'].values
            dates = df['date'].values
            
            if len(close_series) < 30:
                return self._hold_prediction(df, "时序预测需要至少30条数据")
            
            prices = close_series[-60:] if len(close_series) >= 60 else close_series
            
            log_prices = np.log(prices)
            
            returns = np.diff(log_prices)
            
            weights = np.exp(np.linspace(0, 1, len(returns)))
            weights = weights / weights.sum()
            weighted_mean = np.sum(returns * weights)
            weighted_std = np.sqrt(np.sum(weights * (returns - weighted_mean) ** 2))
            
            trend = np.polyfit(np.arange(len(prices)), prices, 1)[0]
            trend_pct = trend / prices[-1]
            
            seasonality = self._detect_seasonality(prices)
            
            last_price = prices[-1]
            
            predicted_return = weighted_mean * 5 + trend_pct * 5
            predicted_price = last_price * np.exp(predicted_return)
            
            confidence = 0.5
            signals = []
            
            if trend_pct > 0:
                signals.append(f"上升趋势(斜率={trend_pct*100:.3f}%/天)")
                confidence += min(0.15, trend_pct * 100)
            elif trend_pct < 0:
                signals.append(f"下降趋势(斜率={trend_pct*100:.3f}%/天)")
                confidence -= min(0.15, abs(trend_pct) * 100)
            
            if seasonality['has_seasonality']:
                signals.append(f"检测到周期性(周期≈{seasonality['period']}天)")
                if seasonality['next_direction'] == 'up':
                    confidence += 0.1
                else:
                    confidence -= 0.1
            
            volatility = weighted_std * np.sqrt(5)
            if volatility > 0.05:
                signals.append(f"高波动率({volatility*100:.1f}%)")
                confidence = max(0.4, confidence - 0.1)
            
            direction = "up" if predicted_price > last_price * 1.01 else "down" if predicted_price < last_price * 0.99 else "hold"
            confidence = max(0.3, min(0.75, confidence))
            
            return {
                "direction": direction,
                "confidence": round(confidence, 3),
                "predicted_price": round(predicted_price, 2),
                "reason": " | ".join(signals) if signals else "时序模型预测",
                "strategy": "time_series",
                "indicators": {
                    "Trend": round(trend_pct * 100, 4),
                    "Volatility": round(volatility * 100, 2),
                    "Seasonality": seasonality['period'] if seasonality['has_seasonality'] else None
                }
            }
        except Exception as e:
            return self._hold_prediction(df, f"时序预测失败: {str(e)}")
    
    def _detect_seasonality(self, prices: np.ndarray) -> Dict:
        try:
            n = len(prices)
            if n < 20:
                return {'has_seasonality': False, 'period': None, 'next_direction': None}
            
            fft = np.fft.fft(prices - np.mean(prices))
            freqs = np.fft.fftfreq(n)
            
            power = np.abs(fft) ** 2
            
            positive_freqs = freqs[:n//2]
            positive_power = power[:n//2]
            
            peak_idx = np.argmax(positive_power[1:]) + 1
            peak_freq = positive_freqs[peak_idx]
            
            if peak_freq > 0:
                period = int(1 / peak_freq)
                if 5 <= period <= 30:
                    next_direction = 'up' if fft[peak_idx].real > 0 else 'down'
                    return {'has_seasonality': True, 'period': period, 'next_direction': next_direction}
            
            return {'has_seasonality': False, 'period': None, 'next_direction': None}
        except:
            return {'has_seasonality': False, 'period': None, 'next_direction': None}
    
    def _ensemble_prediction(self, df: pd.DataFrame) -> Dict:
        predictions = []
        
        strategies_to_use = ['ma_trend', 'rsi_reversal', 'macd_momentum', 'bollinger_band', 'kdj_signal', 'time_series']
        
        for strategy in strategies_to_use:
            try:
                pred = self.strategies[strategy](df)
                predictions.append(pred)
            except:
                pass
        
        if not predictions:
            return self._hold_prediction(df, "所有预测策略失败")
        
        up_votes = sum(1 for p in predictions if p['direction'] == 'up')
        down_votes = sum(1 for p in predictions if p['direction'] == 'down')
        total_votes = len(predictions)
        
        avg_confidence = np.mean([p['confidence'] for p in predictions])
        avg_predicted_price = np.mean([p['predicted_price'] for p in predictions])
        
        if up_votes > down_votes:
            direction = "up"
            confidence = avg_confidence * (up_votes / total_votes)
        elif down_votes > up_votes:
            direction = "down"
            confidence = avg_confidence * (down_votes / total_votes)
        else:
            direction = "hold"
            confidence = avg_confidence * 0.5
        
        confidence = max(0.3, min(0.85, confidence))
        
        reasons = []
        for p in predictions:
            if p['direction'] == direction:
                reasons.append(f"[{p['strategy']}] {p['reason'][:50]}")
        
        return {
            "direction": direction,
            "confidence": round(confidence, 3),
            "predicted_price": round(avg_predicted_price, 2),
            "reason": " | ".join(reasons[:3]) if reasons else "综合预测",
            "strategy": "ensemble",
            "vote_summary": {
                "up": up_votes,
                "down": down_votes,
                "hold": total_votes - up_votes - down_votes
            },
            "individual_predictions": [
                {
                    "strategy": p['strategy'],
                    "direction": p['direction'],
                    "confidence": p['confidence']
                } for p in predictions
            ]
        }
    
    def _hold_prediction(self, df: pd.DataFrame, reason: str) -> Dict:
        close = df['close'].iloc[-1] if len(df) > 0 else 0
        return {
            "direction": "hold",
            "confidence": 0.5,
            "predicted_price": round(close, 2),
            "reason": reason,
            "strategy": "hold"
        }
    
    def get_available_strategies(self) -> List[Dict]:
        return [
            {"name": "ma_trend", "description": "均线趋势策略 - 基于均线交叉和排列判断趋势"},
            {"name": "rsi_reversal", "description": "RSI反转策略 - 基于RSI超买超卖判断反转"},
            {"name": "macd_momentum", "description": "MACD动量策略 - 基于MACD金叉死叉判断动量"},
            {"name": "bollinger_band", "description": "布林带策略 - 基于价格在布林带位置判断"},
            {"name": "kdj_signal", "description": "KDJ信号策略 - 基于KDJ金叉死叉判断"},
            {"name": "linear_regression", "description": "线性回归策略 - 基于多特征线性回归预测"},
            {"name": "time_series", "description": "时序预测策略 - 基于趋势和周期性分析"},
            {"name": "ensemble", "description": "综合预测策略 - 综合多种策略投票决策"}
        ]
