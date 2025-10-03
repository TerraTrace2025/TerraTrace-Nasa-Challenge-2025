from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.api.routes import api_router
from src.core.config import CORS_ORIGINS
import uvicorn
import os

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

    uvicorn.run(
        "src.app:app",
        host=host,
        port=8000,
        reload=reload_flag,
    )
