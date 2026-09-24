from fastapi import APIRouter

from app.api.v1 import (
    analytics,
    audit,
    auth,
    business,
    data_quality,
    ml,
    opportunities,
    reports,
    scenarios,
    transactions,
)

api_router = APIRouter()
for module in (auth, business, transactions, data_quality, analytics, opportunities, scenarios, ml, audit, reports):
    api_router.include_router(module.router)
