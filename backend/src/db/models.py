from sqlalchemy import Column, Integer, String, Float, Date, DateTime, ForeignKey, Text, Enum
from sqlalchemy.orm import relationship
from datetime import datetime
from src.db.base import Base
import enum
from passlib.context import CryptContext

def now():
    return datetime.utcnow()


# --- Enums ---
class TransportMode(str, enum.Enum):
    truck = "truck"
    train = "train"


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
    created_at = Column(DateTime, default=now)
    updated_at = Column(DateTime, default=now, onupdate=now)

    # Address info
    country = Column(String, nullable=False)
    city = Column(String, nullable=False)
    street = Column(String, nullable=True)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)

    # Relationships
    stock_mappings = relationship(
        "CompanyStockMapping", back_populates="company", cascade="all, delete-orphan"
    )

    user = relationship(
        "CompanyUser", back_populates="company", uselist=False, cascade="all, delete-orphan"
    )


class Supplier(Base):
    __tablename__ = "suppliers"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    created_at = Column(DateTime, default=now)

    # Address info
    country = Column(String, nullable=False)
    city = Column(String, nullable=False)
    street = Column(String, nullable=True)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)

    # Relationships
    stocks = relationship(
        "SupplierStock", back_populates="supplier", cascade="all, delete-orphan"
    )
    alerts = relationship("Alert", back_populates="supplier", cascade="all, delete-orphan")


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

    # Mapping to companies
    company_mappings = relationship(
        "CompanyStockMapping", back_populates="stock", cascade="all, delete-orphan"
    )


class CompanyStockMapping(Base):
    __tablename__ = "company_stock_mappings"
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    stock_id = Column(Integer, ForeignKey("supplier_stocks.id", ondelete="CASCADE"), nullable=False)
    agreed_volume = Column(Float, nullable=False)
    created_at = Column(DateTime, default=now)
    transportation_mode = Column(Enum(TransportMode), nullable=False)

    company = relationship("Company", back_populates="stock_mappings")
    stock = relationship("SupplierStock", back_populates="company_mappings")


class Alert(Base):
    __tablename__ = "alerts"
    id = Column(Integer, primary_key=True, index=True)
    supplier_id = Column(Integer, ForeignKey("suppliers.id", ondelete="CASCADE"), nullable=False)
    alert_type = Column(Enum(AlertType), nullable=False)
    severity = Column(Enum(Severity), nullable=False)
    message = Column(Text, nullable=False)
    created_at = Column(DateTime, default=now)

    supplier = relationship("Supplier", back_populates="alerts")


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


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class CompanyUser(Base):
    __tablename__ = "company_users"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, unique=True)
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime, default=now)
    updated_at = Column(DateTime, default=now, onupdate=now)

    company = relationship("Company", back_populates="user")

    def set_password(self, password: str):
        self.hashed_password = pwd_context.hash(password)

    def verify_password(self, password: str) -> bool:
        return pwd_context.verify(password, self.hashed_password)
