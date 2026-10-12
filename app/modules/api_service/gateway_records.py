"""Reading and writing records through the public API (port of the second half of the mock's publicApi.ts `handle`),
once every check in gateway.py has passed. Records are the form's responses as apps see them:
`{ id (reference), submitted_at, status, data }` with the endpoint's returned questions under their API names,
choices as their labels and file ids as references.

- **GET:** one record or a page of them (page, per_page up to the endpoint's page size, `sort=submitted_at` for oldest
  first, a filter per filter question by its API name). Test tokens get made-up records.
- **POST:** only accepted questions (FRM-API-1014), the Formalie-Key replay (24 hours, FRM-API-1020 for another body;
  recognised before the answers are checked again, so a retry with file ids replays), the endpoint's required
  questions and the form's own rules (FRM-RESP-1001), the form's response limit (FRM-FORM-1003), the form's duplicate
  rules as on its web page; stored through the same pipeline as a web response (destinations,
  webhooks, notifications, response emails), channel `api`, audited as the token.
- **PUT:** the answers sent, each checked like an edit; levels of a list that no longer fit are cleared.
- **DELETE:** soft delete, kept in the audit trail.
- **Files:** `POST …/files?field=` one file (multipart, field `file`), checked like the form page and stored at once;
  its id goes in the JSON of a POST or PUT.
Test tokens: everything is checked and answered, nothing is stored (`meta.test`).
"""

from __future__ import annotations

import hashlib
import json
import math
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert
from starlette.requests import Request

from app.core import js
from app.core.security.refs import get_codec
from app.modules.api_service.choices import choice_filter, choice_out
from app.modules.api_service.endpoints import example_record
from app.modules.api_service.gateway import GatewayError, Raced, Work, iso
from app.modules.api_service.models import ApiIdempotency
from app.modules.api_service.tokens import canonical_json
from app.modules.audit.service import Actor, record
from app.modules.forms.answers import max_file_bytes, validate_answer
from app.modules.forms.logic import cascade_closed, fit_answer
from app.modules.forms.models import Form, FormVersion
from app.modules.public import rules
from app.modules.public.service import limit_reached
from app.modules.public.submit import check_submission
from app.modules.responses.models import Response
from app.modules.uploads import service as uploads

FILE_FIELDS = ("file_upload", "image_upload")
REPLAY_HOURS = 24


def encode(value: Any) -> str:
    return get_codec().encode_id(str(value))


def decode(ref: str | None) -> uuid.UUID | None:
    if not ref:
        return None
    found = get_codec().decode_id(ref)
    try:
        return uuid.UUID(str(found)) if found else None
    except ValueError:
        return None


def actor_of(work: Work) -> Actor:
    token = work.token
    return Actor("api_key", token.id if isinstance(token.id, uuid.UUID) else None, f"API: {token.name}", None)


def is_file_field(kind: str | None) -> bool:
    return kind in FILE_FIELDS


def record_of(work: Work, response: Response) -> dict[str, Any]:
    """A response as the API returns it (mock: record)."""
    data = response.data or {}
    types = {f["key"]: f.get("type") for f in work.choices}

    def value(key: str) -> Any:
        definition = work.label_defs.get(key)
        answer = choice_out(definition, data.get(key)) if definition else data.get(key)
        if not is_file_field(types.get(key)) or not isinstance(answer, list):
            return answer
        return [{**f, "id": encode(f["id"])} if isinstance(f, dict) and "id" in f else f for f in answer]
    return {"id": encode(response.id), "submitted_at": iso(response.submitted_at), "status": response.status,
            "data": {f["name"]: value(f["key"]) for f in work.choices if f.get("returned")}}


async def responses_of(work: Work) -> list[Response]:
    """The form's responses that still exist, newest first."""
    return list((await work.db.execute(select(Response).where(
        Response.tenant_id == work.tenant.id, Response.form_id == work.form.id, Response.deleted_at.is_(None))
        .order_by(Response.submitted_at.desc(), Response.id.desc()))).scalars())


async def one_of(work: Work) -> Response | None:
    wanted = decode(work.record_ref)
    if wanted is None:
        return None
    return (await work.db.execute(select(Response).where(
        Response.tenant_id == work.tenant.id, Response.form_id == work.form.id, Response.id == wanted,
        Response.deleted_at.is_(None)))).scalar_one_or_none()


def _number(value: str | None) -> float:
    """Number(value) of a query value, 0 when it is not one (so `|| default` applies, as in the mock)."""
    if value is None:
        return 0.0
    n = js.to_number(value)
    return 0.0 if js.is_nan(n) or n in (float("inf"), float("-inf")) else n


def _plain(n: float) -> int | float:
    return int(n) if float(n).is_integer() else n


# ── Reading ──────────────────────────────────────────────────────────────────────

async def read(work: Work) -> tuple[int, Any]:
    if work.test:
        sample = example_record([{**f, "label": (work.fields.get(f["key"]) or {}).get("label") or f["key"],
                                  "type": (work.fields.get(f["key"]) or {}).get("type") or "short_text", "page": 0,
                                  "form_required": False, "acceptable": True, "filterable": False}
                                 for f in work.choices])
        if work.record_ref is not None:
            return 200, {"data": {**sample, "id": work.record_ref}, "meta": {"test": True}}
        return 200, {"data": [sample], "meta": {"page": 1, "per_page": 1, "total": 1, "test": True}}
    if work.record_ref is not None:
        found = await one_of(work)
        if found is None:
            raise GatewayError("FRM-API-1013")
        return 200, {"data": record_of(work, found)}
    query = work.request.query_params
    filters = [f for f in work.choices if f.get("filter") and len(query.getlist(f["name"])) == 1]
    entries = await responses_of(work)
    if filters:
        def keep(entry: Response) -> bool:
            data = entry.data or {}
            for f in filters:
                value = data.get(f["key"])
                definition = work.fields.get(f["key"])
                sent = query.get(f["name"]) or ""
                wanted = choice_filter(definition, sent) if definition else sent
                if isinstance(value, list):
                    if wanted not in [js.to_string(v) for v in value]:
                        return False
                elif ("" if value is None else js.to_string(value)) != wanted:
                    return False
            return True
        entries = [e for e in entries if keep(e)]
    entries.sort(key=lambda e: e.submitted_at, reverse=query.get("sort") != "submitted_at")
    size = work.endpoint.page_size
    per_page = min(size, max(1, _number(query.get("per_page")) or min(20, size)))
    page = max(1, _number(query.get("page")) or 1)
    start, end = int((page - 1) * per_page), int(page * per_page)
    return 200, {"data": [record_of(work, e) for e in entries[start:end]],
                 "meta": {"page": _plain(page), "per_page": _plain(per_page), "total": len(entries),
                          "total_pages": max(1, math.ceil(len(entries) / per_page))}}


# ── Files ────────────────────────────────────────────────────────────────────────

async def upload(work: Work, too_big: bool) -> tuple[int, Any]:
    """POST …/files?field=: one file, checked like the form page, stored at once (test tokens: checked only)."""
    asked = work.request.query_params.get("field") or ""
    key = work.key_of.get(asked, "")
    definition = work.fields.get(key)
    if definition is None or not is_file_field(definition.get("type")) or not any(
            c["key"] == key and c.get("accept") for c in work.choices):
        raise GatewayError("FRM-API-1014", [{"field": asked or "field", "message": "not_accepted"}])
    if too_big:
        raise GatewayError("FRM-RESP-1001", [{"field": key, "message": "file_size"}])
    part = await _file_part(work)
    if part is None:
        raise GatewayError("FRM-GEN-1001", [{"field": "file", "message": "Send the file as multipart/form-data in a "
                                                                         "field named file."}])
    file_name, content_type, data = part
    props = definition.get("props") or {}
    image = definition["type"] == "image_upload"
    raw_accept = props.get("accept", js.UNDEFINED)
    accept = "" if js.nullish(raw_accept) else js.to_string(raw_accept)
    if image:
        accept = rules.picture_accept(accept)
    name = file_name[:200]
    if not rules.accepts_file(accept, name, content_type) or (image and not rules.looks_like_picture(name, content_type)):
        raise GatewayError("FRM-RESP-1001", [{"field": key, "message": "file_type"}])
    stored = await uploads.store_api_file(
        work.db, tenant_id=work.tenant.id, organisation_id=work.tenant.organisation_id, form_id=work.form.id,
        field_key=key, file_name=name, content_type=content_type, data=data, max_bytes=max_file_bytes(props),
        kind="image" if image else "file", listed=[t for t in rules.parse_accept(accept) if t.startswith(".")],
        check=work.test)
    if isinstance(stored, str):
        raise GatewayError("FRM-RESP-1001", [{"field": key, "message": "file_size" if stored == "size" else "file_type"}])
    answer = uploads.answer_of(stored)
    return 201, {"data": {**answer, "id": encode(uuid.uuid4() if work.test else stored.id)},
                 **({"meta": {"test": True}} if work.test else {})}


async def _file_part(work: Work) -> tuple[str, str, bytes] | None:
    raw = work.call.raw

    async def receive() -> dict[str, Any]:
        return {"type": "http.request", "body": raw, "more_body": False}
    try:
        form = await Request(work.request.scope, receive).form(max_files=5, max_fields=20,
                                                               max_part_size=uploads.MAX_RESPONDENT_BYTES)
    except Exception:  # noqa: BLE001 (not multipart, or broken: answered as "send the file")
        return None
    for name, value in form.multi_items():
        if name == "file" and not isinstance(value, str) and value.filename:
            data = await value.read()
            return value.filename, value.content_type or "application/octet-stream", data
    return None


# ── Writing ──────────────────────────────────────────────────────────────────────

async def write(work: Work) -> tuple[int, Any]:
    """Only accepted questions, then the form's own rules."""
    body = work.body
    accepted = {f["key"] for f in work.choices if f.get("accept")}
    refused = [*work.call.unknown, *[k for k in body if k not in accepted]]
    if refused:
        raise GatewayError("FRM-API-1014", [{"field": k, "message": "not_accepted"} for k in refused])
    if work.call.method == "POST":
        replayed = await _replay(work)
        if replayed is not None:
            return replayed
    # File answers: ids from …/files (or { id }) → the stored files of this form and question, not used by another
    files: list[Any] = []
    for key, value in list(body.items()):
        definition = work.fields.get(key)
        if definition is None or not is_file_field(definition.get("type")) or value is None:
            continue
        refs = [item if isinstance(item, str) else js.to_string(item["id"]) if isinstance(item, dict) and "id" in item
                else "" for item in (value if isinstance(value, list) else [value])]
        answers: list[Any] = []
        for ref in refs:
            found_id = decode(ref)
            if work.test:
                answers.append({"id": str(found_id) if found_id else ref, "name": "file", "size": 0,
                                "type": "application/octet-stream"} if found_id or ref else None)
            else:
                upload_row = await uploads.respondent_file(work.db, work.tenant.id, found_id, work.form.id, key) \
                    if found_id else None
                answers.append(uploads.answer_of(upload_row) if upload_row else None)
                if upload_row:
                    files.append(upload_row)
        if any(a is None for a in answers):
            raise GatewayError("FRM-RESP-1001", [{"field": key, "message": "file"}])
        body[key] = answers
    if work.call.method == "POST":
        return await _create(work, files)
    return await _change(work, files)


async def _create(work: Work, files: list[Any]) -> tuple[int, Any]:
    body, schema, db = work.body, work.schema, work.db
    by_id = {f["id"]: f for f in work.fields.values()}

    def closed(key: str) -> bool:
        fld = work.fields.get(key)
        return fld is not None and cascade_closed(fld, by_id, body)
    # A level of a list with levels with nothing under the choice above is not asked, so not required (F15 M2)
    missing = [f for f in work.choices if f.get("required") and (body.get(f["key"]) is None or body.get(f["key"]) == "")
               and not closed(f["key"])]
    if missing:
        raise GatewayError("FRM-RESP-1001", [{"field": f["key"], "message": "required"} for f in missing])
    issues, answers = check_submission(schema, body)
    if issues:
        raise GatewayError("FRM-RESP-1001", [{"field": i["key"], "message": i["code"]} for i in issues])
    form = work.form
    if not work.test and limit_reached(work.tenant, form):
        raise GatewayError("FRM-FORM-1003")

    moment = datetime.now(UTC)
    key, digest = work.call.call_key or "", work.digest

    # The form's own duplicate rules, exactly as on its web page (owner, 2026-10-06: a new Formalie-Key is no way
    # round them): the same answers twice are refused; with the form's identity email, the same email is refused and
    # one a typo away is saved but flagged "possible duplicate" for review (an app can not confirm).
    live = (Response.tenant_id == work.tenant.id, Response.form_id == form.id, Response.deleted_at.is_(None))
    fingerprint = rules.fingerprint_of(answers)
    if (await db.execute(select(Response.id).where(*live, Response.fingerprint == fingerprint).limit(1))).scalar_one_or_none():
        raise GatewayError("FRM-RESP-1005", [{"field": "body", "message": "same_answers"}])
    possible: dict[str, Any] | None = None
    identity = rules.identity_of(schema)
    if identity["email"]:
        rows = (await db.execute(select(Response.id, Response.submitted_at, Response.data).where(*live)
                                 .order_by(Response.submitted_at.desc()))).all()
        earlier_records = [{"id": str(r.id), "submitted_at": iso(r.submitted_at), "data": r.data} for r in rows]
        match = rules.match_identity(schema, answers, earlier_records, identity)
        if match["level"] == "clear":
            found = match["record"] or {}
            raise GatewayError("FRM-RESP-1006", [{"field": identity["email"], "message": "already_submitted",
                                                  "submitted_at": found.get("submitted_at"),
                                                  "email": rules.mask_email((found.get("data") or {}).get(identity["email"])) or None}])
        if match["level"] == "likely":
            possible = {"of": match["record"]["id"], "reason": match["reason"]}

    if work.test:
        answer = {"data": {"id": encode(uuid.uuid4()), "submitted_at": iso(moment), "status": "new",
                           "data": {f["name"]: answers.get(f["key"]) for f in work.choices if f.get("returned")}},
                  "meta": {"test": True}}
        await _remember(work, key, digest, None, answer, moment)
        return 201, answer
    stored = await _store(work, answers, fingerprint, identity, possible, files, moment)
    await _remember(work, key, digest, stored.id, None, moment)
    return 201, {"data": record_of(work, stored)}


async def _replay(work: Work) -> tuple[int, Any] | None:
    """A retry within 24 hours: the same key and body answer with the first record; the same key with another body is
    refused, so a key reused by mistake never swallows a new record silently (owner, 2026-10-06). Recognised before
    the answers are checked again, so a retry that carries file ids (already attached to its record) still replays."""
    db = work.db
    work.digest = hashlib.sha256(canonical_json(work.body).encode()).hexdigest()
    earlier = (await db.execute(select(ApiIdempotency).where(
        ApiIdempotency.tenant_id == work.tenant.id, ApiIdempotency.endpoint_id == work.endpoint.id,
        ApiIdempotency.formalie_key == (work.call.call_key or ""), ApiIdempotency.deleted_at.is_(None)))).scalar_one_or_none()
    moment = datetime.now(UTC)
    if earlier is not None and earlier.at <= moment - timedelta(hours=REPLAY_HOURS):
        earlier.deleted_at = moment
        await db.flush()
        return None
    if earlier is None:
        return None
    if earlier.body_hash != work.digest:
        raise GatewayError("FRM-API-1020", [{"field": "Formalie-Key", "message": "used_for_another_body"}])
    if earlier.answer is not None:
        return 200, {**earlier.answer, "meta": {"replayed": True}}
    first = (await db.execute(select(Response).where(
        Response.tenant_id == work.tenant.id, Response.id == earlier.response_id,
        Response.deleted_at.is_(None)))).scalar_one_or_none() if earlier.response_id else None
    if first is not None:
        return 200, {"data": record_of(work, first), "meta": {"replayed": True}}
    earlier.deleted_at = moment  # its record was deleted since: the key makes a new one
    await db.flush()
    return None


async def _remember(work: Work, key: str, digest: str, response_id: uuid.UUID | None, answer: Any,
                    moment: datetime) -> None:
    """The key, in the same transaction as the record: a retry racing this one waits, then replays it."""
    made = (await work.db.execute(insert(ApiIdempotency).values(
        id=uuid.uuid4(), tenant_id=work.tenant.id, organisation_id=work.tenant.organisation_id,
        endpoint_id=work.endpoint.id, formalie_key=key, body_hash=digest, response_id=response_id, answer=answer,
        at=moment).on_conflict_do_nothing(index_elements=["tenant_id", "endpoint_id", "formalie_key"],
                                          index_where=ApiIdempotency.deleted_at.is_(None))
        .returning(ApiIdempotency.id))).scalar_one_or_none()
    if made is None:
        raise Raced()


async def _store(work: Work, answers: dict[str, Any], fingerprint: str, identity: dict[str, Any],
                 possible: dict[str, Any] | None, files: list[Any], moment: datetime) -> Response:
    """The same pipeline as a response from the form's web page (public/router.py submit)."""
    db, tenant, form, schema = work.db, work.tenant, work.form, work.schema
    locked = (await db.execute(select(Form).where(Form.id == form.id).with_for_update())).scalar_one()
    if work.endpoint.version is not None:
        version_no: int | None = work.endpoint.version
    else:
        version = await db.get(FormVersion, locked.published_version_id) if locked.published_version_id else None
        version_no = version.number if version else None
    ctx_ip = work.call.caller.ip if work.call.caller else None
    response = Response(
        tenant_id=tenant.id, organisation_id=tenant.organisation_id, submitted_at=moment, form_id=form.id,
        form_version_no=version_no, number=locked.next_response_number, data=answers,
        language=rules.main_language(schema), channel="api", submission_id=None,
        api_token_id=work.token.id if isinstance(work.token.id, uuid.UUID) else None, fingerprint=fingerprint,
        identity_email=rules.normalise_email(answers.get(identity["email"])) if identity["email"] else None,
        possible_duplicate=possible, ip=ctx_ip if ctx_ip and ctx_ip != "0.0.0.0" else None,
        user_agent=(work.request.headers.get("user-agent") or "")[:300] or None)
    db.add(response)
    await db.flush()
    for upload_row in files:
        upload_row.response_id, upload_row.response_submitted_at = response.id, moment
    await db.execute(update(Form).where(Form.id == form.id).values(
        responses_count=Form.responses_count + 1, next_response_number=Form.next_response_number + 1))
    from app.modules.destinations.service import response_stored
    from app.modules.platform_bridge.events import emit
    from app.modules.webhooks.service import response_event

    await emit(db, "response.created", {"form_id": str(form.id), "response_id": str(response.id),
                                        "submitted_at": iso(moment), "channel": "api"},
               tenant_id=tenant.id, organisation_id=tenant.organisation_id, source="api")
    await response_stored(db, locked, response)  # the form's database table, when it has one
    await response_event(db, "response.created", locked, response)  # the workspace's webhooks
    await record(db, tenant_id=tenant.id, organisation_id=tenant.organisation_id, action="responses.submitted",
                 actor=actor_of(work), resource={"type": "form", "id": str(form.id), "name": form.name},
                 changes=[{"field": "channel", "before": None, "after": "api"}],
                 metadata={"endpoint": work.endpoint.name})

    def after_commit() -> None:  # emails and notifications, once the response is committed
        from app.modules.responses import after

        after.dispatch(tenant, form.id, response.id)
    db.info.setdefault("after_commit", []).append(after_commit)
    return response


async def _change(work: Work, files: list[Any]) -> tuple[int, Any]:
    """PUT / DELETE on one record."""
    db, body = work.db, work.body
    entry = await one_of(work)
    if entry is None and not work.test:
        raise GatewayError("FRM-API-1013")
    from app.modules.responses.router import _event
    from app.modules.responses.service import Entry

    if work.call.method == "DELETE":
        if not work.test and entry is not None:
            entry.deleted_at, entry.deleted_by = datetime.now(UTC), None
            await db.execute(update(Form).where(Form.id == work.form.id, Form.responses_count > 0)
                             .values(responses_count=Form.responses_count - 1))
            await record(db, tenant_id=work.tenant.id, organisation_id=work.tenant.organisation_id,
                         action="responses.deleted", actor=actor_of(work),
                         resource={"type": "response", "id": str(entry.id), "name": work.form.name},
                         metadata={"endpoint": work.endpoint.name})
            await _event(db, "response.deleted", Entry(entry, work.form, work.schema))
        return 200, {"data": {"id": work.record_ref, "deleted": True}, **({"meta": {"test": True}} if work.test else {})}

    problems: list[dict[str, Any]] = []
    for key, value in body.items():
        definition = work.fields.get(key)
        issue = validate_answer(definition, value, bool(definition.get("required"))) if definition else None
        if issue:
            problems.append({"field": key, "message": issue["code"]})
    # Lists with levels (F15 M2): a level sent must sit under the record's choice above (after this change); levels
    # below a changed one that no longer fit are cleared, as in the form
    before = dict(entry.data or {}) if entry is not None else {}
    by_id = {f["id"]: f for f in work.fields.values()}
    merged = {**before, **body}
    for fld in by_id.values():
        if not fld.get("option_parent") or merged.get(fld["key"]) is None:
            continue
        fitted = fit_answer(fld, by_id, merged)
        fitted = None if fitted is js.UNDEFINED else fitted
        if json.dumps(fitted) == json.dumps(merged.get(fld["key"])):
            continue
        if fld["key"] in body:
            problems.append({"field": fld["key"], "message": "choice"})
        else:
            body[fld["key"]] = fitted
        merged[fld["key"]] = fitted
    if problems:
        raise GatewayError("FRM-RESP-1001", problems)
    if work.test or entry is None:
        return 200, {"data": {"id": work.record_ref, **body}, "meta": {"test": True}}
    for upload_row in files:
        upload_row.response_id, upload_row.response_submitted_at = entry.id, entry.submitted_at
    moment = datetime.now(UTC)
    actor = actor_of(work)
    from app.modules.responses.models import ResponseChange

    for key, value in body.items():
        db.add(ResponseChange(tenant_id=entry.tenant_id, organisation_id=entry.organisation_id, response_id=entry.id,
                              response_submitted_at=entry.submitted_at, at=moment, by_id=None, by_name=actor.name or "",
                              field=f"answer:{key}", before=before.get(key), after=value))
    entry.data, entry.edited = {**before, **body}, True
    entry.updated_at, entry.row_version = moment, entry.row_version + 1
    await record(db, tenant_id=work.tenant.id, organisation_id=work.tenant.organisation_id, action="responses.updated",
                 actor=actor, resource={"type": "response", "id": str(entry.id), "name": work.form.name},
                 changes=[{"field": (work.fields.get(k) or {}).get("label") or k, "before": js.stringify(before.get(k)),
                           "after": js.stringify(body.get(k))} for k in body],
                 metadata={"endpoint": work.endpoint.name})
    await db.flush()
    await _event(db, "response.updated", Entry(entry, work.form, work.schema))
    return 200, {"data": record_of(work, entry)}

