"""Query review fixes (B17, docs/reviews/2026-10-query-review.md) give the same answers as before, against the test
database:

- Q2: the same / near email check reads only the candidates (public/duplicates.py) and finds exactly what
  rules.match_identity finds over every earlier response, across pages, ties and deleted rows; an edited email keeps
  `identity_email` in step.
- Q3: the API gateway's list filters, sorts and pages in SQL with the old in-memory answers (the filter's text rules
  for strings, numbers, true / false, nothing, objects and lists).
- Q11: Trash is purged and closing forms are announced by Beat, not by the GETs.
- Q12: processed_events rows past the replay window are pruned; recent ones stay.
"""

from __future__ import annotations

import json
import math
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from sqlalchemy import select

from app.core import js
from app.core.db.session import db_session
from app.modules.api_service import gateway_records
from app.modules.forms.models import Form
from app.modules.links.seo import published_schema
from app.modules.public import duplicates, rules
from app.modules.responses.models import Response
from tests.conftest import client_for
from tests.db.test_api_gateway import API, call, setup
from tests.db.test_api_service import job_form
from tests.db.test_auth_flows import app, seeded, sign_in  # noqa: F401  (fixtures)
from tests.db.test_destinations import real
from tests.db.test_public_forms import publish
from tests.db.test_settings import PASSWORD, new_workspace
from tests.secure_client import SecureClient

pytestmark = pytest.mark.db


def _insert(superuser, tenant_id, organisation_id, form_id, number: int, at: datetime, data: dict[str, Any],  # noqa: ANN001
            *, identity_email: str | None = None, deleted: bool = False) -> uuid.UUID:
    rid = uuid.uuid4()
    superuser.execute(
        "INSERT INTO formaly.responses (id, tenant_id, organisation_id, submitted_at, form_id, number, data, language, "
        "channel, fingerprint, identity_email, deleted_at) VALUES (%s, %s, %s, %s, %s, %s, %s, 'en', 'link', %s, %s, %s)",
        (rid, tenant_id, organisation_id, at, form_id, number, json.dumps(data), uuid.uuid4().hex, identity_email,
         at if deleted else None))
    return rid


async def test_near_email_check_matches_the_whole_list(app, superuser, monkeypatch) -> None:  # noqa: ANN001, F811
    sub, email = await new_workspace(app)
    async with client_for(app, host=f"{sub}.formalie.dev") as http:
        owner = SecureClient(http)
        await sign_in(owner, email, PASSWORD)
        form = await publish(owner, "Sign-up", job_form)  # first_name, email (the identity email)
    form_id = real(form["id"])
    tenant_id, organisation_id = superuser.execute(
        "SELECT tenant_id, organisation_id FROM formaly.forms WHERE id = %s", (form_id,)).fetchone()
    base = datetime.now(UTC) - timedelta(hours=2)
    stored = [  # oldest first: (first_name, email, deleted)
        ("Ana", "ana.silva@example.org", False),
        ("Ana", "ana.silvx@exampel.org", False),   # a typo in the name part and in the domain: still near
        ("Ana", "ana.silva@exampel.org", False),   # the domain a typo away
        ("Bo", "ana.silvq@example.org", False),    # near email, another person's name
        ("Cy", "Cy.Rus+news@gmail.com", False),
        ("Di", None, False),                       # no email given
        ("Ed", "ed@example.org", True),            # deleted: never matched
        ("Ana", "ANA.SILVA@EXAMPLE.ORG", False),   # the same email again, newer
        ("Fay", "fay@example.net", False),
        ("Gus", "gus@example.net", False),
    ]
    stored += [(f"User {n}", f"user{n:03d}@example.org", False) for n in range(12)]
    same_time = base + timedelta(minutes=30)
    for n, (name, address, deleted) in enumerate(stored):
        at = same_time if n in (2, 3) else base + timedelta(minutes=n)  # two at the same moment: newest id wins
        data = {"first_name": name, **({"email": address} if address else {})}
        _insert(superuser, tenant_id, organisation_id, form_id, n + 1, at, data,
                identity_email=rules.normalise_email(address), deleted=deleted)

    probes = [
        {"first_name": "Ana", "email": "ana.silva@example.org"},       # clear
        {"first_name": "Ana", "email": " Ana.Silva+x@Example.org "},   # clear after normalising
        {"first_name": "Ana", "email": "ana.silvb@example.org"},       # likely
        {"first_name": "Zed", "email": "ana.silvb@example.org"},       # near emails, no similar name
        {"first_name": "", "email": "ana.silvb@example.org"},          # no name: any near email
        {"first_name": "Ana", "email": "ana.silvz@exampel.org"},       # near through a double typo
        {"first_name": "Ed", "email": "ed@example.org"},               # only a deleted response has it
        {"first_name": "Ed", "email": "ef@example.org"},               # near a deleted one only
        {"first_name": "Cy", "email": "cyrus@gmail.com"},              # Gmail ignores dots and plus tags
        {"first_name": "Cy", "email": "cyrus@googlemail.com"},
        {"first_name": "Cy", "email": "cyruz@gmail.com"},
        {"first_name": "User 5", "email": "user005@example.com"},      # the domain a typo away, older rows
        {"first_name": "User 9", "email": "usr009@example.org"},
        {"first_name": "Fay", "email": "fay@example.nt"},
        {"first_name": "Hal", "email": "someone.else@elsewhere.org"},  # nothing near
        {"first_name": "Hal", "email": "not an email"},
        {"first_name": "Hal"},
    ]

    async with db_session("read", tenant_id=tenant_id, organisation_id=organisation_id) as db:
        schema = await published_schema(db, await db.get(Form, form_id))
        identity = rules.identity_of(schema)
        assert identity["email"] == "email"
        rows = (await db.execute(select(Response.id, Response.submitted_at, Response.data).where(
            Response.tenant_id == tenant_id, Response.form_id == form_id, Response.deleted_at.is_(None))
            .order_by(Response.submitted_at.desc(), Response.id.desc()))).all()
        everything = [{"id": str(r.id), "submitted_at": duplicates._iso(r.submitted_at), "data": r.data} for r in rows]
        for page in (duplicates.PAGE, 3, 1):
            monkeypatch.setattr(duplicates, "PAGE", page)
            for probe in probes:
                before = rules.match_identity(schema, probe, everything, identity)
                now = await duplicates.match_earlier(db, tenant_id, form_id, schema, probe, identity)
                assert now == before, (page, probe)
        levels = [(await duplicates.match_earlier(db, tenant_id, form_id, schema, p, identity))["level"]
                  for p in probes[:8]]
    assert levels == ["clear", "clear", "likely", "none", "likely", "likely", "none", "none"]

    # An answer edited in the portal keeps identity_email in step, so the check sees the new email
    async with client_for(app, host=f"{sub}.formalie.dev") as http:
        owner = SecureClient(http)
        await sign_in(owner, email, PASSWORD)
        _, reply = await owner.request("GET", f"/forms/{form['id']}/responses", query={"q": "#9"})
        fay = reply["data"][0]
        assert fay["answers"]["email"] == "fay@example.net"
        status, reply = await owner.request("PATCH", f"/responses/{fay['id']}", body={"data": {"email": "Fay.N@Example.net"}})
        assert status == 200, reply
    assert superuser.execute("SELECT identity_email FROM formaly.responses WHERE form_id = %s AND number = 9",
                             (form_id,)).fetchone()[0] == "fay.n@example.net"


def _old_keep(value: Any, wanted: str) -> bool:
    """The gateway's filter before Q3 (in memory)."""
    if isinstance(value, list):
        return wanted in [js.to_string(v) for v in value]
    return ("" if value is None else js.to_string(value)) == wanted


async def test_gateway_filter_text_rules_in_sql(app, superuser) -> None:  # noqa: ANN001, F811
    sub, email = await new_workspace(app)
    async with client_for(app, host=f"{sub}.formalie.dev") as http:
        owner = SecureClient(http)
        await sign_in(owner, email, PASSWORD)
        form = await publish(owner, "Values", job_form)
    form_id = real(form["id"])
    tenant_id, organisation_id = superuser.execute(
        "SELECT tenant_id, organisation_id FROM formaly.forms WHERE id = %s", (form_id,)).fetchone()
    values: list[Any] = ["a", "", None, 5, 5.5, 0, -0.0, 0.1, 1e21, 1e-7, 12345678901234567890, 2**53 + 1, True, False,
                         {"x": 1}, ["a", "b"], ["5", 5, None, True, {"a": 1}], [], "true", "5", "1e+21",
                         "[object Object]", "null", " 5", "05", "Ünïcödé"]
    at = datetime.now(UTC) - timedelta(hours=1)
    ids: dict[uuid.UUID, Any] = {}
    for n, value in enumerate(values):
        ids[_insert(superuser, tenant_id, organisation_id, form_id, n + 1, at, {"v": value})] = value
    ids[_insert(superuser, tenant_id, organisation_id, form_id, 99, at, {})] = js.UNDEFINED  # no answer at all
    wanted_texts = ["a", "b", "", "5", "5.5", "0", "-0", "0.1", "1e+21", "1e-7", "1000000000000000000000",
                    "12345678901234567000", "12345678901234567890", "9007199254740992", "9007199254740993", "true",
                    "false", "[object Object]", "null", "undefined", " 5", "05", "5.0", "x", "Ünïcödé", "NaN"]
    async with db_session("read", tenant_id=tenant_id, organisation_id=organisation_id) as db:
        rows = {r.id: r.data for r in (await db.execute(select(Response.id, Response.data).where(
            Response.form_id == form_id))).all()}
        for wanted in wanted_texts:
            found = set((await db.execute(select(Response.id).where(
                Response.form_id == form_id, gateway_records._answer_is("v", wanted, 0)))).scalars())
            expected = {rid for rid, data in rows.items() if _old_keep(data.get("v"), wanted)}
            assert found == expected, (wanted, sorted(str(rows[r].get("v")) for r in found ^ expected))


async def test_gateway_list_pages_and_sorts_in_sql(app, superuser) -> None:  # noqa: ANN001, F811
    sub, email = await new_workspace(app)
    async with client_for(app, host=f"{sub}.formalie.dev") as http, client_for(app, host=API) as api:
        owner = SecureClient(http)
        await sign_in(owner, email, PASSWORD)
        made = await setup(owner)  # page size 50, `email` is a filter
        form_id = real(made["form"]["id"])
        tenant_id, organisation_id = superuser.execute(
            "SELECT tenant_id, organisation_id FROM formaly.forms WHERE id = %s", (form_id,)).fetchone()
        base = datetime.now(UTC) - timedelta(hours=1)
        rows = []
        for n in range(9):
            at = base + timedelta(minutes=n if n not in (4, 5, 6) else 4)  # three at the same moment
            data = {"first_name": f"P{n}", "email": "ana@example.org" if n % 2 else f"p{n}@example.org"}
            rid = _insert(superuser, tenant_id, organisation_id, form_id, n + 1, at, data, deleted=n == 7)
            if n != 7:
                rows.append((at, rid, data))

        def expected(params: dict[str, str]) -> tuple[list[str], dict[str, Any]]:
            live = sorted(rows, key=lambda r: (r[0], r[1]), reverse=True)  # newest first, then id
            if "email" in params:
                live = [r for r in live if r[2]["email"] == params["email"]]
            live.sort(key=lambda r: r[0], reverse=params.get("sort") != "submitted_at")
            per_page = min(50, max(1, gateway_records._number(params.get("per_page")) or 20))
            page = max(1, gateway_records._number(params.get("page")) or 1)
            start, end = int((page - 1) * per_page), int(page * per_page)
            return [r[2]["first_name"] for r in live[start:end]], {
                "page": gateway_records._plain(page), "per_page": gateway_records._plain(per_page), "total": len(live),
                "total_pages": max(1, math.ceil(len(live) / per_page))}

        cases = [{}, {"sort": "submitted_at"}, {"per_page": "3"}, {"per_page": "3", "page": "2"},
                 {"per_page": "3", "page": "3", "sort": "submitted_at"}, {"per_page": "2", "page": "9"},
                 {"email": "ana@example.org"}, {"email": "ana@example.org", "sort": "submitted_at", "per_page": "2"},
                 {"per_page": "2.5", "page": "2"}, {"page": "0", "per_page": "-1"}, {"email": "nobody@example.org"}]
        for params in cases:
            status, reply, _ = await call(api, "GET", made["path"], token=made["live_secret"], params=params)
            assert status == 200, reply
            names, meta = expected(params)
            assert [r["data"]["first_name"] for r in reply["data"]] == names, params
            assert {k: reply["meta"][k] for k in meta} == meta, params


async def test_trash_and_due_notifications_run_from_beat(app, superuser) -> None:  # noqa: ANN001, F811
    from app.modules.forms.tasks import sweep_trash_everywhere
    from app.modules.notifications.tasks import announce_everywhere

    sub, email = await new_workspace(app)
    async with client_for(app, host=f"{sub}.formalie.dev") as http:
        owner = SecureClient(http)
        await sign_in(owner, email, PASSWORD)
        old = await publish(owner, "Old form", job_form)
        recent = await publish(owner, "Recent form", job_form)
        closing = await publish(owner, "Closing soon", job_form)
        for made in (old, recent):
            status, reply = await owner.request("DELETE", f"/forms/{made['id']}")
            assert status == 200, reply
        superuser.execute("UPDATE formaly.forms SET deleted_at = now() - interval '31 days' WHERE id = %s", (real(old["id"]),))
        superuser.execute("UPDATE formaly.forms SET closes_at = now() + interval '3 hours' WHERE id = %s",
                          (real(closing["id"]),))

        # The GETs only read: the old form leaves the Trash list at once, but nothing is written
        _, reply = await owner.request("GET", "/forms", query={"filter[trash]": "1"})
        assert [f["name"] for f in reply["data"]] == ["Recent form"]
        assert superuser.execute("SELECT purged_at FROM formaly.forms WHERE id = %s", (real(old["id"]),)).fetchone()[0] is None
        _, reply = await owner.request("GET", "/notifications")
        assert not any(n["event"] == "form_closing" for n in reply["data"]["items"])

        # Beat: the Trash sweep purges it (the row stays), the announcement appears once
        assert await sweep_trash_everywhere() >= 1
        purged = superuser.execute("SELECT purged_at, deleted_at FROM formaly.forms WHERE id = %s", (real(old["id"]),)).fetchone()
        assert purged[0] is not None and purged[1] is not None
        assert superuser.execute("SELECT purged_at FROM formaly.forms WHERE id = %s", (real(recent["id"]),)).fetchone()[0] is None
        assert await announce_everywhere() >= 1
        await announce_everywhere()
        _, reply = await owner.request("GET", "/notifications")
        closing_items = [n for n in reply["data"]["items"] if n["event"] == "form_closing"]
        assert len(closing_items) == 1 and closing_items[0]["params"]["form"] == "Closing soon"


def test_processed_events_are_pruned_after_the_replay_window(superuser, db_settings, monkeypatch) -> None:  # noqa: ANN001
    from app.core.events import tasks
    from app.workers import db as worker_db

    monkeypatch.setattr(worker_db, "get_settings", lambda: db_settings)  # formalie_worker on the test database
    worker_db.worker_engine.cache_clear()
    old, fresh = uuid.uuid4(), uuid.uuid4()
    superuser.execute("INSERT INTO formaly.processed_events (consumer, event_id, processed_at) VALUES "
                      "('test.prune', %s, now() - interval '8 days'), ('test.prune', %s, now() - interval '6 days')",
                      (old, fresh))
    try:
        assert tasks.prune_processed() >= 1
        kept = {r[0] for r in superuser.execute(
            "SELECT event_id FROM formaly.processed_events WHERE consumer = 'test.prune'").fetchall()}
        assert old not in kept and fresh in kept
        # Never inside the replay window, whatever is asked
        assert superuser.execute("SELECT platform.prune_processed_events(0, 10)").fetchone()[0] == 0
        assert superuser.execute("SELECT count(*) FROM formaly.processed_events WHERE event_id = %s",
                                 (fresh,)).fetchone()[0] == 1
    finally:
        worker_db.worker_engine.cache_clear()


async def test_response_lists_in_sql_match_the_in_memory_lists(app, superuser) -> None:  # noqa: ANN001, F811
    from app.modules.responses import router as R

    sub, email = await new_workspace(app)
    async with client_for(app, host=f"{sub}.formalie.dev") as http:
        owner = SecureClient(http)
        await sign_in(owner, email, PASSWORD)
        made = [await publish(owner, name, job_form) for name in ("Beta", "alpha", "Alpha", "Ünï")]
    form_ids = [real(f["id"]) for f in made]
    tenant_id, organisation_id = superuser.execute(
        "SELECT tenant_id, organisation_id FROM formaly.forms WHERE id = %s", (form_ids[0],)).fetchone()
    base = datetime.now(UTC) - timedelta(days=3)
    statuses, channels = ["new", "reviewed", "approved", "rejected"], ["link", "embed", "api"]
    tag_sets = [[], ["vip"], ["vip", "late"], ["late"], ["x,y"]]
    for n in range(40):
        at = base + timedelta(hours=n // 3 * 5)  # three at a time share a moment
        rid = _insert(superuser, tenant_id, organisation_id, form_ids[n % 4], n + 1, at,
                      {"first_name": f"P{n}", "email": f"p{n}@example.org"}, deleted=n == 13)
        superuser.execute(
            "UPDATE formaly.responses SET status = %s, channel = %s, tags = %s, possible_duplicate = %s, "
            "duplicate_cleared = %s WHERE id = %s",
            (statuses[n % 4], channels[n % 3], json.dumps(tag_sets[n % 5]),
             json.dumps({"of": "x", "reason": "email_similar"}) if n % 6 == 0 else ("null" if n % 2 else None),
             n % 12 == 0, rid))
    day = (base + timedelta(days=1)).date().isoformat()
    cases: list[dict[str, str]] = [
        {}, {"sort": "submitted_at"}, {"sort": "-number"}, {"sort": "number"}, {"sort": "status"}, {"sort": "-status"},
        {"sort": "form"}, {"sort": "-form"}, {"sort": "anything"}, {"page": "2", "page_size": "7"},
        {"page": "9", "page_size": "7"}, {"page_size": "500"}, {"filter[status]": "new,approved"},
        {"filter[tag]": "vip"}, {"filter[tag]": "late,x,y"}, {"filter[channel]": "api"}, {"filter[flag]": "duplicate"},
        {"from": day}, {"to": day}, {"from": day, "to": day, "sort": "-status", "page_size": "3", "page": "2"},
        {"filter[form]": str(form_ids[1])}, {"filter[form]": f"{form_ids[2]},nonsense"}, {"filter[form]": "nonsense"},
        {"filter[form]": str(form_ids[0]).upper()},
    ]
    async with db_session("read", tenant_id=tenant_id, organisation_id=organisation_id) as db:
        forms = [await db.get(Form, i) for i in form_ids]
        for subset, answers in (([forms[0]], True), (forms, False)):
            everything = await R._entries(db, tenant_id, subset)
            for query in cases:
                fast = await R.sql_page(db, tenant_id, subset, query, answers)
                assert fast is not None, query
                slow_page, slow_meta = R._page(R.filter_entries(everything, query, answers), query)
                assert [e.response.id for e in fast[0]] == [e.response.id for e in slow_page], query
                assert fast[1] == slow_meta, query
                assert [R.service.row_of(e, answers) for e in fast[0]] == [R.service.row_of(e, answers)
                                                                           for e in slow_page], query
        # Searches, answer filters and the respondent sort need the answers: the in-memory path answers them
        for query in ({"q": "p3"}, {"sort": "respondent"}, {"filter[empty]": "email"}):
            assert await R.sql_page(db, tenant_id, [forms[0]], query, True) is None
