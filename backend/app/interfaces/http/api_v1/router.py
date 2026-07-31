from fastapi import APIRouter

from app.interfaces.http.api_v1.auth import router as auth_router
from app.interfaces.http.api_v1.conversations import router as conversations_router
from app.interfaces.http.api_v1.documents import router as documents_router
from app.interfaces.http.api_v1.health import router as health_router
from app.interfaces.http.api_v1.identity import router as identity_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(auth_router)
api_router.include_router(identity_router)
api_router.include_router(documents_router)
api_router.include_router(conversations_router)
