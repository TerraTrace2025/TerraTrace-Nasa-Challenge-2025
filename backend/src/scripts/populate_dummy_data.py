from sqlalchemy.orm import Session
from src.db.session import SessionLocal, engine
from src.db.models import TransportMode
from src.db import models, base
from datetime import date, timedelta
import random

def populate():
    # --- Create tables ---
    base.Base.metadata.create_all(bind=engine)
    db: Session = SessionLocal()

    # --- Clear existing data ---
    db.query(models.CompanyUser).delete()
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
            "country": "Switzerland",
            "city": "Basel",
            "street": "Freie Strasse 80",
            "latitude": 47.5596,
            "longitude": 7.5886,
        },
        {
            "name": "AgriCorp",
            "budget_limit": 75000,
            "country": "Switzerland",
            "city": "Bern",
            "street": "Bundesgasse 20",
            "latitude": 46.9481,
            "longitude": 7.4474,
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
        {
            "name": "Supplier A",
            "country": "Switzerland",
            "city": "Zurich",
            "street": "Bahnhofstrasse 100",
            "latitude": 47.3769,
            "longitude": 8.5417
        },
        {
            "name": "Supplier B",
            "country": "Switzerland",
            "city": "Bern",
            "street": "Bundesplatz 5",
            "latitude": 46.9481,
            "longitude": 7.4474
        },
        {
            "name": "Supplier C",
            "country": "Switzerland",
            "city": "Geneva",
            "street": "Rue du Rhône 50",
            "latitude": 46.2044,
            "longitude": 6.1432
        }
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
            risk_score=random.random(),
            message=f"Dummy alert for {supplier.name}"
        )
        db.add(alert)
    db.commit()

    print("✅ Dummy data populated successfully!")
    db.close()

if __name__ == "__main__":
    populate()