"""Development only: play the platform admin's part of Formalie support access (B16) against the local backend, so
the portal's support screens can be tried without formaliePlatformFront.

    fmly\\Scripts\\python.exe scripts\\dev_support_ticket.py request                 # Formalie asks remedylegal for access
    fmly\\Scripts\\python.exe scripts\\dev_support_ticket.py request --mode write --hours 1 --reason "Fix the export"
    fmly\\Scripts\\python.exe scripts\\dev_support_ticket.py session                 # a one-time link into remedylegal
    fmly\\Scripts\\python.exe scripts\\dev_support_ticket.py session --mode write --subdomain samathtax

`request` calls POST /internal/admin/v1/support-access/requests: the workspace's admins get a notice and see the
request in Settings -> Security -> Formalie support access (Approve / Decline).
`session` needs access that is on (turned on there, or a request approved) and calls
POST /internal/admin/v1/support-access/{grant_id}/session; it prints the redeem link (/support#ticket=...), which
works once, within SUPPORT_TICKET_SECONDS (2 minutes). Open it in a browser where nobody else is signed in to that
workspace (a private window), or on localhost with ?tenant=: https://localhost:2202/support?tenant=remedylegal#ticket=...

Every call is signed exactly like the platform admin's (app/modules/platform_bridge/signing.py) with the first key in
PLATFORM_ADMIN_KEYS ("key_id:secret", secret at least 32 characters). When it is empty, add one to .env, e.g.
    PLATFORM_ADMIN_KEYS=dev:<python -c "import secrets; print(secrets.token_urlsafe(32))">
and restart the backend (scripts\\dev-up.ps1 -Restart). The workspace and its open grant are looked up in the
development database as formalie_owner (DB_OWNER_URL). Refuses to run unless APP_ENV is development.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import uuid
from pathlib import Path
from urllib.parse import quote

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import httpx  # noqa: E402
from sqlalchemy import text  # noqa: E402
from sqlalchemy.ext.asyncio import create_async_engine  # noqa: E402

from app.core.config import get_settings  # noqa: E402
from app.core.db.engines import async_url  # noqa: E402
from app.modules.platform_bridge import signing  # noqa: E402

PREFIX = "/internal/admin/v1"
STAFF_ID = "dev-script"


async def lookup(subdomain: str) -> tuple[uuid.UUID, uuid.UUID | None]:
    """The workspace's id and its open grant (if any), read as formalie_owner."""
    settings = get_settings()
    if settings.db_owner_url is None:
        raise SystemExit("DB_OWNER_URL is not set")
    engine = create_async_engine(async_url(settings.db_owner_url.get_secret_value()))
    try:
        async with engine.connect() as conn:
            tenant = (await conn.execute(text("SELECT id FROM tenants WHERE subdomain = :s AND deleted_at IS NULL"),
                                         {"s": subdomain})).scalar_one_or_none()
            if tenant is None:
                raise SystemExit(f"No workspace '{subdomain}' in the development database")
            grant = (await conn.execute(text(
                "SELECT id FROM support_access_grants WHERE tenant_id = :t AND deleted_at IS NULL AND revoked_at IS NULL "
                "AND expires_at > now() ORDER BY created_at DESC LIMIT 1"), {"t": tenant})).scalar_one_or_none()
    finally:
        await engine.dispose()
    return tenant, grant


def call(base: str, path: str, payload: dict[str, object], staff_name: str, reason: str, verify: bool | str) -> dict:
    settings = get_settings()
    keys = signing.keys_of([k.get_secret_value() for k in settings.platform_admin_keys])
    if not keys:
        raise SystemExit("PLATFORM_ADMIN_KEYS is empty: add one to .env and restart the backend (see the top of this script)")
    key_id, secret = next(iter(keys.items()))
    body = json.dumps(payload).encode()
    extra = {"X-Platform-Staff-Id": STAFF_ID, "X-Platform-Staff-Name": quote(staff_name, safe=""),
             "X-Platform-Reason": quote(reason, safe=""), "Idempotency-Key": f"dev-{uuid.uuid4().hex}"}
    headers = signing.sign_headers(key_id, secret, "POST", PREFIX + path, body, extra)
    response = httpx.post(base.rstrip("/") + PREFIX + path, content=body,
                          headers={**headers, "Content-Type": "application/json"}, verify=verify, timeout=20)
    try:
        answer = response.json()
    except ValueError:
        raise SystemExit(f"{response.status_code}: {response.text[:300]}") from None
    if response.status_code >= 400 or answer.get("success") is False:
        raise SystemExit(f"{response.status_code}: {json.dumps(answer.get('error', answer), indent=2)}")
    return answer.get("data", answer)


def main() -> None:
    settings = get_settings()
    if not settings.is_development or settings.is_production:
        raise SystemExit("Development only (APP_ENV must be development)")
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("action", choices=["request", "session"])
    parser.add_argument("--subdomain", default="remedylegal")
    parser.add_argument("--mode", choices=["read", "write"], default="read")
    parser.add_argument("--hours", type=int, choices=[1, 24, 168], default=24, help="request only")
    parser.add_argument("--staff", default="Alex Morgan", help="the staff member's name the workspace sees")
    parser.add_argument("--reason", default="You asked us to look at a form that does not send its emails.")
    parser.add_argument("--api", default=f"https://{settings.root_domain}:{settings.server_port}",
                        help="the backend's own address (default https://formalie.dev:5004)")
    parser.add_argument("--insecure", action="store_true", help="skip TLS verification of the dev certificate")
    args = parser.parse_args()
    # The dev certificate's root (mkcert) is in NODE_EXTRA_CA_CERTS for the Nuxt proxy; use it here too
    verify: bool | str = False if args.insecure else (os.environ.get("NODE_EXTRA_CA_CERTS") or True)

    tenant, grant = asyncio.run(lookup(args.subdomain))
    if args.action == "request":
        data = call(args.api, "/support-access/requests",
                    {"tenant_id": str(tenant), "reason": args.reason, "mode": args.mode, "hours": args.hours},
                    args.staff, args.reason, verify)
        print(f"Asked {args.subdomain} for {args.mode} access for {args.hours}h (request {data.get('request_id')}).")
        print("Approve or decline it in Settings -> Security -> Formalie support access, then run: ... session")
        return
    if grant is None:
        raise SystemExit(f"Support access is off in {args.subdomain}: turn it on (or approve a request) in Settings -> "
                         "Security -> Formalie support access first")
    data = call(args.api, f"/support-access/{grant}/session", {"mode": args.mode}, args.staff,
                "Development test of the support view", verify)
    print(f"Support session {data['session_id']} ({data['mode']}), ends {data['ends_at']}.")
    print(f"Open within 2 minutes, once:\n  {data['redeem_url']}")
    print(f"  or https://localhost:2202/support?tenant={args.subdomain}#ticket={data['ticket']}")


if __name__ == "__main__":
    main()
