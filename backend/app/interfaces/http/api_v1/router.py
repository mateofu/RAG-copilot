from fastapi import APIRouter

from app.interfaces.http.api_v1.health import router as health_router

api_router = APIRouter()
api_router.include_router(health_router)
