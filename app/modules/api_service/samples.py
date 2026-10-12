"""The mock's sample API service (data/apiStore.ts: seed services, endpoints, tokens and rules) for the seeded
development workspaces only (scripts/seed_dev.py), so the portal's screens look the same against this backend. Run
once per workspace: skipped when it has ever had an API service. Values stay international and neutral.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security.fernet_tokens import encrypt_secret
from app.modules.api_service import tokens as T
from app.modules.api_service.endpoints import endpoint_fields_of, endpoint_name_from
from app.modules.api_service.models import ApiAccessRule, ApiEndpoint, ApiService, ApiToken
from app.modules.api_service.service import ensure_settings
from app.modules.forms.models import Form, FormVersion

SERVICES = [
    ("Customer onboarding", "Sign-ups and account requests from the website and the mobile app.", "active"),
    ("Partner bookings", "Bookings that partner systems send in and read back.", "active"),
    ("Internal tools", "Back-office scripts; switched off while they are rebuilt.", "disabled"),
]
METHODS = [["POST"], ["GET", "POST", "PUT"], ["GET", "POST", "PUT", "DELETE"], ["GET"], ["POST", "GET"]]


async def seed_api_samples(session: AsyncSession, tenant_id: uuid.UUID, organisation_id: uuid.UUID,
                           owner_id: uuid.UUID | None) -> int:
    """Inside the workspace's RLS context. Returns how many items were added (0 when it already has some)."""
    await ensure_settings(session, tenant_id, organisation_id)
    if (await session.execute(select(ApiService.id).where(ApiService.tenant_id == tenant_id).limit(1))).first():
        return 0
    now = datetime.now(UTC)
    day = timedelta(days=1)
    base = {"tenant_id": tenant_id, "organisation_id": organisation_id, "created_by": owner_id, "updated_by": owner_id}
    services = []
    for i, (name, description, status) in enumerate(SERVICES):
        created = now - (150 - i * 10) * day
        services.append(ApiService(name=name, description=description, status=status, allowed_origins=[],
                                   created_at=created, updated_at=created + 2 * day, **base))
    session.add_all(services)
    await session.flush()

    # Endpoints on the workspace's first five published forms
    forms = list((await session.execute(select(Form).where(
        Form.tenant_id == tenant_id, Form.deleted_at.is_(None), Form.status == "published",
        Form.published_version_id.is_not(None)).order_by(Form.created_at).limit(5))).scalars())
    taken: set[str] = set()
    endpoints = 0
    for i, form in enumerate(forms):
        schema = (await session.execute(select(FormVersion.schema).where(
            FormVersion.tenant_id == tenant_id, FormVersion.id == form.published_version_id))).scalar_one_or_none()
        name = endpoint_name_from(form.name) or f"form-{i + 1}"
        name = name if len(name) >= 3 else f"form-{i + 1}"
        stem, n = name, 2
        while name in taken:
            name, n = f"{stem[:60]}-{n}", n + 1
        taken.add(name)
        created = now - (120 - i * 15) * day
        fields = [{k: f[k] for k in ("key", "name", "accept", "required", "returned", "filter")}
                  for f in endpoint_fields_of(schema)] if schema else []
        session.add(ApiEndpoint(service_id=services[0 if i < 2 else 1 if i < 4 else 2].id, name=name, description=None,
                                form_id=form.id, version=None, methods=METHODS[i % len(METHODS)], fields=fields, page_size=50,
                                headers=[], status="active", created_at=created, updated_at=created + day, **base))
        endpoints += 1

    # A live website token, a test partner client, an expiring and a revoked one
    def token(index: int, name: str, kind: str, mode: str, **extra: object) -> ApiToken:
        secret = T.new_secret(kind, mode)
        values = {"scopes": {"services": [], "endpoints": [], "methods": []}, "expires_at": None, "revoked_at": None,
                  "last_used_at": now - (index + 1) * timedelta(milliseconds=3_100_000), **extra}
        return ApiToken(name=name, kind=kind, mode=mode, secret_hash=T.hash_secret(secret), secret_enc=encrypt_secret(secret),
                        preview=T.secret_preview(secret), client_id=T.new_secret("client_id", mode) if kind == "client" else None,
                        lifetime_minutes=15 if kind == "client" else None, signing=False,
                        created_at=now - (100 - index * 18) * day, **values, **base)  # type: ignore[arg-type]

    first, second = str(services[0].id), str(services[1].id)
    session.add_all([
        token(0, "Website sign-ups", "static", "live", scopes={"services": [first], "endpoints": [], "methods": ["POST"]}),
        token(1, "Partner sandbox", "client", "test", scopes={"services": [second], "endpoints": [], "methods": []}),
        token(2, "Mobile app", "static", "live", expires_at=now + 9 * day),
        token(3, "Old import script", "static", "live", revoked_at=now - 20 * day, last_used_at=now - 24 * day),
    ])

    # Sample rules that never get in the way of testing: blocks on documentation addresses, a website-only rule off
    session.add_all([
        ApiAccessRule(action="block", kind="ip", values=["192.0.2.66", "198.51.100.0/28"], scope_type="all", scope_id=None,
                      note="Seen scraping; blocked everywhere.", enabled=True, last_hit_at=now - 0.2 * day,
                      created_at=now - 40 * day, updated_at=now - 40 * day, **base),
        ApiAccessRule(action="block", kind="domain", values=["*.spam-example.net"], scope_type="all", scope_id=None, note=None,
                      enabled=True, last_hit_at=now - 2 * day, created_at=now - 25 * day, updated_at=now - 25 * day, **base),
        ApiAccessRule(action="allow", kind="domain", values=["example.com", "*.example.com"], scope_type="service",
                      scope_id=services[0].id, note="Website only: switch on when the new site is live.", enabled=False,
                      created_at=now - 10 * day, updated_at=now - 10 * day, **base),
    ])
    await session.flush()
    return len(services) + endpoints + 4 + 3
