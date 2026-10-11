"""Development seed: the same workspaces and accounts as the frontend's mock (server/mock/data/tenants.ts), so the
frontend's flows work unchanged against this backend. Safe to run again (existing workspaces are skipped).

    fmly\\Scripts\\python.exe scripts\\seed_dev.py            # the development database
    fmly\\Scripts\\python.exe scripts\\seed_dev.py --test     # the test database
    fmly\\Scripts\\python.exe scripts\\seed_dev.py --person you@gmail.com   # try social sign-in (below)

--person adds that address as an Admin of Remedy Legal (no password) and switches on Google, Microsoft and
Facebook there, so you can sign in with your own Google, Microsoft or Facebook account. Development only.

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
     "status": "active", "plan": "business", "methods": ["password", "google", "microsoft"]},
    {"id": U("7a1f3b25-4d3c-4e66-8b10-2c3d4e5f6071"), "org": U("1b2c3d4e-5f60-4b7c-9d8e-0f1a2b3c4d5e"),
     "name": "Samath Tax", "subdomain": "samathtax", "website": "https://www.samathtax.example",
     "status": "active", "plan": "starter", "methods": ["password", "google", "facebook"]},
    {"id": U("8b2a4c36-5e4d-4f77-9c21-3d4e5f607182"), "org": U("2c3d4e5f-6071-4c8d-8e9f-1a2b3c4d5e6f"),
     "name": "Old Co", "subdomain": "oldco", "website": None, "status": "suspended", "plan": "starter",
     "methods": ["password"]},
    # Formalie's own workspace: its forms collect our data (support, enquiries). Nobody signs in to it.
    {"id": U("f0a1b2c3-0000-4f00-8f00-00000000f0f0"), "org": U("f0a1b2c3-0000-4f00-8f00-00000000f0f1"),
     "name": "Formalie", "subdomain": "formalie-team", "website": "https://formalie.com", "status": "active",
     "plan": "starter", "methods": ["password"]},
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
                    print(f"  {ws['subdomain']}: already there")
                    continue
                people = [u for u in USERS if u[1] == ws["subdomain"]]
                founder_row = people[0] if people else None
                founder = Founder(founder_row[2], founder_row[3], founder_row[4], password_hash) if founder_row else None
                await create_workspace(session, name=ws["name"], subdomain=ws["subdomain"], founder=founder,
                                       plan_id=ws["plan"], signin_methods=ws["methods"], website=ws["website"],
                                       tenant_id=ws["id"], organisation_id=ws["org"],
                                       owner_id=founder_row[0] if founder_row else None)
                if founder_row and founder_row[5]:
                    await session.execute(text("UPDATE users SET phone = :p WHERE id = :id"),
                                          {"p": founder_row[5], "id": founder_row[0]})
                member = await role_by_key(session, "member")
                now = datetime.now(UTC)
                for uid, _, first, last, email, phone, _role, status in people[1:]:
                    session.add(User(id=uid, tenant_id=ws["id"], organisation_id=ws["org"], email=email, first_name=first,
                                     last_name=last, phone=phone, status=status, role_id=member.id,  # type: ignore[union-attr]
                                     password_hash=password_hash, password_changed_at=now, joined_at=now))
                if ws["status"] != "active":
                    await session.execute(text("UPDATE platform.tenants SET status = :s WHERE id = :id"),
                                          {"s": ws["status"], "id": ws["id"]})
                print(f"  {ws['subdomain']}: created ({len(people)} people, plan {ws['plan']}, {ws['status']})")
    finally:
        await engine.dispose()


async def add_person(database: str, email: str) -> None:
    """Your own address as an Admin of Remedy Legal, with every social sign-in method switched on there."""
    settings = get_settings()
    if settings.is_production:
        raise SystemExit("Refusing to seed test accounts in production.")
    ws = WORKSPACES[0]
    url = make_url(async_url(settings.db_owner_url.get_secret_value())).set(database=database)  # type: ignore[union-attr]
    engine = create_async_engine(url.render_as_string(hide_password=False))
    try:
        async with AsyncSession(engine, expire_on_commit=False) as session, session.begin():
            await set_rls_context(session, ws["id"], ws["org"], None)
            await session.execute(text(
                "UPDATE workspace_settings SET value = jsonb_set(value, '{methods}', "
                "'[\"password\", \"google\", \"microsoft\", \"facebook\"]'::jsonb), updated_at = now() "
                "WHERE section = 'signin'"))
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
