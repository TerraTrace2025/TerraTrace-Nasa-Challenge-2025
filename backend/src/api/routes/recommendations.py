from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from src.db.session import get_db
from src.db import models
from src.schemas import schemas

router = APIRouter(prefix="/recommendations", tags=["recommendations"])

@router.post("/", response_model=schemas.RecommendationRead)
def create_recommendation(rec: schemas.RecommendationCreate, db: Session = Depends(get_db)):
    db_rec = models.Recommendation(**rec.dict())
    db.add(db_rec)
    db.commit()
    db.refresh(db_rec)
    return db_rec

@router.get("/", response_model=list[schemas.RecommendationRead])
def list_recommendations(db: Session = Depends(get_db)):
    return db.query(models.Recommendation).all()

@router.delete("/{rec_id}")
def delete_recommendation(rec_id: int, db: Session = Depends(get_db)):
    db_rec = db.query(models.Recommendation).get(rec_id)
    if not db_rec:
        return {"error": "Recommendation not found"}
    db.delete(db_rec)
    db.commit()
    return {"message": "Recommendation deleted"}

@router.get("/company/{company_id}", response_model=list[schemas.RecommendationRead])
def get_recommendations_by_company(company_id: int, db: Session = Depends(get_db)):
    recs = db.query(models.Recommendation).filter(models.Recommendation.company_id == company_id).all()
    return recs
