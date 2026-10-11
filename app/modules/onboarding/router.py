"""Onboarding (mock: routes/onboarding.ts): GET / PATCH /onboarding, POST /onboarding/finish.

One state per workspace, kept with its settings (section `onboarding`). A workspace made by sign-up starts at the
first step; one without that row (the seeded ones, and any from before onboarding was built) counts as set up.
Company, branding and localisation are the workspace settings themselves: onboarding shows and saves them there.
Every saved step is in the audit trail with before / after values (`metadata.source: onboarding`).
The team step records the invitations (`users.invited`), as the mock does; sending them is People (B4).
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Request
from sqlalchemy import func, select

from app.core.db.session import db_session
from app.core.errors import FrmError
from app.core.responses import ok
from app.core.security.limits import rate_limit
from app.modules.audit.service import Actor, record
from app.modules.auth.sessions import Principal, require_admin
from app.modules.onboarding import schemas
from app.modules.onboarding.state import SECTION, set_up_state
from app.modules.settings.catalogues import ONBOARDING_STEPS
from app.modules.settings.service import get_section, save_section
from app.modules.tenants.models import Organisation
from app.modules.uploads.service import completed_url
from app.modules.users.models import User

router = APIRouter(tags=["onboarding"])

def _scope(principal: Principal) -> dict[str, Any]:
    return {"tenant_id": principal.tenant.id, "organisation_id": principal.tenant.organisation_id,
            "user_id": principal.user.id}


async def _state(db: Any, tenant_id: Any) -> tuple[dict[str, Any], dict[str, Any]]:
    """(stored state, the Onboarding answer with company, branding and localisation from the settings)."""
    stored = await get_section(db, tenant_id, SECTION) or set_up_state()
    company = await get_section(db, tenant_id, "company")
    branding = await get_section(db, tenant_id, "branding")
    localisation = {k: v for k, v in (await get_section(db, tenant_id, "localisation")).items() if k != "form_languages"}
    view = {
        "status": stored["status"], "current_step": stored["current_step"], "steps": stored["steps"],
        "company": {"name": company["display_name"], "industry": company["industry"], "size": company["size"],
                    "country": company["address"]["country"], "website": company["website"]},
        "branding": {"logo_url": branding["logo_url"], "brand_color": branding["brand_color"]},
        "localisation": localisation,
        "invites": stored["invites"], "first_form": stored["first_form"],
    }
    return stored, view


def _diff(before: dict[str, Any], after: dict[str, Any], fields: list[str]) -> list[dict[str, Any]]:
    return [{"field": f, "before": before.get(f), "after": after.get(f)} for f in fields if before.get(f) != after.get(f)]


@router.get("/onboarding", dependencies=[rate_limit("onboarding-get", per_minute=60)])
async def get_onboarding(principal: Principal = Depends(require_admin)) -> Any:
    async with db_session("read", **_scope(principal)) as db:
        return ok((await _state(db, principal.tenant.id))[1])


@router.patch("/onboarding", dependencies=[rate_limit("onboarding-patch", per_minute=30)])
async def patch_onboarding(request: Request, principal: Principal = Depends(require_admin)) -> Any:
    tenant, user = principal.tenant, principal.user
    body = schemas.patch.parse(await request.json())
    step, actor = body["step"], Actor.user(user)
    by = {"tenant_id": tenant.id, "organisation_id": tenant.organisation_id}

    async with db_session("write", **_scope(principal)) as db:
        stored, view = await _state(db, tenant.id)

        async def save(section: str, value: dict[str, Any]) -> None:
            await save_section(db, tenant.id, tenant.organisation_id, section, value, user.id)

        if body["action"] == "save":
            data = schemas.SCHEMAS[step].parse(body.get("data"))
            if step == "company":
                changes = _diff(view["company"], data, ["name", "industry", "size", "country", "website"])
                saved = await get_section(db, tenant.id, "company")
                await save("company", {**saved, "display_name": data["name"], "legal_name": saved["legal_name"] or data["name"],
                                       "industry": data["industry"], "size": data["size"], "website": data["website"],
                                       "address": {**saved["address"], "country": data["country"]}})
                organisation = await db.get(Organisation, tenant.organisation_id)
                if organisation is not None:
                    organisation.name = data["name"]
                if changes:
                    await record(db, **by, action="workspace.updated", actor=actor, changes=changes,
                                 resource={"type": "workspace", "id": str(tenant.id), "name": data["name"]},
                                 metadata={"source": "onboarding"})
            elif step == "branding":
                logo_url = await completed_url(db, tenant.id, data["logo_upload_id"]) if data["logo_upload_id"] else None
                if data["logo_upload_id"] and not logo_url:
                    raise FrmError("FRM-GEN-1002", [{"field": "logo", "message": "Upload the logo again."}])
                before = view["branding"]
                after = {"logo_url": logo_url or before["logo_url"], "brand_color": data["brand_color"]}
                changes = ([{"field": "logo", "before": "set" if before["logo_url"] else None, "after": "uploaded"}]
                           if logo_url else []) + _diff({"brand_colour": before["brand_color"]},
                                                       {"brand_colour": after["brand_color"]}, ["brand_colour"])
                await save("branding", {**await get_section(db, tenant.id, "branding"), **after})
                if changes:
                    await record(db, **by, action="settings.updated", actor=actor, changes=changes,
                                 resource={"type": "setting", "id": None, "name": "Branding"},
                                 metadata={"source": "onboarding"})
            elif step == "localisation":
                changes = _diff(view["localisation"], data, ["language", "timezone", "currency", "date_format",
                                                              "number_format", "week_start"])
                await save("localisation", {**await get_section(db, tenant.id, "localisation"), **data})
                if changes:
                    await record(db, **by, action="settings.updated", actor=actor, changes=changes,
                                 resource={"type": "setting", "id": None, "name": "Localisation"},
                                 metadata={"source": "onboarding"})
            elif step == "team":
                invites = data["invites"]
                emails = [i["email"].lower() for i in invites]
                members = set((await db.execute(select(func.lower(User.email)).where(
                    User.tenant_id == tenant.id, User.deleted_at.is_(None), func.lower(User.email).in_(emails)))).scalars())
                already = next((i for i in invites if i["email"].lower() in members), None)
                if already:
                    raise FrmError("FRM-GEN-1002", [{"field": "invites",
                                                     "message": f"{already['email']} is already in this workspace."}])
                known = {i["email"].lower() for i in stored["invites"]}
                for invite in (i for i in invites if i["email"].lower() not in known):
                    await record(db, **by, action="users.invited", actor=actor,
                                 resource={"type": "user", "id": None, "name": invite["email"]},
                                 metadata={"role": invite["role"], "source": "onboarding"})
                stored["invites"] = invites
            else:
                stored["first_form"] = data
            stored["steps"][step] = "done"
        elif stored["steps"][step] != "done":
            stored["steps"][step] = "skipped"

        index = ONBOARDING_STEPS.index(step)
        stored["current_step"] = ONBOARDING_STEPS[min(index + 1, len(ONBOARDING_STEPS) - 1)]
        if stored["status"] == "not_started":
            stored["status"] = "in_progress"
        await save(SECTION, stored)
        return ok((await _state(db, tenant.id))[1])


@router.post("/onboarding/finish", dependencies=[rate_limit("onboarding-finish", per_minute=10)])
async def finish_onboarding(principal: Principal = Depends(require_admin)) -> Any:
    tenant = principal.tenant
    async with db_session("write", **_scope(principal)) as db:
        stored, _ = await _state(db, tenant.id)
        if stored["status"] != "completed":
            stored["status"] = "completed"
            await save_section(db, tenant.id, tenant.organisation_id, SECTION, stored, principal.user.id)
            steps = list(stored["steps"].values())
            await record(db, tenant_id=tenant.id, organisation_id=tenant.organisation_id,
                         action="workspace.setup_completed", actor=Actor.user(principal.user),
                         resource={"type": "workspace", "id": str(tenant.id), "name": tenant.name},
                         metadata={"done": str(steps.count("done")), "skipped": str(steps.count("skipped"))})
        return ok((await _state(db, tenant.id))[1])
