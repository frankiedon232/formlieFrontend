"""Dashboard, Forms view (F21 M2; mock: routes/dashboardForms.ts): running the forms. Forms the person may see
(role, sharing, folder access); responses only of forms whose responses they may see. Same period and filter rules
as the Workspace view.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from app.core.db.session import db_session
from app.modules.analytics.rules import jround
from app.modules.auth.sessions import Principal
from app.modules.dashboard import common as C
from app.modules.dashboard.rules import iso_day, period_from
from app.modules.forms import access
from app.modules.forms.access import viewer_for
from app.modules.forms.service import Names, iso

ORDER = {"nearly_full": 0, "closing": 1, "no_responses": 2, "unpublished_changes": 3, "stale_draft": 4}


async def forms_view(principal: Principal, query: dict[str, Any]) -> dict[str, Any]:
    tenant_id = principal.tenant.id
    async with db_session("read", **C.scope(principal)) as db:
        viewer = await viewer_for(db, principal)
        clock = await C.clock_of(db, tenant_id)
        p = period_from(query, clock.today())
        scope = C.filter_of(query)
        forms = [f for f in await C.visible_forms(db, viewer, tenant_id)
                 if scope.matches(C.form_folder(f, viewer), str(f.owner_id))]
        counted = [f.id for f in forms if access.responses_allowed(f, viewer, "view")]
        per_day = await C.responses_per_day(db, tenant_id, counted, clock, p.prev_start, p.end)
        channels = await C.channels(db, tenant_id, counted, clock, p.start, p.end)
        names = await Names().load(db, tenant_id)

    now = datetime.now(UTC)
    created = [{"start": start, "count": 0} for start in p.buckets]
    created_now = created_before = silent = active = active_before = responses_now = responses_before = 0
    top: list[dict[str, Any]] = []
    folders: dict[str, dict[str, Any]] = {}
    owners: dict[str, dict[str, Any]] = {}
    work: list[dict[str, Any]] = []
    for form in forms:
        made = clock.day_of(form.created_at)
        if p.start <= made <= p.end:
            created_now += 1
            i = p.bucket_of(made)
            if i is not None:
                created[i]["count"] += 1
        elif p.prev_start <= made < p.start:
            created_before += 1

        days = per_day.get(form.id, {})
        own = sum(n for day, n in days.items() if p.start <= day <= p.end)
        own_before = sum(n for day, n in days.items() if p.prev_start <= day < p.start)
        responses_now += own
        responses_before += own_before
        active += bool(own)
        active_before += bool(own_before)
        if own or own_before:
            top.append({"id": str(form.id), "name": form.name, "status": form.status, "responses": own,
                        "previous": own_before, "completion_rate": form.completion_rate or 0})

        folder = viewer.folders.get(form.folder_id) if form.folder_id else None
        key = str(folder.id) if folder else "_none"
        group = folders.setdefault(key, {"id": str(folder.id) if folder else None, "name": folder.name if folder else None,
                                         "forms": 0, "responses": 0})
        group["forms"] += 1
        group["responses"] += own
        owner = owners.setdefault(str(form.owner_id), {"id": str(form.owner_id),
                                                       "name": names.by_id.get(form.owner_id, ""), "forms": 0,
                                                       "responses": 0})
        owner["forms"] += 1
        owner["responses"] += own

        # What needs work
        ref = {"id": str(form.id), "name": form.name}
        if form.status == "draft" and now - form.updated_at > timedelta(days=14):
            work.append({"kind": "stale_draft", "form": ref, "at": iso(form.updated_at), "count": None})
        if form.status == "published" and not own:
            silent += 1
            work.append({"kind": "no_responses", "form": ref, "at": None, "count": None})
        if form.has_unpublished_changes:
            work.append({"kind": "unpublished_changes", "form": ref, "at": iso(form.updated_at), "count": None})
        if form.status == "published" and form.closes_at and now < form.closes_at < now + timedelta(days=7):
            work.append({"kind": "closing", "form": ref, "at": iso(form.closes_at), "count": None})
        if form.status == "published" and form.response_limit and form.responses_count >= form.response_limit * 0.9:
            work.append({"kind": "nearly_full", "form": ref, "at": None, "count": form.response_limit})

    work.sort(key=lambda item: ORDER[item["kind"]])

    def by_status(status: str) -> int:
        return sum(1 for f in forms if f.status == status)

    def per_form(responses: int, count: int) -> int:
        return jround(responses / count) if count else 0

    return {
        "from": iso_day(p.start), "to": iso_day(p.end), "group": p.group,
        "new_workspace": not forms and not scope.filtered,
        "kpis": {
            "published": {"value": by_status("published"), "previous": None},
            "created": {"value": created_now, "previous": created_before},
            "per_form": {"value": per_form(responses_now, active),
                         "previous": per_form(responses_before, active_before) if active_before else None},
            "silent": {"value": silent, "previous": None},
            "unpublished": {"value": sum(1 for f in forms if f.has_unpublished_changes), "previous": None},
        },
        "by_status": {s: by_status(s) for s in ("draft", "published", "closed", "archived")},
        "created": created,
        "channels": channels,
        "top": sorted(top, key=lambda t: -t["responses"])[:8],
        "folders": sorted(folders.values(), key=lambda f: (-f["responses"], -f["forms"]))[:8],
        "owners": sorted(owners.values(), key=lambda o: (-o["responses"], -o["forms"]))[:6],
        "work": work[:12],
    }
