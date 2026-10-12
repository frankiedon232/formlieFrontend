"""Edge routes (2026-10-12): what Formalie's Cloudflare Worker asks while it serves the static front end.

    GET /edge/forms/{key}/preview   a public form's link preview (title, description, image, language) for the
                                    page's <head>, so shared links and search engines see the form, not an empty SPA;
                                    `embed_ancestors`: the websites allowed to frame its /embed page (frame-ancestors)
    GET /edge/links/{code}          where a short link leads (`/s/{code}` answers with a redirect there)

Plain JSON (envelope.py plaintext list). They answer only a request that carries the right X-Formalie-Edge
(request_context.py, `ctx.edge_trusted`); anything else gets the plain 404 of a route that does not exist. The
workspace comes from the forwarded host exactly as for the public form page (public/service.py), so the same
rules decide what can be opened. Only what anyone holding the link may see: never answers or private settings.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

from app.core.config import get_settings
from app.core.context import get_context
from app.core.db.session import db_session
from app.core.errors import FrmError
from app.core.security.limits import rate_limit
from app.modules.links.seo import published_schema, seo_of
from app.modules.links.urls import frame_ancestors
from app.modules.public import rules, service
from app.modules.public.router import resolve_short_link
from app.modules.uploads.service import completed_url

router = APIRouter(tags=["edge"], include_in_schema=False)

CACHE = {"cache-control": "public, max-age=60", "vary": "X-Forwarded-Host"}
NOT_FOUND = {"error": {"code": "FRM-FORM-1001"}}
# Members-only and invitation-only forms stay private: no title or description for whoever holds the address
PRIVATE_ACCESS = ("invite", "organisation")
# Published (answers or not right now); closed, archived and never published forms are not shown
SHOWN_STATES = ("open", "expired", "scheduled", "limit_reached")


def _require_edge() -> None:
    ctx = get_context()
    if not (ctx and ctx.edge_trusted):
        raise HTTPException(status_code=404)  # looks like a route that does not exist


def _absent() -> JSONResponse:
    return JSONResponse(NOT_FOUND, status_code=404, headers={"cache-control": "no-store"})


@router.get("/edge/forms/{key}/preview", dependencies=[Depends(_require_edge), rate_limit("edge-preview", per_minute=600)])
async def form_preview(key: str) -> Any:
    try:
        tenant = await service.workspace_for(key)
        async with db_session("read", **service.scope_of(tenant)) as db:
            form = await service.find_form(db, tenant, key, "link")
            published = await published_schema(db, form)
            state = service.state_of(tenant, form)
            if published is None or state not in SHOWN_STATES or form.access in PRIVATE_ACCESS:
                return _absent()
            seo = await seo_of(db, form, published_only=True)
            image_path = await completed_url(db, tenant.id, seo["image_upload_id"]) if seo["image_upload_id"] else None
    except FrmError:
        return _absent()
    ctx = get_context()
    host = (ctx.host if ctx else None) or ""
    return JSONResponse({
        "title": seo["title"],
        "description": seo["description"] or None,
        "image_url": f"https://{host}{image_path}" if image_path and host else None,
        "language": rules.form_languages(published)[0],
        "indexable": state == "open" and not seo["noindex"],  # the same rule as the page's own noindex
        "site_name": tenant.name,
        # The embed page's frame-ancestors, the same CSP source list the public form gives (PublicForm.embed_ancestors)
        "embed_ancestors": frame_ancestors(list(form.embed_domains or []), get_settings().root_domain),
    }, headers=CACHE)


@router.get("/edge/links/{code}", dependencies=[Depends(_require_edge), rate_limit("edge-link", per_minute=600)])
async def short_link(code: str) -> Any:
    try:
        location = await resolve_short_link(code)  # the same rules as /s/ (the visit is counted)
    except FrmError:
        return _absent()
    return JSONResponse({"location": location}, headers=CACHE)
