import requests
import json
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, List, Dict
import time

class MarketService:
    def __init__(self):
        self.cache = {}
        self.cache_time = {}
        self.cache_duration = 300
        self._stock_list_cache = None
        self._stock_list_time = None
    
    def _get_stock_list(self):
        import akshare as ak
        now = time.time()
        if self._stock_list_cache is not None and self._stock_list_time and (now - self._stock_list_time < self.cache_duration):
            return self._stock_list_cache
        
        try:
            df = ak.stock_info_a_code_name()
            self._stock_list_cache = df
            self._stock_list_time = now
            return df
        except Exception as e:
            print(f"获取股票列表失败: {e}")
            return None
    
    def get_realtime_quote(self, symbol: str) -> Optional[Dict]:
        try:
            prefix = 'sh' if symbol.startswith('6') else 'sz'
            url = f"https://hq.sinajs.cn/list={prefix}{symbol}"
            headers = {"Referer": "https://finance.sina.com.cn"}
            r = requests.get(url, headers=headers, timeout=10)
            r.encoding = 'gbk'
            
            if r.text and '=' in r.text:
                data = r.text.split('"')[1].split(',')
                if len(data) > 30:
                    name = data[0]
                    price = float(data[3]) if data[3] else 0
                    prev_close = float(data[2]) if data[2] else 0
                    change = price - prev_close
                    change_percent = (change / prev_close * 100) if prev_close > 0 else 0
                    return {
                        "symbol": symbol,
                        "name": name,
                        "price": price,
                        "change": round(change, 2),
                        "change_percent": round(change_percent, 2),
                        "volume": float(data[8]) if data[8] else 0,
                        "timestamp": datetime.now()
                    }
            return None
        except Exception as e:
            print(f"获取实时行情失败: {e}")
            return None
    
    def fetch_history_data(self, symbol: str, start_date: Optional[str] = None, 
                          end_date: Optional[str] = None) -> List[Dict]:
        try:
            return self._fetch_history_data_tencent(symbol, start_date, end_date)
        except Exception as e:
            print(f"腾讯API获取失败: {e}, 尝试备用方法...")
            try:
                return self._fetch_history_data_akshare(symbol, start_date, end_date)
            except Exception as e2:
                print(f"akshare获取失败: {e2}, 尝试新浪API...")
                return self._fetch_history_data_sina(symbol, start_date, end_date)
    
    def _fetch_history_data_tencent(self, symbol: str, start_date: Optional[str] = None, 
                                     end_date: Optional[str] = None) -> List[Dict]:
        try:
            prefix = 'sh' if symbol.startswith('6') else 'sz'
            url = f"https://web.ifzq.gtimg.cn/appstock/app/fqkline/get"
            params = {
                "_var": "kline_dayqfq",
                "param": f"{prefix}{symbol},day,,,500,qfq",
                "r": "0.1"
            }
            
            r = requests.get(url, params=params, timeout=15)
            
            if not r.text or 'kline_dayqfq=' not in r.text:
                print(f"腾讯API返回格式异常")
                return []
            
            json_str = r.text.replace('kline_dayqfq=', '')
            data = json.loads(json_str)
            
            if data.get('code') != 0:
                print(f"腾讯API返回错误: {data.get('msg')}")
                return []
            
            stock_data = data.get('data', {}).get(f'{prefix}{symbol}', {})
            kline_data = stock_data.get('qfqday', []) or stock_data.get('day', [])
            
            if not kline_data:
                return []
            
            result = []
            for item in kline_data:
                try:
                    result.append({
                        "date": datetime.strptime(item[0], "%Y-%m-%d"),
                        "open": float(item[1]),
                        "close": float(item[2]),
                        "high": float(item[3]),
                        "low": float(item[4]),
                        "volume": float(item[5])
                    })
                except:
                    continue
            
            if start_date:
                start_dt = datetime.strptime(start_date.replace('-', ''), '%Y%m%d')
                result = [r for r in result if r['date'] >= start_dt]
            if end_date:
                end_dt = datetime.strptime(end_date.replace('-', ''), '%Y%m%d')
                result = [r for r in result if r['date'] <= end_dt]
            
            return result
        except Exception as e:
            print(f"腾讯API获取历史数据失败: {e}")
            raise e
    
    def _fetch_history_data_akshare(self, symbol: str, start_date: Optional[str] = None, 
                                     end_date: Optional[str] = None) -> List[Dict]:
        try:
            import akshare as ak
            
            end_dt = end_date if end_date else datetime.now().strftime('%Y%m%d')
            start_dt = start_date.replace('-', '') if start_date else (datetime.now() - timedelta(days=365*2)).strftime('%Y%m%d')
            
            df = ak.stock_zh_a_hist(symbol=symbol, period="daily", start_date=start_dt, end_date=end_dt, adjust="")
            
            if df is None or df.empty:
                return []
            
            result = []
            for _, row in df.iterrows():
                try:
                    date_val = row['日期']
                    if isinstance(date_val, str):
                        date = datetime.strptime(date_val, "%Y-%m-%d")
                    else:
                        date = datetime.strptime(str(date_val)[:10], "%Y-%m-%d")
                    
                    result.append({
                        "date": date,
                        "open": float(row['开盘']) if pd.notna(row['开盘']) else 0,
                        "high": float(row['最高']) if pd.notna(row['最高']) else 0,
                        "low": float(row['最低']) if pd.notna(row['最低']) else 0,
                        "close": float(row['收盘']) if pd.notna(row['收盘']) else 0,
                        "volume": float(row['成交量']) if pd.notna(row['成交量']) else 0
                    })
                except Exception as e:
                    continue
            
            return result
        except Exception as e:
            print(f"akshare获取历史数据失败: {e}")
            raise e
    
    def _fetch_history_data_sina(self, symbol: str, start_date: Optional[str] = None, 
                                  end_date: Optional[str] = None) -> List[Dict]:
        try:
            prefix = 'sh' if symbol.startswith('6') else 'sz'
            url = f"https://quotes.sina.cn/cn/api/json_v2.php/CN_MarketDataService.getKLineData"
            params = {
                "symbol": f"{prefix}{symbol}",
                "scale": "240",
                "ma": "no",
                "datalen": "500"
            }
            headers = {
                "Referer": "https://finance.sina.com.cn",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
            
            r = requests.get(url, params=params, headers=headers, timeout=15)
            
            if not r.text or r.text.strip() == '':
                print(f"新浪API返回空响应")
                return []
            
            try:
                data = json.loads(r.text)
            except json.JSONDecodeError as e:
                print(f"新浪API JSON解析错误: {e}")
                return []
            
            if not data:
                return []
            
            result = []
            for item in data:
                try:
                    date_str = item.get('day', '')
                    result.append({
                        "date": datetime.strptime(date_str, "%Y-%m-%d"),
                        "open": float(item.get('open', 0)),
                        "high": float(item.get('high', 0)),
                        "low": float(item.get('low', 0)),
                        "close": float(item.get('close', 0)),
                        "volume": float(item.get('volume', 0))
                    })
                except:
                    continue
            
            if start_date:
                start_dt = datetime.strptime(start_date.replace('-', ''), '%Y%m%d')
                result = [r for r in result if r['date'] >= start_dt]
            if end_date:
                end_dt = datetime.strptime(end_date.replace('-', ''), '%Y%m%d')
                result = [r for r in result if r['date'] <= end_dt]
            
            return result
        except Exception as e:
            print(f"新浪备用方法失败: {e}")
            return []
    
    def search_stock(self, keyword: str) -> List[Dict]:
        try:
            stock_list = self._get_stock_list()
            if stock_list is None:
                return []
            
            result = []
            keyword_lower = keyword.lower()
            for _, row in stock_list.iterrows():
                code = str(row['code'])
                name = str(row['name'])
                if keyword_lower in code.lower() or keyword_lower in name:
                    result.append({
                        "symbol": code,
                        "name": name,
                        "price": 0,
                        "change_percent": 0
                    })
                    if len(result) >= 20:
                        break
            return result
        except Exception as e:
            print(f"搜索股票失败: {e}")
            return []
    
    def get_index_data(self) -> Dict:
        return {}
