from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.database import init_database
from backend.routers import (
    assets_router,
    transactions_router,
    market_router,
    strategies_router,
    portfolio_router,
    accounts_router,
    backtest_router
)

scheduler_instance = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global scheduler_instance
    init_database()
    
    from backend.services.scheduler_service import scheduler
    scheduler.setup_daily_update("15:30")
    scheduler.setup_auto_strategy_run(30)
    scheduler.start()
    scheduler_instance = scheduler
    
    yield
    
    scheduler.stop()

app = FastAPI(
    title="自动化投资系统 API",
    description="个人投资组合管理、交易记录、策略回测系统",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(assets_router)
app.include_router(transactions_router)
app.include_router(market_router)
app.include_router(strategies_router)
app.include_router(portfolio_router)
app.include_router(accounts_router)
app.include_router(backtest_router)

@app.get("/")
def root():
    return {"message": "自动化投资系统 API", "version": "1.0.0"}

@app.get("/api/health")
def health_check():
    return {"status": "healthy"}

@app.get("/api/scheduler/status")
def get_scheduler_status():
    from backend.services.scheduler_service import scheduler
    return scheduler.get_status()

@app.post("/api/scheduler/start")
def start_scheduler():
    from backend.services.scheduler_service import scheduler
    scheduler.start()
    return {"message": "调度器已启动", "status": scheduler.get_status()}

@app.post("/api/scheduler/stop")
def stop_scheduler():
    from backend.services.scheduler_service import scheduler
    scheduler.stop()
    return {"message": "调度器已停止", "status": scheduler.get_status()}

@app.post("/api/scheduler/run-now")
def run_update_now():
    from backend.services.scheduler_service import scheduler
    import threading
    thread = threading.Thread(target=scheduler.update_all_assets_data)
    thread.start()
    return {"message": "已触发立即更新任务"}

@app.post("/api/scheduler/config")
def config_scheduler(
    daily_time: str = "15:30",
    interval_minutes: int = 0
):
    from backend.services.scheduler_service import scheduler
    scheduler.clear_jobs()
    
    if daily_time:
        scheduler.setup_daily_update(daily_time)
    
    if interval_minutes > 0:
        scheduler.setup_interval_update(interval_minutes)
    
    return {
        "message": "调度器配置已更新",
        "daily_time": daily_time,
        "interval_minutes": interval_minutes,
        "status": scheduler.get_status()
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
