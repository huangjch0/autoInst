from sqlalchemy import Column, Integer, String, Float, DateTime, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()

class Account(Base):
    __tablename__ = "accounts"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    initial_capital = Column(Float, default=0)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    transactions = relationship("Transaction", back_populates="account")
    portfolio_snapshots = relationship("PortfolioSnapshot", back_populates="account")

class Asset(Base):
    __tablename__ = "assets"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(50), unique=True, nullable=False)
    name = Column(String(100), nullable=False)
    type = Column(String(20), nullable=False, default="stock")
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    transactions = relationship("Transaction", back_populates="asset")
    signals = relationship("Signal", back_populates="asset")

class Transaction(Base):
    __tablename__ = "transactions"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=True)
    asset_id = Column(Integer, ForeignKey("assets.id"), nullable=False)
    type = Column(String(10), nullable=False)
    date = Column(DateTime, nullable=False)
    quantity = Column(Float, nullable=False)
    price = Column(Float, nullable=False)
    fee = Column(Float, default=0)
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.now)
    
    account = relationship("Account", back_populates="transactions")
    asset = relationship("Asset", back_populates="transactions")

class MarketData(Base):
    __tablename__ = "market_data"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(50), nullable=False, index=True)
    date = Column(DateTime, nullable=False, index=True)
    open = Column(Float)
    high = Column(Float)
    low = Column(Float)
    close = Column(Float)
    volume = Column(Float)
    created_at = Column(DateTime, default=datetime.now)

class Strategy(Base):
    __tablename__ = "strategies"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=True)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    params_json = Column(Text)
    is_active = Column(Integer, default=1)
    auto_run = Column(Integer, default=1)
    run_interval_minutes = Column(Integer, default=60)
    last_run_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    signals = relationship("Signal", back_populates="strategy")
    account = relationship("Account", backref="strategies")

class Signal(Base):
    __tablename__ = "signals"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    strategy_id = Column(Integer, ForeignKey("strategies.id"))
    asset_id = Column(Integer, ForeignKey("assets.id"))
    signal_type = Column(String(10), nullable=False)
    price = Column(Float)
    suggested_quantity = Column(Integer, default=100)
    reason = Column(Text)
    status = Column(String(20), default="pending")
    user_response = Column(Text)
    response_time = Column(DateTime)
    created_at = Column(DateTime, default=datetime.now)
    
    strategy = relationship("Strategy", back_populates="signals")
    asset = relationship("Asset", back_populates="signals")

class Portfolio(Base):
    __tablename__ = "portfolios"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(DateTime, nullable=False)
    total_value = Column(Float, nullable=False)
    cash = Column(Float, default=0)
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.now)

class PortfolioSnapshot(Base):
    __tablename__ = "portfolio_snapshots"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=True)
    date = Column(DateTime, nullable=False)
    total_value = Column(Float, nullable=False)
    cash = Column(Float, default=0)
    position_value = Column(Float, default=0)
    daily_return = Column(Float, default=0)
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.now)
    
    account = relationship("Account", back_populates="portfolio_snapshots")
