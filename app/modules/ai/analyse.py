"""AI assistant, analysing (mock: routes/aiAnalyse.ts). All need ai.analyse, the assistant allowed to read forms and
responses (FRM-AI-1003), and the person allowed to see the form's responses (else "not found").

    POST /ai/analysis               { form_id, from?, to? } → AiAnalysis (kind analysis; default the last 30 days)
    POST /ai/digest                 { form_id, period (week · month · quarter) } → AiAnalysis (kind summary)
    POST /ai/ask                    { form_id, question } → AiAnswer (kind question)
    POST /ai/responses/{id}/summary → AiResponseSummary (kind summary)

Numbers are always counted here from the responses. The model reads written answers (tone and themes), plans what a
question asks, and summarises one response; personal data is masked before it reaches the model when the workspace
asks for it, and names, emails, phones and addresses are never sent for a summary.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any, Callable

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select

from app.core import zod as z
from app.core.db.session import db_session
from app.core.errors import FrmError
from app.core.responses import ok
from app.core.security.limits import rate_limit
from app.modules.ai import checks as C
from app.modules.ai import engine_analysis as AN
from app.modules.ai import prompts as P
from app.modules.ai import service as A
from app.modules.ai.assistant import produce, produce_all
from app.modules.ai.create import reference
from app.modules.ai.kinds import credits_of
from app.modules.ai.kit import mask_text
from app.modules.ai.provider import ModelTask
from app.modules.ai.router import scope
from app.modules.auth.sessions import Principal, require_auth

router = APIRouter(tags=["ai"])
DAY = AN.DAY
LABEL_CHUNK = 150
LABEL_MAX = 600  # written answers the model reads per request; the rest are read with the word lists


def today_ms() -> int:
    return AN.day_ms(datetime.now(UTC).date().isoformat())


async def _form_for(db: Any, principal: Principal, form_id: Any) -> tuple[Any, dict[str, Any] | None]:
    """A form whose responses this person may see (anything else is "not found"), and the questions it is read with."""
    from app.modules.forms import access
    from app.modules.forms.access import viewer_for
    from app.modules.forms.models import Form
    from app.modules.responses.service import response_schema

    wanted = reference(form_id)
    form = await db.get(Form, wanted) if wanted else None
    viewer = await viewer_for(db, principal)
    if form is None or form.tenant_id != principal.tenant.id or form.deleted_at is not None or form.purged_at is not None \
            or not access.responses_allowed(form, viewer, "view"):
        raise FrmError("FRM-GEN-1004")
    return form, await response_schema(db, form)


async def _entries(db: Any, form: Any, since: int | None = None) -> list[dict[str, Any]]:
    from app.modules.responses.models import Response

    query = select(Response.id, Response.number, Response.submitted_at, Response.status, Response.data).where(
        Response.tenant_id == form.tenant_id, Response.form_id == form.id, Response.deleted_at.is_(None))
    if since is not None:
        query = query.where(Response.submitted_at >= datetime.fromtimestamp(since / 1000, UTC))
    rows = (await db.execute(query.order_by(Response.submitted_at.desc(), Response.id.desc()))).all()
    return [{"id": str(r.id), "number": r.number, "at": int(r.submitted_at.timestamp() * 1000), "status": r.status,
             "data": r.data or {}} for r in rows]


async def _labels(texts: list[str], mask: Callable[[str], str]) -> tuple[Callable[[str], tuple[str, list[str]]], A.Made]:
    """Tone and themes of written answers: the model's reading, the word lists for anything it didn't read."""
    unique = list(dict.fromkeys(texts))[:LABEL_MAX]
    jobs = []
    for start in range(0, len(unique), LABEL_CHUNK):
        part = unique[start:start + LABEL_CHUNK]
        jobs.append((ModelTask(task="labels", system=P.labels_system(), schema=P.LABELS, fast=True,
                               content=P.content({"answers": [{"i": i, "text": mask(t)} for i, t in enumerate(part)]}),
                               standin=dict),
                     lambda data, part=part: {part[i]: v for i, v in C.labels_from_model(data, len(part)).items()}))
    answers, made = await produce_all(jobs)
    found: dict[str, tuple[str, list[str]]] = {}
    for part in answers:
        found.update(part or {})
    return (lambda text: found.get(text) or AN.word_labels(text)), made


async def _analysis(principal: Principal, settings: dict[str, Any], form: Any, schema: dict[str, Any] | None,
                    entries: list[dict[str, Any]], start: int, end: int) -> tuple[dict[str, Any], A.Made]:
    mask = mask_text if settings["mask_personal"] else (lambda text: text)
    fields = AN.fields_of(schema)
    length = end - start + DAY
    texts = [t for e in entries if start - length <= e["at"] < end + DAY for t in AN.text_of(fields, e["data"])]
    labels, made = await _labels(texts, mask)
    return AN.analyse({"id": str(form.id), "name": form.name}, schema, entries, start, end, mask, labels), made


day_text = z.string().regex(r"^\d{4}-\d{2}-\d{2}$")
analysis_input = z.obj(form_id=z.string().min(1), **{"from": day_text.nullable().optional(),
                                                      "to": z.string().regex(r"^\d{4}-\d{2}-\d{2}$").nullable().optional()})


def _day_or_none(value: Any) -> int | None:
    try:
        return AN.day_ms(date.fromisoformat(value).isoformat()) if value else None
    except ValueError:
        raise FrmError("FRM-GEN-1002", [{"field": "from", "message": "Invalid date"}]) from None


@router.post("/ai/analysis", dependencies=[rate_limit("ai-analyse", per_minute=20)])
async def analysis_route(request: Request, principal: Principal = Depends(require_auth)) -> Any:
    async with db_session("read", **scope(principal)) as db:
        settings = await A.require_ai(db, principal.tenant, "analysis", ["forms", "responses"])
        values = analysis_input.parse(await request.json())
        form, schema = await _form_for(db, principal, values["form_id"])
        to = _day_or_none(values.get("to")) or today_ms()
        start = _day_or_none(values.get("from")) or to - 29 * DAY
        start, to = min(start, to), max(start, to)
        entries = await _entries(db, form, start - (to - start + DAY))
    result, made = await _analysis(principal, settings, form, schema, entries, start, to)
    async with db_session("write", **scope(principal)) as db:
        saved = await A.record_request(
            db, principal, settings, kind="analysis", status="applied", title=f"Analysis of {form.name}",
            title_key={"code": "analysis", "params": {"form": form.name}},
            target={"type": "form", "id": str(form.id), "name": form.name}, credits=credits_of("analysis"),
            prompt=f"Analyse the responses from {result['period']['from']} to {result['period']['to']}",
            result=f"{result['totals']['responses']} responses, {result['totals']['text_answers']} written answers, "
                   f"{len(result['themes'])} themes.",
            read=["forms", "responses"], made=made, notes=result["findings"])
        return ok({**result, "request_id": str(saved.id), "credits": saved.credits})


digest_input = z.obj(form_id=z.string().min(1), period=z.enum(["week", "month", "quarter"]).optional())
LENGTH = {"week": 7, "month": 30, "quarter": 91}
ADJECTIVE = {"week": "Weekly", "month": "Monthly", "quarter": "Quarterly"}


@router.post("/ai/digest", dependencies=[rate_limit("ai-analyse", per_minute=20)])
async def digest_route(request: Request, principal: Principal = Depends(require_auth)) -> Any:
    async with db_session("read", **scope(principal)) as db:
        settings = await A.require_ai(db, principal.tenant, "summary", ["forms", "responses"])
        values = digest_input.parse(await request.json())
        period = values.get("period") or "week"
        form, schema = await _form_for(db, principal, values["form_id"])
        to = today_ms()
        start = to - (LENGTH[period] - 1) * DAY
        entries = await _entries(db, form, start - LENGTH[period] * DAY)
    result, made = await _analysis(principal, settings, form, schema, entries, start, to)
    async with db_session("write", **scope(principal)) as db:
        saved = await A.record_request(
            db, principal, settings, kind="summary", status="applied", title=f"{ADJECTIVE[period]} digest of {form.name}",
            title_key={"code": f"digest_{period}", "params": {"form": form.name}},
            target={"type": "form", "id": str(form.id), "name": form.name}, credits=credits_of("summary"),
            prompt=f"Summarise the {period} of responses",
            result=f"{result['totals']['responses']} responses ({result['totals']['previous']} the {period} before).",
            read=["forms", "responses"], made=made, notes=result["findings"])
        return ok({**result, "request_id": str(saved.id), "credits": saved.credits})


ask_input = z.obj(form_id=z.string().min(1), question=z.string().trim().min(3).max(500))


@router.post("/ai/ask", dependencies=[rate_limit("ai-analyse", per_minute=30)])
async def ask_route(request: Request, principal: Principal = Depends(require_auth)) -> Any:
    async with db_session("read", **scope(principal)) as db:
        settings = await A.require_ai(db, principal.tenant, "question", ["forms", "responses"])
        values = ask_input.parse(await request.json())
        form, schema = await _form_for(db, principal, values["form_id"])
        entries = await _entries(db, form)
    question = values["question"]
    shown = mask_text(question) if settings["mask_personal"] else question
    fields = [f for f in AN.fields_of(schema) if f["type"] != "hidden"]
    now = int(datetime.now(UTC).timestamp() * 1000)
    today = datetime.now(UTC).date()
    brief = [{"key": f["key"], "label": f.get("label"), "type": f["type"],
              **({"options": [{"value": o.get("value"), "label": o.get("label")} for o in f["options"][:50]]}
                 if f.get("options") else {})} for f in fields]
    task = ModelTask(task="question", system=P.question_system(), schema=P.QUESTION, fast=True,
                     content=P.content({"today": today.isoformat(), "question": shown, "questions": brief}),
                     standin=lambda: AN.plan_question(question, fields, now))
    plan, made = await produce(task, lambda data: C.plan_from_model(data, fields, today))
    result = AN.run_question(plan, fields, entries)
    if result["kind"] == "top":
        summary = ", ".join(f"{r['label']}: {r['count']}" for r in result["rows"][:3])
    elif result["kind"] == "trend":
        summary = f"{len(result['rows'])} periods"
    else:
        summary = "No answer" if result["value"] is None else str(result["value"])
    async with db_session("write", **scope(principal)) as db:
        saved = await A.record_request(
            db, principal, settings, kind="question", status="applied", title=question[:120],
            target={"type": "form", "id": str(form.id), "name": form.name}, credits=credits_of("question"),
            prompt=shown, result=summary, read=["forms", "responses"], made=made, notes=result["notes"])
        return ok({**result, "question": question, "request_id": str(saved.id), "credits": saved.credits})


@router.post("/ai/responses/{response_id}/summary", dependencies=[rate_limit("ai-analyse", per_minute=30)])
async def response_summary_route(response_id: str, principal: Principal = Depends(require_auth)) -> Any:
    from app.modules.forms.access import viewer_for
    from app.modules.responses.router import response_for

    async with db_session("read", **scope(principal)) as db:
        settings = await A.require_ai(db, principal.tenant, "summary", ["forms", "responses"])
        viewer = await viewer_for(db, principal)
        entry = await response_for(db, viewer, response_id, "view")
    form, schema, data = entry.form, entry.schema, dict(entry.response.data or {})
    number = entry.response.number
    mask = mask_text if settings["mask_personal"] else (lambda text: text)
    fields = AN.summary_fields(schema, data)
    answers = [{"key": f["key"], "label": f.get("label"), "type": f["type"], "answer": mask(AN.point_text(f, data[f["key"]]))}
               for f in fields[:12]]
    task = ModelTask(task="summary", system=P.summary_system(), schema=P.SUMMARY, fast=True,
                     content=P.content({"form": form.name, "answers": answers}),
                     standin=lambda: AN.summarise(schema, data, mask))
    result, made = await produce(task, lambda out: C.summary_from_model(out, fields[:12], data, mask))
    async with db_session("write", **scope(principal)) as db:
        saved = await A.record_request(
            db, principal, settings, kind="summary", status="applied", title=f"Summary of response #{number}",
            title_key={"code": "response_summary", "params": {"n": number}},
            target={"type": "response", "id": str(entry.response.id), "name": f"{form.name} #{number}"},
            credits=credits_of("summary"), prompt=f"Summarise response #{number}",
            result="; ".join(f"{p['label']}: {p['value']}" for p in result["points"]), read=["forms", "responses"],
            made=made)
        return ok({**result, "request_id": str(saved.id), "credits": saved.credits})

