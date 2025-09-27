from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from src.db.session import get_db
from src.db import models
from src.schemas import schemas

router = APIRouter(prefix="/companies", tags=["companies"])

@router.post("/", response_model=schemas.CompanyRead)
def create_company(company: schemas.CompanyCreate, db: Session = Depends(get_db)):
    db_company = models.Company(**company.dict())
    db.add(db_company)
    db.commit()
    db.refresh(db_company)
    return db_company

@router.get("/", response_model=list[schemas.CompanyRead])
def list_companies(db: Session = Depends(get_db)):
    return db.query(models.Company).all()

@router.delete("/{company_id}")
def delete_company(company_id: int, db: Session = Depends(get_db)):
    db_company = db.query(models.Company).get(company_id)
    if not db_company:
        return {"error": "Company not found"}
    db.delete(db_company)
    db.commit()
    return {"message": "Company deleted"}

