from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from src.db.session import get_db
from src.db import models
from src.schemas import schemas

router = APIRouter(prefix="/mappings", tags=["mappings"])

@router.post("/", response_model=schemas.CompanySupplierMappingRead)
def create_mapping(mapping: schemas.CompanySupplierMappingCreate, db: Session = Depends(get_db)):
    db_mapping = models.CompanySupplierMapping(**mapping.dict())
    db.add(db_mapping)
    db.commit()
    db.refresh(db_mapping)
    return db_mapping

@router.get("/", response_model=list[schemas.CompanySupplierMappingRead])
def list_mappings(db: Session = Depends(get_db)):
    return db.query(models.CompanySupplierMapping).all()

@router.delete("/{mapping_id}")
def delete_mapping(mapping_id: int, db: Session = Depends(get_db)):
    db_mapping = db.query(models.CompanySupplierMapping).get(mapping_id)
    if not db_mapping:
        return {"error": "Mapping not found"}
    db.delete(db_mapping)
    db.commit()
    return {"message": "Mapping deleted"}

@router.get("/company/{company_id}/suppliers", response_model=list[schemas.SupplierRead])
def get_suppliers_by_company(company_id: int, db: Session = Depends(get_db)):
    supplier_ids = (
        db.query(models.CompanySupplierMapping.supplier_id)
        .filter(models.CompanySupplierMapping.company_id == company_id)
        .distinct()
        .all()
    )
    supplier_ids = [sid[0] for sid in supplier_ids]
    suppliers = db.query(models.Supplier).filter(models.Supplier.id.in_(supplier_ids)).all()
    return suppliers
