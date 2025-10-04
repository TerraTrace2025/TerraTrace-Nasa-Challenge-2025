from sqlalchemy.orm import Session
from src.db.session import SessionLocal, engine
from src.db import models, base
from datetime import date, timedelta
import random

def populate():
    # --- Create tables ---
    base.Base.metadata.create_all(bind=engine)
    db: Session = SessionLocal()

    try:
        # --- Clear existing data in proper order (children -> parents) ---
        db.query(models.CompanyStockMapping).delete()
        db.query(models.SupplierStock).delete()
        db.query(models.CompanyUser).delete()
        db.query(models.Supplier).delete()
        db.query(models.Company).delete()
        db.commit()

        # --- Companies ---
        companies_data = [
            {"name": "GreenFarm Inc", "budget_limit": 50000, "country": "Switzerland", "city": "Basel", "street": "Freie Strasse 80", "latitude": 47.5596, "longitude": 7.5886},
            {"name": "AgriCorp", "budget_limit": 75000, "country": "Switzerland", "city": "Bern", "street": "Bundesgasse 20", "latitude": 46.9481, "longitude": 7.4474},
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
                "name": "Sonnenhof Wohlen",
                "country": "Switzerland",
                "city": "Wohlen",
                "postcode": "5610",
                "latitude": 47.3501938,
                "longitude": 8.2790485,
                "elevation": 423.0,
                "crop_types": [models.CropType.soybean, models.CropType.wheat, models.CropType.barley, models.CropType.corn, models.CropType.sunflowerseed]
            },
            {
                "name": "Rudis Farm Worb",
                "country": "Switzerland",
                "city": "Worb",
                "postcode": "3076",
                "latitude": 46.9302365,
                "longitude": 7.5662725,
                "elevation": 607.0,
                "crop_types": [models.CropType.rapeseed, models.CropType.soybean, models.CropType.wheat, models.CropType.barley, models.CropType.corn, models.CropType.sunflowerseed]
            },
            {
                "name": "Biohof Melchnau",
                "country": "Switzerland",
                "city": "Melchnau",
                "postcode": "4917",
                "latitude": 47.1814972,
                "longitude": 7.8487757,
                "elevation": 556.0,
                "crop_types": [models.CropType.rapeseed, models.CropType.soybean, models.CropType.wheat, models.CropType.barley, models.CropType.corn, models.CropType.sunflowerseed]
            },
            {
                "name": "Alpenkorn Hof Schaan",
                "country": "Liechtenstein",
                "city": "Schaan",
                "postcode": "9494",
                "latitude": 47.1667928,
                "longitude": 9.5112894,
                "elevation": None,
                "crop_types": [models.CropType.rapeseed, models.CropType.wheat, models.CropType.corn]
            },
            {
                "name": "Courtepin Naturhof",
                "country": "Switzerland",
                "city": "Courtepin",
                "postcode": "1784",
                "latitude": 46.8655678,
                "longitude": 7.1229681,
                "elevation": None,
                "crop_types": [models.CropType.rapeseed, models.CropType.soybean, models.CropType.corn]
            },
            {
                "name": "Jura Kornhaus Porrentruy",
                "country": "Switzerland",
                "city": "Porrentruy",
                "postcode": "2900",
                "latitude": 47.382472,
                "longitude": 7.0985409,
                "elevation": 632.0,
                "crop_types": [models.CropType.rapeseed, models.CropType.soybean, models.CropType.wheat, models.CropType.corn, models.CropType.sunflowerseed]
            },
            {
                "name": "Obstgartenhof Märstetten",
                "country": "Switzerland",
                "city": "Märstetten",
                "postcode": "8560",
                "latitude": 47.5877643,
                "longitude": 9.0655244,
                "elevation": 415.0,
                "crop_types": [models.CropType.rapeseed, models.CropType.sunflowerseed]
            },
            {
                "name": "Orbe Kornspeicher",
                "country": "Switzerland",
                "city": "Orbe",
                "postcode": "1350",
                "latitude": 46.7249527,
                "longitude": 6.5328117,
                "elevation": 487.0,
                "crop_types": [models.CropType.rapeseed]
            },
            {
                "name": "Avenches Landhof",
                "country": "Switzerland",
                "city": "Avenches",
                "postcode": "1580",
                "latitude": 46.8800784,
                "longitude": 7.0403621,
                "elevation": 475.0,
                "crop_types": [models.CropType.rapeseed]
            },
            {
                "name": "Niederhasli Ackerhof",
                "country": "Switzerland",
                "city": "Niederhasli",
                "postcode": "8155",
                "latitude": 47.4791424,
                "longitude": 8.4872639,
                "elevation": 421.0,
                "crop_types": [models.CropType.rapeseed]
            },
            {
                "name": "Sonnenfeldhof Bätterkinden",
                "country": "Switzerland",
                "city": "Bätterkinden",
                "postcode": "3315",
                "latitude": 47.1349774,
                "longitude": 7.5364764,
                "elevation": 464.0,
                "crop_types": [models.CropType.rapeseed, models.CropType.corn, models.CropType.sunflowerseed]
            },
            {
                "name": "Bergwiesenhof Huttwil",
                "country": "Switzerland",
                "city": "Huttwil",
                "postcode": "4950",
                "latitude": 47.112213,
                "longitude": 7.8491741,
                "elevation": 655.0,
                "crop_types": [models.CropType.rapeseed, models.CropType.soybean, models.CropType.wheat, models.CropType.barley, models.CropType.corn]
            },
            {
                "name": "Laupen Kornfeldhof",
                "country": "Switzerland",
                "city": "Laupen",
                "postcode": "3177",
                "latitude": 46.9063781,
                "longitude": 7.2400154,
                "elevation": 478.0,
                "crop_types": [models.CropType.rapeseed, models.CropType.wheat, models.CropType.barley, models.CropType.corn, models.CropType.sunflowerseed]
            },
            {
                "name": "Herzogenbuchsee Hofgut",
                "country": "Switzerland",
                "city": "Herzogenbuchsee",
                "postcode": "3360",
                "latitude": 47.1894169,
                "longitude": 7.7063292,
                "elevation": None,
                "crop_types": [models.CropType.rapeseed, models.CropType.wheat, models.CropType.barley, models.CropType.corn]
            },
            {
                "name": "Laufen Mühlenhof",
                "country": "Switzerland",
                "city": "Laufen",
                "postcode": "4242",
                "latitude": 47.4199521,
                "longitude": 7.5006735,
                "elevation": None,
                "crop_types": [models.CropType.rapeseed, models.CropType.wheat, models.CropType.barley, models.CropType.corn, models.CropType.sunflowerseed]
            },
            {
                "name": "Rebgut Gelterkinden",
                "country": "Switzerland",
                "city": "Gelterkinden",
                "postcode": "4460",
                "latitude": 47.4642264,
                "longitude": 7.8555368,
                "elevation": 409.0,
                "crop_types": [models.CropType.rapeseed, models.CropType.wheat, models.CropType.barley, models.CropType.corn, models.CropType.sunflowerseed]
            },
            {
                "name": "Seelandhof Kerzers",
                "country": "Switzerland",
                "city": "Kerzers",
                "postcode": "3210",
                "latitude": 46.9729028,
                "longitude": 7.1928124,
                "elevation": 437.0,
                "crop_types": [models.CropType.rapeseed, models.CropType.soybean, models.CropType.wheat, models.CropType.corn, models.CropType.sunflowerseed]
            },
            {
                "name": "Jura Talhof Delémont",
                "country": "Switzerland",
                "city": "Delémont",
                "postcode": "2800",
                "latitude": 47.3643065,
                "longitude": 7.3454865,
                "elevation": None,
                "crop_types": [models.CropType.rapeseed]
            },
            {
                "name": "Berglandhof Cernier",
                "country": "Switzerland",
                "city": "Cernier",
                "postcode": "2053",
                "latitude": 47.0598115,
                "longitude": 6.9014078,
                "elevation": 830.0,
                "crop_types": [models.CropType.rapeseed]
            },
            {
                "name": "Eichenhof Eiken",
                "country": "Switzerland",
                "city": "Eiken",
                "postcode": "5074",
                "latitude": 47.5343174,
                "longitude": 7.9878434,
                "elevation": 328.0,
                "crop_types": [models.CropType.soybean, models.CropType.wheat, models.CropType.barley, models.CropType.corn, models.CropType.sunflowerseed]
            },
            {
                "name": "Zofingen Kornhof",
                "country": "Switzerland",
                "city": "Zofingen",
                "postcode": "4800",
                "latitude": 47.2862833,
                "longitude": 7.9486027,
                "elevation": 444.0,
                "crop_types": [models.CropType.soybean, models.CropType.wheat, models.CropType.barley]
            },
            {
                "name": "Hasle Sonnenberg Hof",
                "country": "Switzerland",
                "city": "Hasle-Rüegsau",
                "postcode": "3415",
                "latitude": 47.0160899,
                "longitude": 7.6565435,
                "elevation": None,
                "crop_types": [models.CropType.soybean, models.CropType.barley]
            },
            {
                "name": "Busswil Feldhof",
                "country": "Switzerland",
                "city": "Busswil b. Büren",
                "postcode": "3292",
                "latitude": 47.0993634,
                "longitude": 7.3221402,
                "elevation": 444.0,
                "crop_types": [models.CropType.soybean, models.CropType.wheat, models.CropType.barley, models.CropType.corn]
            },
            {
                "name": "Uetendorf Auenhof",
                "country": "Switzerland",
                "city": "Uetendorf",
                "postcode": "3661",
                "latitude": 46.7740609,
                "longitude": 7.5796278,
                "elevation": 553.0,
                "crop_types": [models.CropType.soybean, models.CropType.wheat, models.CropType.barley]
            },
            {
                "name": "Jussy Weingut",
                "country": "Switzerland",
                "city": "Jussy",
                "postcode": "1254",
                "latitude": 46.2320439,
                "longitude": 6.272693,
                "elevation": 478.0,
                "crop_types": [models.CropType.soybean, models.CropType.corn, models.CropType.sunflowerseed]
            },
            {
                "name": "Satigny Reb- und Kornhof",
                "country": "Switzerland",
                "city": "Satigny",
                "postcode": "1242",
                "latitude": 46.2138696,
                "longitude": 6.0399764,
                "elevation": 412.0,
                "crop_types": [models.CropType.soybean, models.CropType.corn, models.CropType.sunflowerseed]
            },
            {
                "name": "Landquart Alpenhof",
                "country": "Switzerland",
                "city": "Landquart",
                "postcode": "7302",
                "latitude": 46.962238,
                "longitude": 9.5635869,
                "elevation": None,
                "crop_types": [models.CropType.soybean]
            },
            {
                "name": "Seehof Sursee",
                "country": "Switzerland",
                "city": "Sursee",
                "postcode": "6210",
                "latitude": 47.1716724,
                "longitude": 8.106727,
                "elevation": 511.0,
                "crop_types": [models.CropType.soybean]
            },
            {
                "name": "Rheinblick Hof Schaffhausen",
                "country": "Switzerland",
                "city": "Schaffhausen",
                "postcode": "8207",
                "latitude": 47.7236103,
                "longitude": 8.6609547,
                "elevation": 457.0,
                "crop_types": [models.CropType.soybean, models.CropType.sunflowerseed]
            },
            {
                "name": "Messen Sonnenhof",
                "country": "Switzerland",
                "city": "Messen",
                "postcode": "3254",
                "latitude": 47.0990718,
                "longitude": 7.4358168,
                "elevation": 467.0,
                "crop_types": [models.CropType.soybean, models.CropType.sunflowerseed]
            },
            {
                "name": "Ammannsegg Kornhof",
                "country": "Switzerland",
                "city": "Lohn-Ammannsegg",
                "postcode": "4573",
                "latitude": 47.1707127,
                "longitude": 7.5286625,
                "elevation": 502.0,
                "crop_types": [models.CropType.soybean]
            },
            {
                "name": "Kölliken Feldhof",
                "country": "Switzerland",
                "city": "Kölliken",
                "postcode": "5742",
                "latitude": 47.3341488,
                "longitude": 8.0216498,
                "elevation": 438.0,
                "crop_types": [models.CropType.wheat, models.CropType.barley, models.CropType.corn]
            },
            {
                "name": "Schüpfen Kornkammer",
                "country": "Switzerland",
                "city": "Schüpfen",
                "postcode": "3054",
                "latitude": 47.039854,
                "longitude": 7.3755017,
                "elevation": None,
                "crop_types": [models.CropType.wheat, models.CropType.barley]
            },
            {
                "name": "Wichtrach Bauernhof",
                "country": "Switzerland",
                "city": "Wichtrach",
                "postcode": "3114",
                "latitude": 46.8443901,
                "longitude": 7.5743172,
                "elevation": None,
                "crop_types": [models.CropType.wheat, models.CropType.barley]
            },
            {
                "name": "Lyssach Hofgut",
                "country": "Switzerland",
                "city": "Lyssach",
                "postcode": "3421",
                "latitude": 47.0661146,
                "longitude": 7.5818154,
                "elevation": None,
                "crop_types": [models.CropType.wheat, models.CropType.barley]
            },
            {
                "name": "Ersigen Landhof",
                "country": "Switzerland",
                "city": "Ersigen",
                "postcode": "3423",
                "latitude": 47.0939692,
                "longitude": 7.6003717,
                "elevation": None,
                "crop_types": [models.CropType.wheat, models.CropType.barley, models.CropType.corn]
            },
            {
                "name": "Pontenet Bergbauernhof",
                "country": "Switzerland",
                "city": "Pontenet",
                "postcode": "2733",
                "latitude": 47.2438668,
                "longitude": 7.2544484,
                "elevation": None,
                "crop_types": [models.CropType.barley]
            },
            {
                "name": "Düdingen Landgut",
                "country": "Switzerland",
                "city": "Düdingen",
                "postcode": "3186",
                "latitude": 46.849259,
                "longitude": 7.1879193,
                "elevation": None,
                "crop_types": [models.CropType.corn]
            },
            {
                "name": "Alpenhof Steg",
                "country": "Switzerland",
                "city": "Steg",
                "postcode": "3940",
                "latitude": 46.3165452,
                "longitude": 7.7506697,
                "elevation": 700.0,
                "crop_types": [models.CropType.sunflowerseed]
            },
            {
                "name": "Marthaler Rebberg Hof",
                "country": "Switzerland",
                "city": "Marthalen",
                "postcode": "8460",
                "latitude": 47.6277669,
                "longitude": 8.6513989,
                "elevation": 390.0,
                "crop_types": [models.CropType.sunflowerseed]
            },
            {
                "name": "Bercher Kornfeldhof",
                "country": "Switzerland",
                "city": "Bercher",
                "postcode": "1038",
                "latitude": 46.6913831,
                "longitude": 6.7084457,
                "elevation": None,
                "crop_types": [models.CropType.sunflowerseed]
            },
            {
                "name": "Penthalaz Landhof",
                "country": "Switzerland",
                "city": "Penthalaz",
                "postcode": "1305",
                "latitude": 46.6084942,
                "longitude": 6.5247826,
                "elevation": 432.0,
                "crop_types": [models.CropType.sunflowerseed]
            },
        ]

        suppliers = []
        for sdata in suppliers_data:
            # *** WICHTIG: crop_types NICHT an Supplier übergeben ***
            supplier = models.Supplier(**{k: v for k, v in sdata.items() if k != "crop_types"})
            db.add(supplier)
            # crop_types für später (SupplierStock) merken
            suppliers.append((supplier, sdata.get("crop_types", [])))
        db.commit()

        # --- Supplier Stocks ---
        for supplier, crop_types in suppliers:
            for crop_type in crop_types:
                stock = models.SupplierStock(
                    supplier_id=supplier.id,
                    crop_type=crop_type,
                    remaining_volume=random.randint(50, 500),
                    price=round(random.uniform(10, 100), 2),
                    expiry_date=date.today() + timedelta(days=random.randint(5, 30)),
                    risk_score=random.randint(1, 100),  # random risk score
                    message=f"Dummy alert for {supplier.name} - {crop_type.value}"
                )
                db.add(stock)
        db.commit()

        # --- Company-to-Stock Mappings ---
        all_stocks = db.query(models.SupplierStock).all()
        for company in companies:
            if not all_stocks:
                break
            sampled_stocks = random.sample(all_stocks, k=min(5, len(all_stocks)))
            for stock in sampled_stocks:
                # agreed_volume: min 1, max remaining_volume
                max_agree = max(1, int(stock.remaining_volume))
                agreed_volume = random.randint(1, max_agree)
                mapping = models.CompanyStockMapping(
                    company_id=company.id,
                    supplier_id=stock.supplier_id,
                    stock_id=stock.id,
                    agreed_volume=agreed_volume,
                    transportation_mode=random.choice(list(models.TransportMode)),
                )
                db.add(mapping)
        db.commit()

        print("✅ Dummy data populated successfully!")

    finally:
        db.close()

if __name__ == "__main__":
    populate()
