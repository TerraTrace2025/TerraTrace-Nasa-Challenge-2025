from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from src.db.session import get_db
from src.db import models
from src.schemas import schemas
from src.api.dependencies.auth import get_current_company

router = APIRouter(prefix="/needs", tags=["needs"])

# POST: Create a new need (open for anyone)
@router.post("/", response_model=schemas.CompanyNeedsRead)
def create_need(need: schemas.CompanyNeedsCreate, db: Session = Depends(get_db)):
    db_need = models.CompanyNeeds(**need.dict())
    db.add(db_need)
    db.commit()
    db.refresh(db_need)
    return db_need

# GET: Retrieve all needs for the current logged-in company
@router.get("/", response_model=list[schemas.CompanyNeedsRead])
def get_current_company_needs(current_company: models.Company = Depends(get_current_company), db: Session = Depends(get_db)):
    needs = db.query(models.CompanyNeeds).filter(models.CompanyNeeds.company_id == current_company.id).all()
    return needs

# DELETE: Delete a need (only the owner company)
@router.delete("/{need_id}", response_model=schemas.MessageResponse)
def delete_need(need_id: int, current_company: models.Company = Depends(get_current_company), db: Session = Depends(get_db)):
    db_need = db.query(models.CompanyNeeds).get(need_id)
    if not db_need:
        raise HTTPException(status_code=404, detail="Need not found")
    if db_need.company_id != current_company.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: You can only delete your own company's needs"
        )
    db.delete(db_need)
    db.commit()
    return {"message": "Need deleted"}
