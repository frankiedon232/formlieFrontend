"""Navigation counts (mock: routes/navigation.ts): cheap counters and short lists for the sidebar.

Each area fills its part as it is built: people and organisation data (B3), forms and folders (B5), templates,
themes and page designs (B6), responses (B8); data sources and response storage (B9). Until then those count
nothing.
"""

from __future__ import annotations

from collections import Counter
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import func, select

from app.core.db.session import db_session
from app.core.responses import ok
from app.core.security.limits import rate_limit
from app.modules.auth.sessions import Principal, require_auth
from app.modules.dashboard.catalogues import (
    DATASOURCE_STATUSES, SYSTEM_PAGE_COUNT, SYSTEM_TEMPLATES, SYSTEM_THEME_COUNT, TEMPLATE_CATEGORY_KEYS,
)
from app.modules.org.models import OrgUnit
from app.modules.users.models import USER_STATUSES, User

router = APIRouter(tags=["navigation"])


def _template_categories(used: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    """Formalie's categories, most used first (forms made from their templates), then the largest."""
    sizes = Counter(t["category"] for t in SYSTEM_TEMPLATES)
    forms: Counter[str] = Counter()
    for template in SYSTEM_TEMPLATES:
        forms[template["category"]] += (used.get(template["key"]) or {}).get("forms", 0)
    items = [{"key": key, "count": sizes[key], "forms": forms[key]} for key in TEMPLATE_CATEGORY_KEYS if sizes[key] > 0]
    return [{"key": i["key"], "count": i["count"]} for i in sorted(items, key=lambda i: (-i["forms"], -i["count"]))]


async def _responses(principal: Principal) -> dict[str, int]:
    """Responses by review status, of the forms whose responses this person may see."""
    from app.modules.forms import access
    from app.modules.forms.access import viewer_for
    from app.modules.forms.service import forms_of
    from app.modules.responses.models import Response

    async with db_session("read", tenant_id=principal.tenant.id, organisation_id=principal.tenant.organisation_id,
                          user_id=principal.user.id) as db:
        viewer = await viewer_for(db, principal)
        forms = [f.id for f in await forms_of(db, principal.tenant.id)
                 if f.deleted_at is None and access.responses_allowed(f, viewer, "view")]
        by_status = dict((await db.execute(select(Response.status, func.count()).where(
            Response.tenant_id == principal.tenant.id, Response.form_id.in_(forms), Response.deleted_at.is_(None))
            .group_by(Response.status))).all()) if forms else {}
    counts = {s: by_status.get(s, 0) for s in ("new", "reviewed", "approved", "rejected")}
    return {"all": sum(counts.values()), **counts}


async def _library(principal: Principal) -> dict[str, Any]:
    """The workspace's own templates, themes and page designs next to Formalie's."""
    from app.modules.design.models import PageDesign, Theme
    from app.modules.templates.models import WorkspaceTemplate
    from app.modules.templates.service import usage

    tenant_id = principal.tenant.id
    async with db_session("read", tenant_id=tenant_id, organisation_id=principal.tenant.organisation_id,
                          user_id=principal.user.id) as db:
        used = await usage(db, tenant_id)
        mine = (await db.execute(select(func.count()).select_from(WorkspaceTemplate).where(
            WorkspaceTemplate.tenant_id == tenant_id, WorkspaceTemplate.deleted_at.is_(None)))).scalar_one()
        sources: dict[Any, dict[str, int]] = {}
        for model, system in ((Theme, SYSTEM_THEME_COUNT), (PageDesign, SYSTEM_PAGE_COUNT)):
            by = dict((await db.execute(select(model.source, func.count()).where(
                model.tenant_id == tenant_id, model.deleted_at.is_(None)).group_by(model.source))).all())
            sources[model] = {"total": sum(by.values()) + system, "system": system, "saved": by.get("saved", 0),
                              "created": by.get("created", 0)}
    return {"templates": {"total": len(SYSTEM_TEMPLATES), "mine": mine, "categories": _template_categories(used)},
            "themes": sources[Theme], "pages": sources[PageDesign]}


async def _forms(principal: Principal) -> tuple[dict[str, int], list[dict[str, Any]]]:
    """Forms this person may see by status (`all` leaves archived ones out, like the list), and their folders."""
    from app.modules.forms import access
    from app.modules.forms.access import viewer_for
    from app.modules.forms.service import forms_of

    async with db_session("read", tenant_id=principal.tenant.id, organisation_id=principal.tenant.organisation_id,
                          user_id=principal.user.id) as db:
        viewer = await viewer_for(db, principal)
        seen = [f for f in await forms_of(db, principal.tenant.id) if access.can_see(f, viewer)]
    live = [f for f in seen if f.deleted_at is None]
    counts = {"all": sum(1 for f in live if f.status != "archived"),
              **{s: sum(1 for f in live if f.status == s) for s in ("draft", "published", "closed", "archived")},
              "trash": len(seen) - len(live)}
    folders = sorted(({"id": str(folder.id), "name": folder.name, "color": folder.color,
                       "count": sum(1 for f in live if f.folder_id == folder.id and f.status != "archived")}
                      for folder in viewer.folders.values() if access.folder_visible(folder, viewer)),
                     key=lambda item: item["name"].casefold())
    return counts, folders


@router.get("/navigation/counts", dependencies=[rate_limit("navigation-counts", per_minute=240)])
async def navigation_counts(principal: Principal = Depends(require_auth)) -> Any:
    tenant_id = principal.tenant.id
    people = {"total": 0, "active": 0, "invited": 0, "pending": 0, "not_activated": 0, "disabled": 0,
              "departments": 0, "job_titles": 0}
    if principal.can("people.view"):
        async with db_session("read", tenant_id=tenant_id, organisation_id=principal.tenant.organisation_id,
                              user_id=principal.user.id) as db:
            by_status = dict((await db.execute(select(User.status, func.count()).where(
                User.tenant_id == tenant_id, User.deleted_at.is_(None)).group_by(User.status))).all())
            by_kind = dict((await db.execute(select(OrgUnit.kind, func.count()).where(
                OrgUnit.tenant_id == tenant_id, OrgUnit.deleted_at.is_(None), OrgUnit.archived_at.is_(None))
                .group_by(OrgUnit.kind))).all())
        people = {"total": sum(by_status.values()), **{s: by_status.get(s, 0) for s in USER_STATUSES},
                  "departments": by_kind.get("departments", 0), "job_titles": by_kind.get("job_titles", 0)}
    forms_part, folders = await _forms(principal)
    library = await _library(principal)
    return ok({
        "forms": forms_part,
        "responses": await _responses(principal),
        **library,
        "folders": folders,
        "destinations": {"total": 0, "failing": 0},
        "people": people,
        "datasources": {"total": 0, **{status: 0 for status in DATASOURCE_STATUSES}},
    })
