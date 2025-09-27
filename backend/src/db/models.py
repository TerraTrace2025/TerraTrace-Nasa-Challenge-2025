from sqlalchemy import (
    Column, Integer, String, Float, Date, DateTime, ForeignKey, Text, Enum
)
from sqlalchemy.orm import relationship
from datetime import datetime
from src.db.base import Base
import enum


def now():
    return datetime.utcnow()


# --- Enums ---
class TransportMode(str, enum.Enum):
    truck = "truck"
    train = "train"
    ship = "ship"
    air = "air"


class CropType(str, enum.Enum):
    wheat = "wheat"
    rice = "rice"
    potatoes = "potatoes"
    corn = "corn"
    barley = "barley"


class AlertType(str, enum.Enum):
    climate_risk = "climate_risk"
    waste_risk = "waste_risk"


class Severity(str, enum.Enum):
    green = "green"
    yellow = "yellow"
    red = "red"


# --- Tables ---
class Company(Base):
    __tablename__ = "companies"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True, index=True)
    budget_limit = Column(Float, nullable=True)
    preferred_transport_modes = Column(Enum(TransportMode), nullable=True)
    created_at = Column(DateTime, default=now)
    updated_at = Column(DateTime, default=now, onupdate=now)

    country = Column(String, nullable=False)
    city = Column(String, nullable=False)
    street = Column(String, nullable=True)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)

    needs = relationship(
        "CompanyNeeds", back_populates="company", cascade="all, delete-orphan"
    )
    mappings = relationship(
        "CompanySupplierMapping", back_populates="company", cascade="all, delete-orphan"
    )


class CompanyNeeds(Base):
    __tablename__ = "company_needs"
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    crop_type = Column(Enum(CropType), nullable=False, index=True)
    required_volume = Column(Float, nullable=False)
    created_at = Column(DateTime, default=now)

    company = relationship("Company", back_populates="needs")


class Supplier(Base):
    __tablename__ = "suppliers"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    created_at = Column(DateTime, default=now)

    country = Column(String, nullable=False)
    city = Column(String, nullable=False)
    street = Column(String, nullable=True)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)

    stocks = relationship(
        "SupplierStock", back_populates="supplier", cascade="all, delete-orphan"
    )
    mappings = relationship(
        "CompanySupplierMapping", back_populates="supplier", cascade="all, delete-orphan"
    )


class SupplierStock(Base):
    __tablename__ = "supplier_stocks"
    id = Column(Integer, primary_key=True, index=True)
    supplier_id = Column(Integer, ForeignKey("suppliers.id", ondelete="CASCADE"), nullable=False)
    crop_type = Column(Enum(CropType), nullable=False)
    remaining_volume = Column(Float, nullable=False)
    price = Column(Float, nullable=True)
    expiry_date = Column(Date, nullable=True)
    created_at = Column(DateTime, default=now)

    supplier = relationship("Supplier", back_populates="stocks")


class CompanySupplierMapping(Base):
    __tablename__ = "company_supplier_mappings"
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    supplier_id = Column(Integer, ForeignKey("suppliers.id", ondelete="CASCADE"), nullable=False)
    crop_type = Column(Enum(CropType), nullable=False)
    agreed_volume = Column(Float, nullable=False)
    created_at = Column(DateTime, default=now)

    company = relationship("Company", back_populates="mappings")
    supplier = relationship("Supplier", back_populates="mappings")


class Alert(Base):
    __tablename__ = "alerts"
    id = Column(Integer, primary_key=True, index=True)
    supplier_id = Column(Integer, ForeignKey("suppliers.id", ondelete="CASCADE"), nullable=False)
    alert_type = Column(Enum(AlertType), nullable=False)
    severity = Column(Enum(Severity), nullable=False)
    message = Column(Text, nullable=False)
    created_at = Column(DateTime, default=now)

    supplier = relationship("Supplier")


class Recommendation(Base):
    __tablename__ = "recommendations"
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    risky_supplier_id = Column(Integer, ForeignKey("suppliers.id", ondelete="CASCADE"), nullable=False)
    alternative_supplier_id = Column(Integer, ForeignKey("suppliers.id", ondelete="CASCADE"), nullable=False)
    reasoning = Column(Text, nullable=True)
    created_at = Column(DateTime, default=now)

    company = relationship("Company")
    risky_supplier = relationship("Supplier", foreign_keys=[risky_supplier_id])
    alternative_supplier = relationship("Supplier", foreign_keys=[alternative_supplier_id])
