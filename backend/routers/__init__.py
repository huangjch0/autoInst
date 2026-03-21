from .assets import router as assets_router
from .transactions import router as transactions_router
from .market import router as market_router
from .strategies import router as strategies_router
from .portfolio import router as portfolio_router
from .accounts import router as accounts_router
from .backtest import router as backtest_router

__all__ = [
    'assets_router',
    'transactions_router', 
    'market_router',
    'strategies_router',
    'portfolio_router',
    'accounts_router',
    'backtest_router'
]
