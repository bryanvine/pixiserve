from fastapi import APIRouter

from app.api.v1 import auth, assets, health, system

api_router = APIRouter()

api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(assets.router, prefix="/assets", tags=["assets"])
api_router.include_router(system.router, prefix="/system", tags=["system"])
