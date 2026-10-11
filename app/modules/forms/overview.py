"""Overview pages (mock: routes/formOverview.ts, folders.ts, directory.ts).

    GET /forms/{id}/overview     statistics, 30-day trend, structure, latest versions, template, design, first questions
    GET /folders/overview        every folder with its numbers (q, sort, pages)
    GET /folders/{id}            one folder with its numbers
    GET /directory               departments, job titles, roles and people (field access, people pickers, logic)

Numbers come from responses, which arrive in B8 (until then: none, so views, starts and the trend are zero).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select

from app.core.db.session import db_session
from app.core.errors import FrmError
from app.core.responses import PageParams, ok
from app.core.security.limits import rate_limit
from app.modules.auth.sessions import Principal, require_auth
from app.modules.forms import access, service
from app.modules.forms.access import Viewer, viewer_for
from app.modules.forms.builder import _draft, _version_view, _versions, is_input
from app.modules.forms.models import Folder, Form
from app.modules.forms.router import _natural
from app.modules.forms.schema import all_fields
from app.modules.forms.service import Names, iso
from app.modules.org.models import OrgUnit
from app.modules.org.service import people_of
from app.modules.rbac.service import role_key, roles_of

router = APIRouter(tags=["overview"])


def _scope(principal: Principal) -> dict[str, Any]:
    return {"tenant_id": principal.tenant.id, "organisation_id": principal.tenant.organisation_id,
            "user_id": principal.user.id}


def _asked(field: dict[str, Any]) -> bool:
    return is_input(field["type"]) and field["type"] not in ("hidden", "calculated")


def schema_stats(schema: dict[str, Any]) -> dict[str, int]:
    """schemaStats(): pages, questions (no hidden or calculated ones), rules, calculations."""
    fields = all_fields(schema)
    return {"pages": len(schema["pages"]), "fields": sum(1 for f in fields if _asked(f)),
            "logic": len(schema.get("logic") or []), "calculations": sum(1 for f in fields if f["type"] == "calculated")}


def preview_labels(schema: dict[str, Any], count: int = 3) -> list[str]:
    """previewLabels(): the first questions."""
    return [f.get("label", "") for f in all_fields(schema) if _asked(f)][:count]


def _days(start: datetime) -> list[dict[str, Any]]:
    return [{"date": (start + timedelta(days=i)).strftime("%Y-%m-%d"), "count": 0} for i in range(30)]


@router.get("/forms/{form_id}/overview", dependencies=[rate_limit("form-overview", per_minute=120)])
async def form_overview(form_id: str, principal: Principal = Depends(require_auth)) -> Any:
    async with db_session("write", **_scope(principal)) as db:
        viewer = await viewer_for(db, principal)
        try:
            form = await db.get(Form, uuid.UUID(form_id))
        except ValueError:
            form = None
        if form is None or form.tenant_id != principal.tenant.id or form.purged_at is not None:
            raise FrmError("FRM-GEN-1004")
        access.require_level(form, viewer, "responses")
        schema = _draft(form)
        versions = await _versions(db, form)
        template = None
        if form.template_key:
            from app.modules.templates import catalogue
            from app.modules.templates.service import find_own

            found = catalogue.system_template(form.template_key)
            own = None if found else await find_own(db, principal.tenant.id, form.template_key)
            name = found["name"] if found else own.name if own else None
            template = {"key": form.template_key, "name": name} if name else None
    today = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    return ok({
        "stats": {"views": 0, "starts": 0, "responses": 0, "completion_rate": 0, "avg_seconds": None,
                  "last_response_at": None},
        "daily": _days(today - timedelta(days=29)),
        "structure": schema_stats(schema),
        "versions": [{k: v for k, v in _version_view(version).items() if k != "change_summary"} for version in versions[:3]],
        "template": template,
        "theme": schema.get("theme") or {},
        "preview": preview_labels(schema),
    })


def _folder_row(folder: Folder, forms: list[Form], viewer: Viewer, names: Names) -> dict[str, Any]:
    """FolderRow: its numbers over the forms this person can see (responses: B8)."""
    shown = service.folder_view(folder, viewer, names)
    counts = {"draft": 0, "published": 0, "closed": 0, "archived": 0}
    owners: dict[uuid.UUID, dict[str, str]] = {}
    last: datetime | None = None
    for form in forms:
        counts[form.status] += 1
        owners.setdefault(form.owner_id, names.ref(form.owner_id))  # type: ignore[arg-type]
        last = max(last, form.updated_at) if last else form.updated_at
    published = [f for f in forms if f.status == "published"]
    today = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    return {
        "id": str(folder.id), "name": folder.name, "color": folder.color,
        "forms_count": sum(1 for f in forms if f.status != "archived"), "status_counts": counts,
        "responses_count": 0, "responses_30d": 0, "previous_30d": 0, "daily": _days(today - timedelta(days=29)),
        "completion_rate": round(sum(f.completion_rate for f in published) / len(published)) if published else None,
        "last_activity_at": iso(last), "owners": list(owners.values())[:5],
        "created_by": shown["created_by"], "access": shown["access"], "can": shown["can"],
    }


async def _rows(db: Any, principal: Principal) -> tuple[Viewer, list[dict[str, Any]]]:
    viewer = await viewer_for(db, principal)
    names = await Names().load(db, principal.tenant.id)
    forms = [f for f in await service.forms_of(db, principal.tenant.id) if f.deleted_at is None and access.can_see(f, viewer)]
    rows = [_folder_row(folder, [f for f in forms if f.folder_id == folder.id], viewer, names)
            for folder in viewer.folders.values() if access.folder_visible(folder, viewer)]
    return viewer, rows


@router.get("/folders/overview", dependencies=[rate_limit("folders-overview", per_minute=120)])
async def folder_overview(request: Request, principal: Principal = Depends(require_auth)) -> Any:
    query = dict(request.query_params)
    async with db_session("read", **_scope(principal)) as db:
        _, rows = await _rows(db, principal)
    q = (query.get("q") or "").strip().lower()
    if q:
        rows = [r for r in rows if q in r["name"].lower()]
    sort = query.get("sort") or "name"
    key = sort.lstrip("-")
    rows.sort(key=lambda r: _natural(r.get(key)), reverse=sort.startswith("-"))
    params = PageParams.from_query(query.get("page"), query.get("page_size"))
    return ok(rows[params.offset:params.offset + params.page_size], params.meta(len(rows)))


@router.get("/folders/{folder_id}", dependencies=[rate_limit("folders-get", per_minute=120)])
async def get_folder(folder_id: str, principal: Principal = Depends(require_auth)) -> Any:
    async with db_session("read", **_scope(principal)) as db:
        _, rows = await _rows(db, principal)
    row = next((r for r in rows if r["id"] == folder_id), None)
    if row is None:
        raise FrmError("FRM-GEN-1004")
    return ok(row)


@router.get("/directory", dependencies=[rate_limit("directory", per_minute=120)])
async def get_directory(principal: Principal = Depends(require_auth)) -> Any:
    """Any member: archived entries are flagged, so forms still using them can name them."""
    tenant_id = principal.tenant.id
    async with db_session("read", **_scope(principal)) as db:
        units = (await db.execute(select(OrgUnit).where(OrgUnit.tenant_id == tenant_id, OrgUnit.deleted_at.is_(None))
                                  .order_by(OrgUnit.created_at, OrgUnit.id))).scalars().all()
        roles = await roles_of(db, tenant_id)
        people = await people_of(db, tenant_id)

    def listed(kind: str) -> list[dict[str, Any]]:
        return [{"id": str(u.id), "name": u.name, **({"detail": u.code} if u.code else {}),
                 **({"archived": True} if u.archived_at else {})} for u in units if u.kind == kind]
    return ok({"departments": listed("departments"), "job_titles": listed("job_titles"),
               "roles": [{"id": role_key(r), "name": r.name} for r in roles],
               "users": [{"id": p["id"], "name": p["name"], "detail": p["email"]} for p in people]})
