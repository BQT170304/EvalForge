"""API Router aggregation for v1 endpoints."""

from fastapi import APIRouter

from evalforge.api.v1.datasets import router as datasets_router
from evalforge.api.v1.evaluate import router as evaluate_router
from evalforge.api.v1.experiments import router as experiments_router
from evalforge.api.v1.health import router as health_router
from evalforge.api.v1.metrics import router as metrics_router
from evalforge.api.v1.reports import router as reports_router

api_v1_router = APIRouter()

# Include all sub-routers
api_v1_router.include_router(health_router)
api_v1_router.include_router(evaluate_router)
api_v1_router.include_router(metrics_router)
api_v1_router.include_router(datasets_router)
api_v1_router.include_router(experiments_router)
api_v1_router.include_router(reports_router)
