from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from src.db.session import get_db
from src.db import models
from src.schemas import schemas

router = APIRouter(prefix="/alerts", tags=["alerts"])

@router.post("/", response_model=schemas.AlertRead)
def create_alert(alert: schemas.AlertCreate, db: Session = Depends(get_db)):
    db_alert = models.Alert(**alert.dict())
    db.add(db_alert)
    db.commit()
    db.refresh(db_alert)
    return db_alert

@router.get("/", response_model=list[schemas.AlertRead])
def list_alerts(db: Session = Depends(get_db)):
    return db.query(models.Alert).all()

@router.delete("/{alert_id}")
def delete_alert(alert_id: int, db: Session = Depends(get_db)):
    db_alert = db.query(models.Alert).get(alert_id)
    if not db_alert:
        return {"error": "Alert not found"}
    db.delete(db_alert)
    db.commit()
    return {"message": "Alert deleted"}

@router.get("/company/{company_id}", response_model=list[schemas.AlertRead])
def get_alerts_by_company(company_id: int, db: Session = Depends(get_db)):
    # Alle Supplier IDs für diese Firma
    supplier_ids = (
        db.query(models.CompanySupplierMapping.supplier_id)
        .filter(models.CompanySupplierMapping.company_id == company_id)
        .distinct()
        .all()
    )
    supplier_ids = [sid[0] for sid in supplier_ids]
    alerts = db.query(models.Alert).filter(models.Alert.supplier_id.in_(supplier_ids)).all()
    return alerts
