"""Development seed: the same workspaces and accounts as the frontend's mock (server/mock/data/tenants.ts), so the
frontend's flows work unchanged against this backend. Safe to run again (existing workspaces are skipped).

    fmly\\Scripts\\python.exe scripts\\seed_dev.py            # the development database
    fmly\\Scripts\\python.exe scripts\\seed_dev.py --test     # the test database
    fmly\\Scripts\\python.exe scripts\\seed_dev.py --person you@gmail.com   # try social sign-in (below)

--person adds that address as an Admin of Remedy Legal (no password), so you can sign in there with your own Google
or Facebook account (every workspace offers both, owner 2026-10-12). Development only.

Every seeded account signs in with the mock's test password (MOCK_PASSWORD in the mock's data/tenants.ts); codes
arrive in Mailpit (http://127.0.0.1:8025). Never run against production: it refuses when APP_ENV=production.
"""

from __future__ import annotations

import asyncio
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import text  # noqa: E402
from sqlalchemy.engine import make_url  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine  # noqa: E402

from app.core.config import get_settings  # noqa: E402
from app.core.db.engines import async_url  # noqa: E402
from app.core.db.session import set_rls_context  # noqa: E402
from app.core.ids import uuid7  # noqa: E402
from app.core.security.passwords import hash_password  # noqa: E402
from app.modules.rbac.service import role_by_key  # noqa: E402
from app.modules.tenants.workspace import Founder, create_workspace  # noqa: E402
from app.modules.users.models import User  # noqa: E402

MOCK_PASSWORD = "Formalie!2026"  # the mock's test password (data/tenants.ts); test accounts only

U = uuid.UUID
WORKSPACES = [
    {"id": U("6f0e2a14-3c2b-4d55-9a0f-1b2c3d4e5f60"), "org": U("0a1b2c3d-4e5f-4a6b-8c7d-9e0f1a2b3c4d"),
     "name": "Remedy Legal", "subdomain": "remedylegal", "website": "https://www.remedylegal.example",
     "status": "active", "plan": "business"},
    {"id": U("7a1f3b25-4d3c-4e66-8b10-2c3d4e5f6071"), "org": U("1b2c3d4e-5f60-4b7c-9d8e-0f1a2b3c4d5e"),
     "name": "Samath Tax", "subdomain": "samathtax", "website": "https://www.samathtax.example",
     "status": "active", "plan": "starter"},
    {"id": U("8b2a4c36-5e4d-4f77-9c21-3d4e5f607182"), "org": U("2c3d4e5f-6071-4c8d-8e9f-1a2b3c4d5e6f"),
     "name": "Old Co", "subdomain": "oldco", "website": None, "status": "suspended", "plan": "starter"},
    # Formalie's own workspace: its forms collect our data (support, enquiries). Nobody signs in to it.
    {"id": U("f0a1b2c3-0000-4f00-8f00-00000000f0f0"), "org": U("f0a1b2c3-0000-4f00-8f00-00000000f0f1"),
     "name": "Formalie", "subdomain": "formalie-team", "website": "https://formalie.com", "status": "active",
     "plan": "starter"},
]
# (id, workspace, first, last, email, phone, role, status); the first of each workspace is its founder (owner)
USERS = [
    (U("a1b2c3d4-0001-4000-8000-000000000001"), "remedylegal", "Frankie", "Don", "admin@remedylegal.test", "+447700900001", "owner", "active"),
    (U("a1b2c3d4-0005-4000-8000-000000000005"), "remedylegal", "James", "Carter", "james.carter@carterpartners.test", None, "member", "active"),
    (U("a1b2c3d4-0004-4000-8000-000000000004"), "remedylegal", "Marcus", "Reid", "marcus.reid@remedylegal.test", None, "member", "disabled"),
    (U("a1b2c3d4-0006-4000-8000-000000000006"), "remedylegal", "Lena", "Novak", "staff@remedylegal.test", None, "member", "active"),
    (U("a1b2c3d4-0002-4000-8000-000000000002"), "samathtax", "Elena", "Rossi", "admin@samathtax.test", None, "owner", "active"),
    (U("a1b2c3d4-0003-4000-8000-000000000003"), "samathtax", "James", "Carter", "james.carter@carterpartners.test", None, "member", "active"),
]


# The mock's sample organisation data (data/orgStore.ts seed): everyone in one department, the last two empty
ORG_SAMPLES = ("remedylegal", "samathtax")  # the mock's seeded workspaces with people
DEPARTMENTS = ["Finance", "Operations", "People", "Sales", "Support", "Technology", "Legal", "Compliance"]
JOB_TITLES = ["Manager", "Team lead", "Specialist", "Coordinator", "Analyst", "Assistant"]


async def seed_org(session: AsyncSession, ws: dict) -> int:
    """Departments and job titles with their people, once (skipped when the workspace has any)."""
    from app.modules.org.models import OrgUnit, OrgUnitMember

    await set_rls_context(session, ws["id"], ws["org"], None)
    if (await session.execute(text("SELECT 1 FROM org_units LIMIT 1"))).first():
        return 0
    people = [u[0] for u in USERS if u[1] == ws["subdomain"] and u[7] != "disabled"]

    def add(kind: str, name: str, members: list[uuid.UUID]) -> None:
        unit = OrgUnit(id=uuid7(), tenant_id=ws["id"], organisation_id=ws["org"], kind=kind, name=name)
        session.add(unit)
        for member in members:
            session.add(OrgUnitMember(tenant_id=ws["id"], organisation_id=ws["org"], org_unit_id=unit.id, user_id=member))

    for i, name in enumerate(DEPARTMENTS):
        add("departments", name, [p for n, p in enumerate(people) if n % 6 == i] if i < 6 else [])
    for i, name in enumerate(JOB_TITLES):
        add("job_titles", name, [p for n, p in enumerate(people) if n % len(JOB_TITLES) == i])
    await session.flush()
    return len(DEPARTMENTS) + len(JOB_TITLES)


async def seed_lists(session: AsyncSession, ws: dict) -> int:
    """Formalie's sample lists (the mock gives them to every seeded workspace)."""
    from app.modules.lists.samples import seed_sample_lists

    await set_rls_context(session, ws["id"], ws["org"], None)
    return await seed_sample_lists(session, ws["id"], ws["org"])


async def seed_api(session: AsyncSession, ws: dict) -> int:
    """The mock's sample API service (data/apiStore.ts), sample webhooks with a month of deliveries
    (integrationStore.ts) and 60 days of sample traffic (apiTraffic.ts), each once; endpoints on published forms."""
    from app.modules.api_service.samples import seed_api_samples

    await set_rls_context(session, ws["id"], ws["org"], None)
    from app.modules.api_service.traffic_samples import seed_sample_traffic
    from app.modules.webhooks.samples import seed_sample_webhooks

    owner = next((u[0] for u in USERS if u[1] == ws["subdomain"]), None)
    added = await seed_api_samples(session, ws["id"], ws["org"], owner)
    added += await seed_sample_webhooks(session, ws["id"], ws["org"], owner)
    calls = await seed_sample_traffic(session, ws["id"], ws["org"])
    return added + (1 if calls else 0)


async def seed(database: str) -> None:
    settings = get_settings()
    if settings.is_production:
        raise SystemExit("Refusing to seed test accounts in production.")
    url = make_url(async_url(settings.db_owner_url.get_secret_value())).set(database=database)  # type: ignore[union-attr]
    engine = create_async_engine(url.render_as_string(hide_password=False))
    password_hash = hash_password(MOCK_PASSWORD)
    try:
        for ws in WORKSPACES:
            async with AsyncSession(engine, expire_on_commit=False) as session, session.begin():
                exists = (await session.execute(text("SELECT 1 FROM platform.tenants WHERE id = :id"), {"id": ws["id"]})).first()
                if exists:
                    added = await seed_org(session, ws) if ws["subdomain"] in ORG_SAMPLES else 0
                    lists = await seed_lists(session, ws)
                    api = await seed_api(session, ws)
                    extra = [f"{added} departments and job titles"] * bool(added) + [f"{lists} sample lists"] * bool(lists)                         + [f"{api} API service samples"] * bool(api)
                    print(f"  {ws['subdomain']}: already there" + (f" (added {', '.join(extra)})" if extra else ""))
                    continue
                people = [u for u in USERS if u[1] == ws["subdomain"]]
                founder_row = people[0] if people else None
                founder = Founder(founder_row[2], founder_row[3], founder_row[4], password_hash) if founder_row else None
                await create_workspace(session, name=ws["name"], subdomain=ws["subdomain"], founder=founder,
                                       plan_id=ws["plan"], website=ws["website"],
                                       tenant_id=ws["id"], organisation_id=ws["org"],
                                       owner_id=founder_row[0] if founder_row else None, onboarding=False)
                if founder_row and founder_row[5]:
                    await session.execute(text("UPDATE users SET phone = :p WHERE id = :id"),
                                          {"p": founder_row[5], "id": founder_row[0]})
                member = await role_by_key(session, "member")
                now = datetime.now(UTC)
                for uid, _, first, last, email, phone, _role, status in people[1:]:
                    session.add(User(id=uid, tenant_id=ws["id"], organisation_id=ws["org"], email=email, first_name=first,
                                     last_name=last, phone=phone, status=status, role_id=member.id,  # type: ignore[union-attr]
                                     password_hash=password_hash, password_changed_at=now, joined_at=now))
                if ws["subdomain"] in ORG_SAMPLES:
                    await seed_org(session, ws)
                await seed_lists(session, ws)
                await seed_api(session, ws)
                if ws["status"] != "active":
                    await session.execute(text("UPDATE platform.tenants SET status = :s WHERE id = :id"),
                                          {"s": ws["status"], "id": ws["id"]})
                print(f"  {ws['subdomain']}: created ({len(people)} people, plan {ws['plan']}, {ws['status']})")
    finally:
        await engine.dispose()


async def add_person(database: str, email: str) -> None:
    """Your own address as an Admin of Remedy Legal (signs in with Google or Facebook)."""
    settings = get_settings()
    if settings.is_production:
        raise SystemExit("Refusing to seed test accounts in production.")
    ws = WORKSPACES[0]
    url = make_url(async_url(settings.db_owner_url.get_secret_value())).set(database=database)  # type: ignore[union-attr]
    engine = create_async_engine(url.render_as_string(hide_password=False))
    try:
        async with AsyncSession(engine, expire_on_commit=False) as session, session.begin():
            await set_rls_context(session, ws["id"], ws["org"], None)
            known = (await session.execute(text("SELECT 1 FROM users WHERE lower(email) = :e AND deleted_at IS NULL"),
                                           {"e": email})).first()
            if known:
                print(f"  {email}: already in Remedy Legal")
            else:
                admin = await role_by_key(session, "admin")
                now = datetime.now(UTC)
                session.add(User(id=uuid7(), tenant_id=ws["id"], organisation_id=ws["org"], email=email,
                                 first_name=email.split("@")[0][:60], last_name="", status="active",
                                 role_id=admin.id, joined_at=now))  # type: ignore[union-attr]
                print(f"  {email}: added to Remedy Legal as an Admin")
    finally:
        await engine.dispose()


def main() -> None:
    settings = get_settings()
    database = settings.db_test_database if "--test" in sys.argv else make_url(
        settings.db_owner_url.get_secret_value()).database  # type: ignore[union-attr]
    print(f"Seeding {database}")
    asyncio.run(seed(database or "formalie"))
    if "--person" in sys.argv:
        email = sys.argv[sys.argv.index("--person") + 1].strip().lower()
        asyncio.run(add_person(database or "formalie", email))
    print("Done. Sign in on https://remedylegal.formalie.dev:2202 with admin@remedylegal.test (codes in Mailpit).")


if __name__ == "__main__":
    main()
