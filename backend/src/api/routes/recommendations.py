from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from src.db.session import get_db
from src.db import models
from src.schemas import schemas
from src.api.dependencies.auth import get_current_company

router = APIRouter(prefix="/recommendations", tags=["recommendations"])

# GET: Retrieve all recommendations for the current company
@router.get("/company", response_model=list[schemas.RecommendationRead])
def get_recommendations_for_current_company(
    current_company: models.Company = Depends(get_current_company),
    db: Session = Depends(get_db)
):
    recs = db.query(models.Recommendation).filter(models.Recommendation.company_id == current_company.id).all()
    return recs
