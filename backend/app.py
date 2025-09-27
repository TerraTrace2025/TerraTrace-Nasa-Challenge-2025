from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.api.routes import api_router
from src.core.config import CORS_ORIGINS
import uvicorn

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

print("Registered Endpoints:")
for route in app.routes:
    if hasattr(route, "methods") and hasattr(route, "path"):
        methods = ",".join(route.methods)
        print(f"{methods:10} -> {route.path}")


# --- Run with Uvicorn directly ---
if __name__ == "__main__":
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
