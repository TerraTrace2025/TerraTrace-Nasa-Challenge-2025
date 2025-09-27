from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from src.db.session import get_db
from src.db import models
from src.schemas import schemas

router = APIRouter(prefix="/stocks", tags=["stocks"])

@router.post("/", response_model=schemas.SupplierStockRead)
def create_stock(stock: schemas.SupplierStockCreate, db: Session = Depends(get_db)):
    db_stock = models.SupplierStock(**stock.dict())
    db.add(db_stock)
    db.commit()
    db.refresh(db_stock)
    return db_stock

@router.get("/", response_model=list[schemas.SupplierStockRead])
def list_stocks(db: Session = Depends(get_db)):
    return db.query(models.SupplierStock).all()

@router.delete("/{stock_id}")
def delete_stock(stock_id: int, db: Session = Depends(get_db)):
    db_stock = db.query(models.SupplierStock).get(stock_id)
    if not db_stock:
        return {"error": "Stock not found"}
    db.delete(db_stock)
    db.commit()
    return {"message": "Stock deleted"}

@router.get("/supplier/{supplier_id}", response_model=list[schemas.SupplierStockRead])
def get_stocks_by_supplier(supplier_id: int, db: Session = Depends(get_db)):
    stocks = db.query(models.SupplierStock).filter(models.SupplierStock.supplier_id == supplier_id).all()
    return stocks
