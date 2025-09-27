from fastapi import APIRouter
from . import companies, suppliers, stocks, needs, mappings, alerts, recommendations, auth

api_router = APIRouter()

api_router.include_router(auth.router)
api_router.include_router(companies.router)
api_router.include_router(suppliers.router)
api_router.include_router(stocks.router)
api_router.include_router(needs.router)
api_router.include_router(mappings.router)
api_router.include_router(alerts.router)
api_router.include_router(recommendations.router)
