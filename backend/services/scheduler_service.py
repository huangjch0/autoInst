import schedule
import time
import threading
from datetime import datetime, timedelta
from typing import Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SchedulerService:
    _instance = None
    _running = False
    _thread = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, 'initialized'):
            self.initialized = True
            self.jobs = []
            self.last_run_times = {}
    
    def update_all_assets_data(self):
        from backend.database import SessionLocal
        from backend.database import Asset, MarketData
        from backend.services.market_service import MarketService
        
        logger.info(f"[{datetime.now()}] 开始自动更新所有资产数据...")
        
        db = SessionLocal()
        try:
            assets = db.query(Asset).all()
            
            if not assets:
                logger.info("没有资产需要更新")
                return
            
            service = MarketService()
            success_count = 0
            fail_count = 0
            
            for asset in assets:
                try:
                    data = service.fetch_history_data(asset.symbol)
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
                        success_count += 1
                        logger.info(f"成功更新 {asset.symbol} ({asset.name}): {saved_count} 条数据")
                    else:
                        fail_count += 1
                        logger.warning(f"无法获取 {asset.symbol} 的数据")
                except Exception as e:
                    fail_count += 1
                    logger.error(f"更新 {asset.symbol} 失败: {str(e)}")
            
            self.last_run_times['update_all'] = datetime.now()
            logger.info(f"自动更新完成: 成功 {success_count}, 失败 {fail_count}")
            
        except Exception as e:
            logger.error(f"自动更新任务出错: {str(e)}")
        finally:
            db.close()
    
    def run_auto_strategies(self):
        from backend.database import SessionLocal
        from backend.database import Strategy, Signal
        from backend.services.strategy_service import StrategyService
        
        logger.info(f"[{datetime.now()}] 开始自动执行策略...")
        
        db = SessionLocal()
        try:
            strategies = db.query(Strategy).filter(
                Strategy.is_active == 1,
                Strategy.auto_run == 1
            ).all()
            
            if not strategies:
                logger.info("没有需要自动执行的策略")
                return
            
            strategy_service = StrategyService()
            total_signals = 0
            approval_signals = 0
            
            for strategy in strategies:
                if strategy.last_run_at:
                    next_run = strategy.last_run_at + timedelta(minutes=strategy.run_interval_minutes or 60)
                    if datetime.now() < next_run:
                        logger.info(f"策略 [{strategy.name}] 未到执行时间，跳过")
                        continue
                
                try:
                    logger.info(f"执行策略 [{strategy.name}]...")
                    signals = strategy_service.run_strategy(strategy, db)
                    
                    strategy.last_run_at = datetime.now()
                    db.commit()
                    
                    total_signals += len(signals)
                    approval_signals += len([s for s in signals if s.get("signal_type") in ["buy", "sell"] and s.get("id")])
                    
                    logger.info(f"策略 [{strategy.name}] 执行完成，生成 {len(signals)} 个信号")
                    
                except Exception as e:
                    logger.error(f"策略 [{strategy.name}] 执行失败: {str(e)}")
            
            self.last_run_times['auto_strategies'] = datetime.now()
            logger.info(f"自动策略执行完成: 共 {len(strategies)} 个策略，{total_signals} 个信号，{approval_signals} 个待审批")
            
        except Exception as e:
            logger.error(f"自动策略执行出错: {str(e)}")
        finally:
            db.close()
    
    def setup_auto_strategy_run(self, interval_minutes: int = 30):
        schedule.every(interval_minutes).minutes.do(self.run_auto_strategies)
        logger.info(f"已设置每 {interval_minutes} 分钟自动执行策略")
    
    def setup_daily_update(self, update_time: str = "15:30"):
        schedule.every().day.at(update_time).do(self.update_all_assets_data)
        logger.info(f"已设置每日 {update_time} 自动更新数据")
    
    def setup_interval_update(self, interval_minutes: int = 60):
        schedule.every(interval_minutes).minutes.do(self.update_all_assets_data)
        logger.info(f"已设置每 {interval_minutes} 分钟自动更新数据")
    
    def run_pending(self):
        while self._running:
            schedule.run_pending()
            time.sleep(1)
    
    def start(self):
        if self._running:
            logger.warning("调度器已在运行中")
            return
        
        self._running = True
        self._thread = threading.Thread(target=self.run_pending, daemon=True)
        self._thread.start()
        logger.info("调度器已启动")
    
    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("调度器已停止")
    
    def get_status(self) -> dict:
        return {
            "running": self._running,
            "jobs": [
                {
                    "job": str(job),
                    "next_run": str(job.next_run) if job.next_run else None
                } for job in schedule.get_jobs()
            ],
            "last_run_times": {
                k: v.isoformat() if v else None 
                for k, v in self.last_run_times.items()
            }
        }
    
    def clear_jobs(self):
        schedule.clear()
        logger.info("已清除所有定时任务")

scheduler = SchedulerService()
