from fastapi import APIRouter

from app.api.candidates import router as candidates_router
from app.api.export import router as export_router
from app.api.health import router as health_router
from app.api.jobs import router as jobs_router
from app.api.sync import router as sync_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(jobs_router)
api_router.include_router(candidates_router)
api_router.include_router(sync_router)
api_router.include_router(export_router)
