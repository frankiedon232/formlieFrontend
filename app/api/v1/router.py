"""Every /api/v1 route, one router per module (docs/ENDPOINTS.md lists them all)."""

from __future__ import annotations

from fastapi import APIRouter

from app.modules.audit.router import router as audit_router
from app.modules.auth.router import router as auth_router
from app.modules.dashboard.router import router as navigation_router
from app.modules.exports.router import router as exports_router
from app.modules.onboarding.router import router as onboarding_router
from app.modules.org.router import router as org_router
from app.modules.platform.router import router as platform_router
from app.modules.settings.router import router as settings_router
from app.modules.tenants.router import router as tenants_router
from app.modules.uploads.router import router as uploads_router

api_router = APIRouter()
api_router.include_router(platform_router)
api_router.include_router(tenants_router)
api_router.include_router(auth_router)
api_router.include_router(audit_router)
api_router.include_router(exports_router)
api_router.include_router(uploads_router)
api_router.include_router(onboarding_router)
api_router.include_router(org_router)
api_router.include_router(navigation_router)
api_router.include_router(settings_router)  # after any module with its own /settings/{name} route (sso, B11)
