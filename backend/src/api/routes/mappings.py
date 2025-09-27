from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from src.db.session import get_db
from src.db import models
from src.schemas import schemas
from src.api.dependencies.auth import get_current_company

router = APIRouter(prefix="/mappings", tags=["mappings"])

# POST: Create a new mapping (only current company)
@router.post("/", response_model=schemas.CompanySupplierMappingRead)
def create_mapping(mapping: schemas.CompanySupplierMappingCreate, current_company: models.Company = Depends(get_current_company), db: Session = Depends(get_db)):
    if mapping.company_id != current_company.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: You can only create mappings for your own company"
        )
    db_mapping = models.CompanySupplierMapping(**mapping.dict())
    db.add(db_mapping)
    db.commit()
    db.refresh(db_mapping)
    return db_mapping

# GET: List all mappings for the current company
@router.get("/", response_model=list[schemas.CompanySupplierMappingRead])
def list_mappings(current_company: models.Company = Depends(get_current_company), db: Session = Depends(get_db)):
    return db.query(models.CompanySupplierMapping).filter(
        models.CompanySupplierMapping.company_id == current_company.id
    ).all()

# DELETE: Delete a mapping (only current company)
@router.delete("/{mapping_id}", response_model=schemas.MessageResponse)
def delete_mapping(mapping_id: int, current_company: models.Company = Depends(get_current_company), db: Session = Depends(get_db)):
    db_mapping = db.query(models.CompanySupplierMapping).get(mapping_id)
    if not db_mapping:
        raise HTTPException(status_code=404, detail="Mapping not found")
    if db_mapping.company_id != current_company.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: You can only delete mappings for your own company"
        )
    db.delete(db_mapping)
    db.commit()
    return {"message": "Mapping deleted"}
