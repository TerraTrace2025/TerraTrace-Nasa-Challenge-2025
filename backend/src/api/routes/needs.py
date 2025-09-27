from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from src.db.session import get_db
from src.db import models
from src.schemas import schemas

router = APIRouter(prefix="/needs", tags=["needs"])

@router.post("/", response_model=schemas.CompanyNeedsRead)
def create_need(need: schemas.CompanyNeedsCreate, db: Session = Depends(get_db)):
    db_need = models.CompanyNeeds(**need.dict())
    db.add(db_need)
    db.commit()
    db.refresh(db_need)
    return db_need

@router.get("/", response_model=list[schemas.CompanyNeedsRead])
def list_needs(db: Session = Depends(get_db)):
    return db.query(models.CompanyNeeds).all()

@router.delete("/{need_id}")
def delete_need(need_id: int, db: Session = Depends(get_db)):
    db_need = db.query(models.CompanyNeeds).get(need_id)
    if not db_need:
        return {"error": "Need not found"}
    db.delete(db_need)
    db.commit()
    return {"message": "Need deleted"}

@router.get("/company/{company_id}", response_model=list[schemas.CompanyNeedsRead])
def get_needs_by_company(company_id: int, db: Session = Depends(get_db)):
    needs = db.query(models.CompanyNeeds).filter(models.CompanyNeeds.company_id == company_id).all()
    return needs
