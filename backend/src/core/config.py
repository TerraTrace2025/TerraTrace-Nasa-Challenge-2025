from typing import List

# path to DB file
DB_URL = "sqlite:///./backend/src/app.db"
CORS_ORIGINS: List[str] = [
    "http://localhost",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]
