from pydantic import BaseModel
from typing import Optional
from datetime import datetime, date
from src.db.models import TransportMode, CropType, AlertType, Severity


# --- Company ---
class CompanyBase(BaseModel):
    name: str
    budget_limit: Optional[float] = None
    preferred_transport_modes: Optional[TransportMode] = None
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


# --- Company Needs ---
class CompanyNeedsBase(BaseModel):
    crop_type: CropType
    required_volume: float

class CompanyNeedsCreate(CompanyNeedsBase):
    company_id: int

class CompanyNeedsRead(CompanyNeedsBase):
    id: int
    created_at: datetime
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


# --- Company-Supplier Mapping ---
class CompanySupplierMappingBase(BaseModel):
    company_id: int
    supplier_id: int
    crop_type: CropType
    agreed_volume: float

class CompanySupplierMappingCreate(CompanySupplierMappingBase):
    pass

class CompanySupplierMappingRead(CompanySupplierMappingBase):
    id: int
    created_at: datetime
    class Config:
        from_attributes = True


# --- Alerts ---
class AlertBase(BaseModel):
    supplier_id: int
    alert_type: AlertType
    severity: Severity
    message: str

class AlertCreate(AlertBase):
    pass

class AlertRead(AlertBase):
    id: int
    created_at: datetime
    class Config:
        from_attributes = True


# --- Recommendations ---
class RecommendationBase(BaseModel):
    company_id: int
    risky_supplier_id: int
    alternative_supplier_id: int
    reasoning: Optional[str] = None

class RecommendationCreate(RecommendationBase):
    pass

class RecommendationRead(RecommendationBase):
    id: int
    created_at: datetime
    class Config:
        from_attributes = True


class MessageResponse(BaseModel):
    message: str