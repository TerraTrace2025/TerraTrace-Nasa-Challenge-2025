import os
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.api.routes import api_router
from src.core.config import CORS_ORIGINS
from src.scripts import populate_dummy_data
import uvicorn

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("food_waste_api")

app = FastAPI(title="Food-waste Match & Monitoring API")

# CORS setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Attach API router
app.include_router(api_router, prefix="/api")

for route in app.routes:
    if hasattr(route, "methods") and hasattr(route, "path"):
        methods = ",".join(route.methods)
        print(f"{methods:10} -> {route.path}")


if __name__ == "__main__":
    host = os.getenv("FASTAPI_HOST", "127.0.0.1")
    reload_flag = os.getenv("FASTAPI_RELOAD", "True").lower() in ("true", "1", "yes")

    logger.info("Starting Food-waste API...")
    logger.info(f"Host: {host}, Reload: {reload_flag}")

    if not reload_flag:
        logger.info("Populating dummy data...")
        populate_dummy_data.populate()

    uvicorn.run(
        "src.app:app",
        host=host,
        port=8000,
        reload=reload_flag,
    )
