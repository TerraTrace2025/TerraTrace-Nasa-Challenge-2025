from fastapi import APIRouter, Depends
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
