"""Every /api/v1 route, one router per module (docs/ENDPOINTS.md lists them all)."""

from __future__ import annotations

from fastapi import APIRouter

from app.modules.audit.router import router as audit_router
from app.modules.auth.router import router as auth_router
from app.modules.exports.router import router as exports_router
from app.modules.platform.router import router as platform_router
from app.modules.tenants.router import router as tenants_router

api_router = APIRouter()
api_router.include_router(platform_router)
api_router.include_router(tenants_router)
api_router.include_router(auth_router)
api_router.include_router(audit_router)
api_router.include_router(exports_router)
