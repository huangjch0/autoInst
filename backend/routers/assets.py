from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel
from backend.database import get_db, Asset

router = APIRouter(prefix="/api/assets", tags=["assets"])

class AssetCreate(BaseModel):
    symbol: str
    name: str
    type: str = "stock"

class AssetResponse(BaseModel):
    id: int
    symbol: str
    name: str
    type: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class AssetUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[str] = None

@router.get("/", response_model=List[AssetResponse])
def get_assets(db: Session = Depends(get_db)):
    return db.query(Asset).all()

@router.get("/{asset_id}", response_model=AssetResponse)
def get_asset(asset_id: int, db: Session = Depends(get_db)):
    asset = db.query(Asset).filter(Asset.id == asset_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="资产未找到")
    return asset

@router.post("/", response_model=AssetResponse)
def create_asset(asset: AssetCreate, db: Session = Depends(get_db)):
    existing = db.query(Asset).filter(Asset.symbol == asset.symbol).first()
    if existing:
        raise HTTPException(status_code=400, detail="该资产代码已存在")
    db_asset = Asset(symbol=asset.symbol, name=asset.name, type=asset.type)
    db.add(db_asset)
    db.commit()
    db.refresh(db_asset)
    return db_asset

@router.put("/{asset_id}", response_model=AssetResponse)
def update_asset(asset_id: int, asset: AssetUpdate, db: Session = Depends(get_db)):
    db_asset = db.query(Asset).filter(Asset.id == asset_id).first()
    if not db_asset:
        raise HTTPException(status_code=404, detail="资产未找到")
    if asset.name:
        db_asset.name = asset.name
    if asset.type:
        db_asset.type = asset.type
    db.commit()
    db.refresh(db_asset)
    return db_asset

@router.delete("/{asset_id}")
def delete_asset(asset_id: int, db: Session = Depends(get_db)):
    db_asset = db.query(Asset).filter(Asset.id == asset_id).first()
    if not db_asset:
        raise HTTPException(status_code=404, detail="资产未找到")
    db.delete(db_asset)
    db.commit()
    return {"message": "资产已删除"}
