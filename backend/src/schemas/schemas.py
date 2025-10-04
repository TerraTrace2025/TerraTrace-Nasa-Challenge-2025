from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, date
from src.db.models import TransportMode, CropType, AlertType

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


class SupplierStockRead(BaseModel):
    id: int
    supplier_id: int
    supplier_name: str
    crop_type: str
    price: float | None
    expiry_date: str | None
    risk_class: AlertType | None
    message: str | None
    created_at: str

    class Config:
        from_attributes = True


# --- Company-Stock Mapping ---
class CompanyStockMappingBase(BaseModel):
    company_id: int
    stock_id: int
    supplier_id: int     # <-- Add supplier_id here
    transportation_mode: TransportMode

class CompanyStockMappingCreate(CompanyStockMappingBase):
    pass

class CompanyStockMappingRead(CompanyStockMappingBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True



# --- General Response ---
class MessageResponse(BaseModel):
    message: str
