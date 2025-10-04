from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from src.db.session import get_db
from src.db import models
from src.schemas import schemas

router = APIRouter(prefix="/stocks", tags=["stocks"])


# GET: List all stocks for a specific supplier (accessible by everyone)
@router.get("/supplier/{supplier_id}", response_model=list[schemas.SupplierStockRead])
def get_stocks_by_supplier(supplier_id: int, db: Session = Depends(get_db)):
    stocks = db.query(models.SupplierStock).filter(models.SupplierStock.supplier_id == supplier_id).all()
    return stocks

@router.get("/crop/{crop_type}", response_model=list[schemas.SupplierStockRead])
def get_stocks_by_crop(crop_type: models.CropType, db: Session = Depends(get_db)):
    stocks = (
        db.query(models.SupplierStock)
        .join(models.Supplier)
        .filter(models.SupplierStock.crop_type == crop_type)
        .all()
    )

    if not stocks:
        raise HTTPException(status_code=404, detail=f"No stocks found for crop type '{crop_type.value}'")

    # Convert to schema including supplier name
    result = [
        schemas.SupplierStockRead(
            id=s.id,
            supplier_id=s.supplier_id,
            supplier_name=s.supplier.name,
            crop_type=s.crop_type.value,
            remaining_volume=s.remaining_volume,
            price=s.price,
            expiry_date=s.expiry_date.isoformat() if s.expiry_date else None,
            risk_score=s.risk_score,
            message=s.message,
            created_at=s.created_at.isoformat()
        )
        for s in stocks
    ]

    return result