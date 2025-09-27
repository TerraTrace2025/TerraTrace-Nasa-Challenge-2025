from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from src.db.session import get_db
from src.db import models
from src.schemas import schemas

router = APIRouter(prefix="/suppliers", tags=["suppliers"])

@router.post("/", response_model=schemas.SupplierRead)
def create_supplier(supplier: schemas.SupplierCreate, db: Session = Depends(get_db)):
    db_supplier = models.Supplier(**supplier.dict())
    db.add(db_supplier)
    db.commit()
    db.refresh(db_supplier)
    return db_supplier

@router.get("/", response_model=list[schemas.SupplierRead])
def list_suppliers(db: Session = Depends(get_db)):
    return db.query(models.Supplier).all()

@router.delete("/{supplier_id}")
def delete_supplier(supplier_id: int, db: Session = Depends(get_db)):
    db_supplier = db.query(models.Supplier).get(supplier_id)
    if not db_supplier:
        return {"error": "Supplier not found"}
    db.delete(db_supplier)
    db.commit()
    return {"message": "Supplier deleted"}
