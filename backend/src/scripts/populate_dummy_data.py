from sqlalchemy.orm import Session
from src.db.session import SessionLocal, engine
from src.db import models, base
from datetime import date, timedelta
import random

# Create tables if they don't exist
base.Base.metadata.create_all(bind=engine)

db: Session = SessionLocal()

# --- Clear existing data ---
db.query(models.Recommendation).delete()
db.query(models.Alert).delete()
db.query(models.CompanySupplierMapping).delete()
db.query(models.SupplierStock).delete()
db.query(models.CompanyNeeds).delete()
db.query(models.Supplier).delete()
db.query(models.Company).delete()
db.commit()

# --- Dummy Companies ---
companies_data = [
    {
        "name": "GreenFarm Inc",
        "budget_limit": 50000,
        "preferred_transport_modes": models.TransportMode.truck,
        "country": "USA",
        "city": "San Francisco",
        "street": "123 Market St",
        "latitude": 37.7749,
        "longitude": -122.4194
    },
    {
        "name": "AgriCorp",
        "budget_limit": 75000,
        "preferred_transport_modes": models.TransportMode.train,
        "country": "Germany",
        "city": "Berlin",
        "street": "Unter den Linden 5",
        "latitude": 52.5200,
        "longitude": 13.4050
    },
]

companies = []
for cdata in companies_data:
    c = models.Company(**cdata)
    db.add(c)
    companies.append(c)
db.commit()

# --- Dummy Suppliers ---
suppliers_data = [
    {
        "name": "Supplier A",
        "country": "USA",
        "city": "Los Angeles",
        "street": "456 Sunset Blvd",
        "latitude": 34.0522,
        "longitude": -118.2437
    },
    {
        "name": "Supplier B",
        "country": "Germany",
        "city": "Munich",
        "street": "789 Marienplatz",
        "latitude": 48.1351,
        "longitude": 11.5820
    },
    {
        "name": "Supplier C",
        "country": "France",
        "city": "Paris",
        "street": "10 Rue de Rivoli",
        "latitude": 48.8566,
        "longitude": 2.3522
    },
]

suppliers = []
for sdata in suppliers_data:
    s = models.Supplier(**sdata)
    db.add(s)
    suppliers.append(s)
db.commit()

# --- Dummy Stocks ---
for supplier in suppliers:
    for crop in models.CropType:
        stock = models.SupplierStock(
            supplier_id=supplier.id,
            crop_type=crop,
            remaining_volume=random.randint(50, 500),
            price=random.uniform(10, 100),
            expiry_date=date.today() + timedelta(days=random.randint(5, 30))
        )
        db.add(stock)
db.commit()

# --- Dummy Company Needs ---
for company in companies:
    for crop in models.CropType:
        need = models.CompanyNeeds(
            company_id=company.id,
            crop_type=crop,
            required_volume=random.randint(20, 200)
        )
        db.add(need)
db.commit()

# --- Dummy Mappings (random) ---
for company in companies:
    for need in company.needs:
        supplier = random.choice(suppliers)
        mapping = models.CompanySupplierMapping(
            company_id=company.id,
            supplier_id=supplier.id,
            crop_type=need.crop_type,
            agreed_volume=min(need.required_volume, random.randint(10, 100))
        )
        db.add(mapping)
db.commit()

# --- Dummy Alerts ---
for supplier in suppliers:
    alert = models.Alert(
        supplier_id=supplier.id,
        alert_type=random.choice(list(models.AlertType)),
        severity=random.choice(list(models.Severity)),
        message="Dummy alert message"
    )
    db.add(alert)
db.commit()

# --- Dummy Recommendations ---
for company in companies:
    for mapping in company.mappings:
        alt_supplier = random.choice([s for s in suppliers if s.id != mapping.supplier_id])
        rec = models.Recommendation(
            company_id=company.id,
            risky_supplier_id=mapping.supplier_id,
            alternative_supplier_id=alt_supplier.id,
            reasoning="Dummy recommendation reasoning"
        )
        db.add(rec)
db.commit()

print("✅ Dummy data populated successfully!")
db.close()
