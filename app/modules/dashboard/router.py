"""Navigation counts (mock: routes/navigation.ts): cheap counters and short lists for the sidebar.

Each area fills its part as it is built: people and organisation data (B3), forms and folders (B5); responses (B8),
templates, themes and page designs (B6), data sources and response storage (B9). Until then those count nothing of
the workspace's own, and Formalie's own lists by their size.
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


def _template_categories() -> list[dict[str, Any]]:
    """Formalie's categories, most used first (forms made from them: none yet), then the largest."""
    sizes = Counter(t["category"] for t in SYSTEM_TEMPLATES)
    items = [{"key": key, "count": sizes[key]} for key in TEMPLATE_CATEGORY_KEYS if sizes[key] > 0]
    return sorted(items, key=lambda item: -item["count"])


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
    return ok({
        "forms": forms_part,
        "responses": {"all": 0, "new": 0, "reviewed": 0, "approved": 0, "rejected": 0},
        "templates": {"total": len(SYSTEM_TEMPLATES), "mine": 0, "categories": _template_categories()},
        "themes": {"total": SYSTEM_THEME_COUNT, "system": SYSTEM_THEME_COUNT, "saved": 0, "created": 0},
        "pages": {"total": SYSTEM_PAGE_COUNT, "system": SYSTEM_PAGE_COUNT, "saved": 0, "created": 0},
        "folders": folders,
        "destinations": {"total": 0, "failing": 0},
        "people": people,
        "datasources": {"total": 0, **{status: 0 for status in DATASOURCE_STATUSES}},
    })
