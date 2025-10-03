from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from src.db.session import get_db
from src.db import models
from src.schemas import schemas
from src.api.dependencies.auth import get_current_company

router = APIRouter(prefix="/alerts", tags=["alerts"])

# GET: Retrieve all alerts for the current company
@router.get("/company", response_model=list[schemas.AlertRead])
def get_alerts_for_current_company(current_company: models.Company = Depends(get_current_company), db: Session = Depends(get_db)):
    # Get all supplier IDs associated with this company
    supplier_ids = (
        db.query(models.CompanySupplierMapping.supplier_id)
        .filter(models.CompanySupplierMapping.company_id == current_company.id)
        .distinct()
        .all()
    )
    supplier_ids = [sid[0] for sid in supplier_ids]

    # Get all alerts for these suppliers
    alerts = db.query(models.Alert).filter(models.Alert.supplier_id.in_(supplier_ids)).all()
    return alerts
