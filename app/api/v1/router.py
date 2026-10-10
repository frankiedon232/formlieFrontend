"""Every /api/v1 route, one router per module (docs/ENDPOINTS.md lists them all)."""

from __future__ import annotations

from fastapi import APIRouter

from app.modules.platform.router import router as platform_router

api_router = APIRouter()
api_router.include_router(platform_router)
