from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from src.db.session import get_db
from src.db import models
from src.schemas import schemas

router = APIRouter(prefix="/suppliers", tags=["suppliers"])

# GET: List all suppliers (accessible by everyone)
@router.get("/", response_model=list[schemas.SupplierRead])
def list_suppliers(db: Session = Depends(get_db)):
    return db.query(models.Supplier).all()
