from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from src.db.session import get_db
from src.db import models
from src.schemas import schemas
from src.api.dependencies.auth import get_current_company

router = APIRouter(prefix="/mappings", tags=["mappings"])

@router.post("/", response_model=schemas.CompanyStockMappingRead)
def create_mapping(mapping: schemas.CompanyStockMappingCreate,
                   current_company: models.Company = Depends(get_current_company),
                   db: Session = Depends(get_db)):
    if mapping.company_id != current_company.id:
        raise HTTPException(status_code=403, detail="Forbidden")
    db_mapping = models.CompanyStockMapping(**mapping.dict())
    db.add(db_mapping)
    db.commit()
    db.refresh(db_mapping)
    return db_mapping


@router.get("/", response_model=list[schemas.CompanyStockMappingRead])
def list_mappings(current_company: models.Company = Depends(get_current_company),
                  db: Session = Depends(get_db)):
    return db.query(models.CompanyStockMapping).filter(
        models.CompanyStockMapping.company_id == current_company.id
    ).all()
