"""Every /api/v1 route, one router per module (docs/ENDPOINTS.md lists them all)."""

from __future__ import annotations

from fastapi import APIRouter

from app.modules.audit.router import router as audit_router
from app.modules.auth.router import router as auth_router
from app.modules.dashboard.router import router as navigation_router
from app.modules.data_sources.router import router as data_sources_router
from app.modules.destinations.router import router as destinations_router
from app.modules.design.router import router as design_router
from app.modules.exports.router import router as exports_router
from app.modules.forms.builder import router as builder_router
from app.modules.forms.overview import router as overview_router
from app.modules.forms.router import router as forms_router
from app.modules.links.invites import router as form_invites_router
from app.modules.links.router import router as links_router
from app.modules.notifications.router import router as notifications_router
from app.modules.public.router import router as public_router
from app.modules.responses.exports import router as response_exports_router
from app.modules.responses.files import router as response_files_router
from app.modules.responses.router import router as responses_router
from app.modules.lists.router import router as lists_router
from app.modules.templates.router import router as templates_router
from app.modules.onboarding.router import router as onboarding_router
from app.modules.org.router import router as org_router
from app.modules.people.invites import router as invites_router
from app.modules.people.me import router as me_router
from app.modules.people.router import router as people_router
from app.modules.platform.router import router as platform_router
from app.modules.rbac.router import router as roles_router
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
api_router.include_router(roles_router)
api_router.include_router(invites_router)  # before people: /people/signup-link, /people/invites
api_router.include_router(people_router)
api_router.include_router(me_router)
api_router.include_router(form_invites_router)  # before forms: /forms/pass
api_router.include_router(links_router)  # before forms: /forms/{id}/share, /access, /short-link
api_router.include_router(builder_router)  # before forms: /forms/{id}/publish is not a lifecycle step
api_router.include_router(forms_router)
api_router.include_router(overview_router)
api_router.include_router(design_router)
api_router.include_router(data_sources_router)
api_router.include_router(destinations_router)
api_router.include_router(lists_router)
api_router.include_router(templates_router)
api_router.include_router(notifications_router)
api_router.include_router(public_router)
api_router.include_router(response_exports_router)  # before responses: /responses/exports
api_router.include_router(response_files_router)
api_router.include_router(responses_router)
api_router.include_router(settings_router)  # after any module with its own /settings/{name} route (sso, B11)
