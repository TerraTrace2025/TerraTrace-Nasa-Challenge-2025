from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from src.db.session import get_db
from src.db import models
from src.api.dependencies.auth import create_access_token

router = APIRouter(prefix="/auth", tags=["auth"])

class LoginRequest(BaseModel):
    company_name: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str

@router.post("/login", response_model=TokenResponse)
def login(data: LoginRequest, db: Session = Depends(get_db)):
    company = db.query(models.Company).filter(models.Company.name == data.company_name).first()
    if not company:
        raise HTTPException(status_code=400, detail="Invalid credentials")

    user = db.query(models.CompanyUser).filter(models.CompanyUser.company_id == company.id).first()
    if not user or not user.verify_password(data.password):
        raise HTTPException(status_code=400, detail="Invalid credentials")

    token = create_access_token({"sub": str(company.id)})
    return {"access_token": token, "token_type": "bearer"}
