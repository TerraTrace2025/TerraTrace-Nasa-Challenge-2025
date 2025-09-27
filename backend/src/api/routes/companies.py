from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from src.db.session import get_db
from src.db import models
from src.schemas import schemas
from src.api.dependencies.auth import get_current_company

router = APIRouter(prefix="/companies", tags=["companies"])

# POST: Create a new company (open for registration)
@router.post("/", response_model=schemas.CompanyRead)
def create_company(company: schemas.CompanyCreate, db: Session = Depends(get_db)):
    db_company = models.Company(**company.dict())
    db.add(db_company)
    db.commit()
    db.refresh(db_company)
    return db_company

# GET: Retrieve the current company's details
@router.get("/", response_model=schemas.CompanyRead)
def get_current_company_details(current_company: models.Company = Depends(get_current_company)):
    return current_company

# DELETE: Delete the current company
@router.delete("/")
def delete_current_company(current_company: models.Company = Depends(get_current_company), db: Session = Depends(get_db)):
    db.delete(current_company)
    db.commit()
    return {"message": "Company deleted"}
