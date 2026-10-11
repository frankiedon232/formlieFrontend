"""The form builder (mock: routes/formDraft.ts, API-CONTRACT → Forms):

    GET  /forms/{id}/builder                     everything the builder needs in one call
    PUT  /forms/{id}/draft                       autosave (row_version)
    POST /forms/{id}/publish                     the publish checks, then a new immutable version
    POST /forms/{id}/discard                     back to the published version
    GET  /forms/{id}/preview                     the draft and the live version, read only
    GET  /forms/{id}/versions(/{vid})            published versions
    POST /forms/{id}/versions/{vid}/restore      a version copied into the draft

Editing a published form changes only the draft; the published version stays live. Large lists' options are
filled in on save once option lists exist (B6).
"""

from __future__ import annotations

import copy
import json
import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select

from app.core import zod as z
from app.core.cache.redis import get_redis
from app.core.db.session import db_session
from app.core.errors import FrmError
from app.core.responses import ok
from app.core.security.limits import rate_limit
from app.modules.auth.sessions import Principal, require_auth
from app.modules.forms import access, service
from app.modules.forms.access import Viewer, viewer_for
from app.modules.forms.catalogues import FIELD_TYPES
from app.modules.forms.models import Form, FormVersion
from app.modules.forms.schema import all_fields, blank_schema, count_fields, form_schema_v1
from app.modules.forms.service import Names, iso

router = APIRouter(tags=["builder"])

DRAFT_AUDIT_SECONDS = 600  # draft saves are frequent: one audit entry per form and person per 10 minutes

draft_schema = z.obj(row_version=z.number().int(), schema=form_schema_v1)
publish_schema = z.obj(row_version=z.number().int(), change_summary=z.string().trim().max(500).nullable().optional())


def is_input(field_type: str) -> bool:
    return bool(FIELD_TYPES.get(field_type, {}).get("input"))


def has_options(field_type: str) -> bool:
    return bool(FIELD_TYPES.get(field_type, {}).get("options"))


def cannot_be_required(field: dict[str, Any]) -> bool:
    """Locked, restricted or hidden fields can't be required: someone could never submit the form."""
    locked = bool(field.get("readonly")) or bool(field.get("disabled"))
    restricted = bool(field.get("audience")) and field["audience"].get("mode") != "everyone"
    return locked or restricted or field.get("type") == "hidden"


def publish_issues(schema: dict[str, Any]) -> list[dict[str, Any]]:
    """publishIssues(): everything that blocks publishing (an empty list = ready)."""
    fields = all_fields(schema)
    issues: list[dict[str, Any]] = []
    if not any(is_input(f["type"]) for f in fields):
        issues.append({"code": "no_inputs", "field_id": None})
    seen: dict[str, int] = {}
    for f in fields:
        seen[f["key"]] = seen.get(f["key"], 0) + 1
    for f in fields:
        if is_input(f["type"]) and not f.get("label", "").strip():
            issues.append({"code": "empty_label", "field_id": f["id"]})
        if seen.get(f["key"], 0) > 1:
            issues.append({"code": "duplicate_key", "field_id": f["id"]})
        if has_options(f["type"]) and not f.get("option_set_id") and not (f.get("options") or []):
            issues.append({"code": "no_options", "field_id": f["id"]})
        if f.get("required") and cannot_be_required(f):
            issues.append({"code": "locked_required", "field_id": f["id"]})
    return issues


def _scope(principal: Principal) -> dict[str, Any]:
    return {"tenant_id": principal.tenant.id, "organisation_id": principal.tenant.organisation_id,
            "user_id": principal.user.id}


def _version_view(version: FormVersion) -> dict[str, Any]:
    return {"id": str(version.id), "number": version.number, "published_at": iso(version.published_at),
            "published_by": {"id": str(version.published_by) if version.published_by else None,
                             "name": version.published_by_name or ""},
            "change_summary": version.change_summary, "fields_count": version.fields_count}


async def _versions(db: Any, form: Form) -> list[FormVersion]:
    """Newest first."""
    return list((await db.execute(select(FormVersion).where(FormVersion.tenant_id == form.tenant_id,
                                                            FormVersion.form_id == form.id)
                                  .order_by(FormVersion.number.desc()))).scalars())


async def _live(db: Any, form: Form) -> dict[str, Any] | None:
    """What respondents see (null until the first publish)."""
    version = await db.get(FormVersion, form.published_version_id) if form.published_version_id else None
    return version.schema if version else None


def _draft(form: Form) -> dict[str, Any]:
    if form.draft_schema is None:
        form.draft_schema = blank_schema()
    return form.draft_schema


async def _find(db: Any, viewer: Viewer, form_id: str, action: str) -> Form:
    """A form not in Trash, and the action wanted on it."""
    return await service.find_form(db, viewer, form_id, action=action)


def published_keys(versions: list[FormVersion], live: dict[str, Any] | None, form: Form, schema: dict[str, Any]) -> list[str]:
    """Every question key any published version used: they stay fixed (endpoints, storage, exports and webhooks
    know them) and are never given to another question."""
    schemas = [v.schema for v in versions] + ([live] if live else [])
    if not schemas and form.status != "draft":
        schemas.append(schema)
    return list(dict.fromkeys(f["key"] for s in schemas for f in all_fields(s)))


@router.get("/forms/{form_id}/builder", dependencies=[rate_limit("builder-get", per_minute=120)])
async def get_builder(form_id: str, principal: Principal = Depends(require_auth)) -> Any:
    async with db_session("write", **_scope(principal)) as db:
        viewer = await viewer_for(db, principal)
        form = await _find(db, viewer, form_id, "view")
        # The editor opens for building, share settings or versions; each tab follows what is allowed
        if not any(access.allows(form, viewer, a) for a in ("edit", "share_view", "versions")):
            raise FrmError("FRM-PERM-1001")
        schema = _draft(form)
        versions, live = await _versions(db, form), await _live(db, form)
        return ok({
            "form": service.summary(form, viewer, await Names().load(db, principal.tenant.id)),
            "schema": schema,
            "published_version": versions[0].number if versions else None,
            "published_keys": published_keys(versions, live, form, schema),
            "live_fields": [{"key": f["key"], "label": f.get("label") or "", "required": bool(f.get("required")),
                             "type": f["type"]} for f in all_fields(live) if f.get("key")] if live else [],
        })


@router.put("/forms/{form_id}/draft", dependencies=[rate_limit("builder-draft", per_minute=240)])
async def save_draft(form_id: str, request: Request, principal: Principal = Depends(require_auth)) -> Any:
    async with db_session("write", **_scope(principal)) as db:
        viewer = await viewer_for(db, principal)
        form = await _find(db, viewer, form_id, "edit")
        body = draft_schema.parse(await request.json())
        service.check_version(form, body["row_version"])
        form.draft_schema = body["schema"]
        form.has_unpublished_changes = form.status != "draft"
        service.touch(form, viewer)
        key = f"fm:v1:forms:draft-audit:{form.id}:{viewer.user_id}"
        if await get_redis().set(key, "1", ex=DRAFT_AUDIT_SECONDS, nx=True):
            await service.audit(db, viewer, "forms.updated", form, metadata={
                "change": "draft_edited", "fields": str(len(all_fields(body["schema"])))})
        await db.flush()
        return ok({"row_version": form.row_version, "updated_at": iso(form.updated_at),
                   "has_unpublished_changes": form.has_unpublished_changes})


@router.post("/forms/{form_id}/publish", dependencies=[rate_limit("builder-publish", per_minute=30)])
async def publish_form(form_id: str, request: Request, principal: Principal = Depends(require_auth)) -> Any:
    async with db_session("write", **_scope(principal)) as db:
        viewer = await viewer_for(db, principal)
        form = await _find(db, viewer, form_id, "publish")
        body = publish_schema.parse(await request.json())
        service.check_version(form, body["row_version"])
        if form.status not in ("draft", "published"):
            raise FrmError("FRM-FORM-1007")
        schema = _draft(form)
        issues = publish_issues(schema)
        if issues:
            raise FrmError("FRM-FORM-1004", [{"field": i["field_id"] or "form", "message": i["code"]} for i in issues])
        versions = await _versions(db, form)
        now = datetime.now(UTC)
        version = FormVersion(tenant_id=form.tenant_id, organisation_id=form.organisation_id, form_id=form.id,
                              number=(versions[0].number if versions else 0) + 1, schema=copy.deepcopy(schema),
                              published_by=viewer.user_id, published_by_name=service.name_of(principal.user),
                              published_at=now, change_summary=body.get("change_summary") or None,
                              fields_count=count_fields(schema))
        db.add(version)
        await db.flush()
        before = form.status
        form.published_version_id, form.status, form.has_unpublished_changes = version.id, "published", False
        form.published_at = form.published_at or now
        service.touch(form, viewer)
        await service.audit(db, viewer, "forms.published", form,
                            [{"field": "status", "before": before, "after": "published"}] if before != "published" else [],
                            {"version": str(version.number),
                             **({"summary": version.change_summary} if version.change_summary else {})})
        await db.flush()
        return ok({"form": service.summary(form, viewer, await Names().load(db, principal.tenant.id)),
                   "version": _version_view(version)})


@router.post("/forms/{form_id}/discard", dependencies=[rate_limit("builder-discard", per_minute=30)])
async def discard_draft(form_id: str, principal: Principal = Depends(require_auth)) -> Any:
    async with db_session("write", **_scope(principal)) as db:
        viewer = await viewer_for(db, principal)
        form = await _find(db, viewer, form_id, "edit")
        live = await _live(db, form)
        if live is None:
            raise FrmError("FRM-FORM-1007")
        form.draft_schema, form.has_unpublished_changes = copy.deepcopy(live), False
        service.touch(form, viewer)
        await service.audit(db, viewer, "forms.updated", form, metadata={"change": "draft_discarded"})
        await db.flush()
        return ok({"form": service.summary(form, viewer, await Names().load(db, principal.tenant.id)),
                   "schema": form.draft_schema})


@router.get("/forms/{form_id}/preview", dependencies=[rate_limit("builder-preview", per_minute=120)])
async def preview_form(form_id: str, principal: Principal = Depends(require_auth)) -> Any:
    """The form as respondents will see it (draft and live), read only: "Can view" people get this."""
    async with db_session("write", **_scope(principal)) as db:
        viewer = await viewer_for(db, principal)
        form = await _find(db, viewer, form_id, "preview")
        draft = _draft(form)
        versions = await _versions(db, form)
        return ok({"form": service.summary(form, viewer, await Names().load(db, principal.tenant.id)),
                   "draft": draft, "live": None if form.status == "draft" else await _live(db, form),
                   "published_version": versions[0].number if versions else None})


@router.get("/forms/{form_id}/versions", dependencies=[rate_limit("builder-versions", per_minute=120)])
async def list_versions(form_id: str, principal: Principal = Depends(require_auth)) -> Any:
    async with db_session("read", **_scope(principal)) as db:
        viewer = await viewer_for(db, principal)
        form = await _find(db, viewer, form_id, "versions")
        return ok([_version_view(v) for v in await _versions(db, form)])


async def _version(db: Any, form: Form, version_id: str) -> FormVersion:
    try:
        wanted = uuid.UUID(version_id)
    except ValueError:
        raise FrmError("FRM-GEN-1004") from None
    version = await db.get(FormVersion, wanted)
    if version is None or version.form_id != form.id:
        raise FrmError("FRM-GEN-1004")
    return version


@router.get("/forms/{form_id}/versions/{version_id}", dependencies=[rate_limit("builder-versions", per_minute=120)])
async def get_version(form_id: str, version_id: str, principal: Principal = Depends(require_auth)) -> Any:
    async with db_session("read", **_scope(principal)) as db:
        viewer = await viewer_for(db, principal)
        form = await _find(db, viewer, form_id, "versions")
        version = await _version(db, form, version_id)
        return ok({**_version_view(version), "schema": version.schema})


@router.post("/forms/{form_id}/versions/{version_id}/restore", dependencies=[rate_limit("builder-restore", per_minute=30)])
async def restore_version(form_id: str, version_id: str, principal: Principal = Depends(require_auth)) -> Any:
    """A published version copied into the draft."""
    async with db_session("write", **_scope(principal)) as db:
        viewer = await viewer_for(db, principal)
        form = await _find(db, viewer, form_id, "versions")
        version = await _version(db, form, version_id)
        live = await _live(db, form)
        form.draft_schema = copy.deepcopy(version.schema)
        form.has_unpublished_changes = live is not None and json.dumps(version.schema, sort_keys=True) != json.dumps(
            live, sort_keys=True)
        service.touch(form, viewer)
        await service.audit(db, viewer, "forms.updated", form,
                            metadata={"change": "version_restored", "version": str(version.number)})
        await db.flush()
        return ok({"form": service.summary(form, viewer, await Names().load(db, principal.tenant.id)),
                   "schema": form.draft_schema})
