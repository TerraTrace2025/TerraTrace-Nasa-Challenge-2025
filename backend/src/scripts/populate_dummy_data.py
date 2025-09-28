from sqlalchemy.orm import Session
from src.db.session import SessionLocal, engine
from src.db.models import TransportMode
from src.db import models, base
from datetime import date, timedelta
import random

# --- Create tables ---
base.Base.metadata.create_all(bind=engine)
db: Session = SessionLocal()

# --- Clear existing data ---
db.query(models.CompanyUser).delete()
db.query(models.Recommendation).delete()
db.query(models.Alert).delete()
db.query(models.CompanyStockMapping).delete()
db.query(models.SupplierStock).delete()
db.query(models.Supplier).delete()
db.query(models.Company).delete()
db.commit()

# --- Companies ---
companies_data = [
    {
        "name": "GreenFarm Inc",
        "budget_limit": 50000,
        "country": "USA",
        "city": "San Francisco",
        "street": "123 Market St",
        "latitude": 37.7749,
        "longitude": -122.4194,
    },
    {
        "name": "AgriCorp",
        "budget_limit": 75000,
        "country": "Germany",
        "city": "Berlin",
        "street": "Unter den Linden 5",
        "latitude": 52.5200,
        "longitude": 13.4050,
    },
]

companies = []
for cdata in companies_data:
    company = models.Company(**cdata)
    db.add(company)
    companies.append(company)
db.commit()

# --- Company Users ---
dummy_passwords = ["123", "abc"]
for company, pwd in zip(companies, dummy_passwords):
    user = models.CompanyUser(company_id=company.id)
    user.set_password(pwd)
    db.add(user)
db.commit()

# --- Suppliers ---
suppliers_data = [
    {"name": "Supplier A", "country": "USA", "city": "Los Angeles", "street": "456 Sunset Blvd", "latitude": 34.0522, "longitude": -118.2437},
    {"name": "Supplier B", "country": "Germany", "city": "Munich", "street": "789 Marienplatz", "latitude": 48.1351, "longitude": 11.5820},
    {"name": "Supplier C", "country": "France", "city": "Paris", "street": "10 Rue de Rivoli", "latitude": 48.8566, "longitude": 2.3522},
]

suppliers = []
for sdata in suppliers_data:
    supplier = models.Supplier(**sdata)
    db.add(supplier)
    suppliers.append(supplier)
db.commit()

# --- Supplier Stocks ---
for supplier in suppliers:
    for crop in models.CropType:
        stock = models.SupplierStock(
            supplier_id=supplier.id,
            crop_type=crop,
            remaining_volume=random.randint(50, 500),
            price=round(random.uniform(10, 100), 2),
            expiry_date=date.today() + timedelta(days=random.randint(5, 30)),
        )
        db.add(stock)
db.commit()

# --- Company-to-Stock Mappings ---
all_stocks = db.query(models.SupplierStock).all()
for company in companies:
    sampled_stocks = random.sample(all_stocks, k=3)
    for stock in sampled_stocks:
        mapping = models.CompanyStockMapping(
            company_id=company.id,
            stock_id=stock.id,
            agreed_volume=random.randint(10, int(stock.remaining_volume)),
            transportation_mode=TransportMode.train
        )
        db.add(mapping)
db.commit()

# --- Alerts ---
for supplier in suppliers:
    alert = models.Alert(
        supplier_id=supplier.id,
        alert_type=random.choice(list(models.AlertType)),
        severity=random.choice(list(models.Severity)),
        message=f"Dummy alert for {supplier.name}"
    )
    db.add(alert)
db.commit()

print("✅ Dummy data populated successfully!")
db.close()
