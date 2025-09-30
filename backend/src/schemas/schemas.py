from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, date
from src.db.models import TransportMode, CropType

# --- Company ---
class CompanyBase(BaseModel):
    name: str
    budget_limit: Optional[float] = None
    country: str
    city: str
    street: Optional[str] = None
    latitude: float
    longitude: float

class CompanyCreate(CompanyBase):
    pass

class CompanyRead(CompanyBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# --- Supplier ---
class SupplierBase(BaseModel):
    name: str
    country: str
    city: str
    street: Optional[str] = None
    latitude: float
    longitude: float

class SupplierCreate(SupplierBase):
    pass

class SupplierRead(SupplierBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


# --- Supplier Stock ---
class SupplierStockBase(BaseModel):
    crop_type: CropType
    remaining_volume: float
    price: Optional[float] = None
    expiry_date: Optional[date] = None

class SupplierStockCreate(SupplierStockBase):
    supplier_id: int

class SupplierStockRead(SupplierStockBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


# --- Company-Stock Mapping ---
class CompanyStockMappingBase(BaseModel):
    company_id: int
    stock_id: int
    agreed_volume: float
    transportation_mode: TransportMode

class CompanyStockMappingCreate(CompanyStockMappingBase):
    pass

class CompanyStockMappingRead(CompanyStockMappingBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


# --- Alerts ---
class AlertBase(BaseModel):
    supplier_id: int
    risk_score: int
    message: str

class AlertCreate(AlertBase):
    pass

class AlertRead(AlertBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

# --- General Response ---
class MessageResponse(BaseModel):
    message: str
