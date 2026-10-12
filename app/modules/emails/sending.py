"""Where a workspace's emails come from (Settings → Emails → Sending address; port of the mock's routes/emailSending.ts
and data/sendingStore.ts): Formalie's own address, the workspace's own address on a domain it verified with DNS
records, or its own mail server.

- Own domain: the records the mock lists (SPF include, two DKIM CNAMEs, the bounce CNAME, DMARC recommended), checked
  in real DNS (app/core/dns.py). Mail then goes through Formalie's relay with the workspace's address as From and
  `bounces@fm-bounces.{domain}` as the envelope sender; the relay signs it with the DKIM key behind fm1 / fm2.
- Own mail server: the password is Fernet-encrypted (MultiFernet) and never returned. The test connects for real
  (only to public addresses, app/core/outbound.py), reads the 220 greeting, says EHLO, starts TLS when asked, signs
  in, and checks the server takes the From address and a recipient (MAIL FROM / RCPT TO, then RSET: nothing is sent).
- A domain or server that stops working falls back to Formalie's address, and so does a plan without own addresses.
"""

from __future__ import annotations

import secrets
import smtplib
import socket
import ssl
import uuid
from datetime import UTC, datetime
from email.utils import parseaddr
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import dns, outbound
from app.core.config import get_settings
from app.core.security.fernet_tokens import decrypt_secret, encrypt_secret
from app.modules.billing.service import has_feature
from app.modules.emails.models import EmailSending

SMTP_TIMEOUT_S = 6.0


def iso(value: datetime | None = None) -> str:
    return (value or datetime.now(UTC)).astimezone(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def formalie_address() -> str:
    return parseaddr(get_settings().email_from)[1]


async def row_of(db: AsyncSession, tenant_id: uuid.UUID) -> EmailSending | None:
    return (await db.execute(select(EmailSending).where(EmailSending.tenant_id == tenant_id,
                                                        EmailSending.deleted_at.is_(None)))).scalar_one_or_none()


async def row_for_change(db: AsyncSession, tenant_id: uuid.UUID, organisation_id: uuid.UUID,
                         user_id: uuid.UUID | None) -> EmailSending:
    row = await row_of(db, tenant_id)
    if row is None:
        row = EmailSending(tenant_id=tenant_id, organisation_id=organisation_id, mode="formalie", created_by=user_id)
        db.add(row)
        await db.flush()
    return row


def settle(row: EmailSending) -> None:
    """Never keep sending from something that stopped working (the mock's updateSending)."""
    if row.mode == "domain" and (row.domain or {}).get("status") != "verified":
        row.mode = "formalie"
    if row.mode == "smtp" and (row.smtp or {}).get("status") != "working":
        row.mode = "formalie"


def from_address(row: EmailSending | None, plan_id: str | None) -> str:
    """The address the workspace's emails go out from right now."""
    if row is None or not has_feature(plan_id, "custom_email"):
        return formalie_address()
    if row.mode == "domain" and (row.domain or {}).get("status") == "verified":
        return str(row.domain["address"])  # type: ignore[index]
    if row.mode == "smtp" and (row.smtp or {}).get("status") == "working":
        return str(row.smtp["from_address"])  # type: ignore[index]
    return formalie_address()


def view(row: EmailSending | None, plan_id: str | None) -> dict[str, Any]:
    """EmailSending (shared/types/emails.ts); the DKIM key part and the password stay here."""
    domain = None
    if row is not None and row.domain:
        domain = {k: row.domain.get(k) for k in ("address", "domain", "status", "records", "added_at", "checked_at",
                                                 "problem")}
    return {"mode": row.mode if row is not None else "formalie", "from_address": from_address(row, plan_id),
            "formalie_address": formalie_address(), "domain": domain,
            "smtp": dict(row.smtp) if row is not None and row.smtp else None}


async def route_for(db: AsyncSession, tenant_id: uuid.UUID, plan_id: str | None) -> dict[str, Any] | None:
    """How a workspace email leaves (carried in the queued message, read by service.deliver): None = Formalie's
    address through Formalie's relay."""
    row = await row_of(db, tenant_id)
    if row is None or not has_feature(plan_id, "custom_email"):
        return None
    if row.mode == "domain" and (row.domain or {}).get("status") == "verified":
        return {"mode": "domain", "address": row.domain["address"], "domain": row.domain["domain"]}  # type: ignore[index]
    if row.mode == "smtp" and (row.smtp or {}).get("status") == "working":
        smtp = row.smtp or {}
        return {"mode": "smtp", "host": smtp["host"], "port": smtp["port"], "security": smtp["security"],
                "username": smtp.get("username"), "password_enc": row.smtp_password_enc,
                "from_address": smtp["from_address"]}
    return None


# ── Own domain ───────────────────────────────────────────────────────────────────

def blocked_domain(domain: str) -> bool:
    root = get_settings().root_domain
    return domain == root or domain.endswith(f".{root}") or domain == "formalie.com" or domain.endswith(".formalie.com")


def domain_records(domain: str, key: str | None = None) -> tuple[str, list[dict[str, Any]]]:
    """The DNS records to add (the mock's list), with a new random key for the DKIM targets."""
    settings = get_settings()
    key = key or secrets.token_hex(6)
    return key, [
        {"type": "TXT", "name": domain, "value": f"v=spf1 include:{settings.email_spf_include} ~all", "found": False},
        {"type": "CNAME", "name": f"fm1._domainkey.{domain}", "value": f"fm1.{key}.{settings.email_dkim_domain}",
         "found": False},
        {"type": "CNAME", "name": f"fm2._domainkey.{domain}", "value": f"fm2.{key}.{settings.email_dkim_domain}",
         "found": False},
        {"type": "CNAME", "name": f"fm-bounces.{domain}", "value": settings.email_bounces_host, "found": False},
        {"type": "TXT", "name": f"_dmarc.{domain}", "value": f"v=DMARC1; p=none; rua=mailto:dmarc@{domain}",
         "found": False, "optional": True},
    ]


async def check_records(records: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], str | None]:
    """Looks every record up (the mock's checkSendingDomain) → (records with `found`, problem or None)."""
    include = f"include:{get_settings().email_spf_include}"
    checked = [dict(r) for r in records]
    wrong = False
    try:
        for record in checked:
            if record["type"] == "CNAME":
                targets = [dns.clean(t) for t in await dns.lookup(record["name"], "CNAME")]
                record["found"] = record["value"] in targets
                wrong = wrong or (bool(targets) and not record["found"])
            else:
                texts = await dns.lookup(record["name"], "TXT")
                spf = [t for t in texts if t.startswith("v=spf1")]
                if record["value"].startswith("v=spf1"):
                    # Any SPF record that includes Formalie's (people merge it into the one they have)
                    record["found"] = any(include in t for t in spf)
                    wrong = wrong or (bool(spf) and not record["found"])
                elif record["value"].startswith("v=DMARC1"):
                    record["found"] = any(t.startswith("v=DMARC1") for t in texts)
                else:
                    record["found"] = record["value"] in texts
        missing = [r for r in checked if not r.get("optional") and not r["found"]]
        problem = ("wrong_value" if wrong else "not_found") if missing else None
    except dns.DnsError:
        problem = "dns_error"
    return checked, problem


# ── Own mail server ──────────────────────────────────────────────────────────────

def encrypt_password(value: str | None) -> str | None:
    return encrypt_secret(value) if value else None


def password_of(value: str | None) -> str | None:
    return decrypt_secret(value) if value else None


class _PinnedSMTP(smtplib.SMTP):
    """Connects to the checked address; the name stays the server's for EHLO and the TLS certificate."""

    def __init__(self, address: str, timeout: float) -> None:
        self._address = address
        super().__init__(timeout=timeout)

    def _get_socket(self, host: str, port: int, timeout: float) -> socket.socket:
        return socket.create_connection((self._address, port), timeout)


class _PinnedSMTPS(smtplib.SMTP_SSL):
    def __init__(self, address: str, timeout: float) -> None:
        self._address = address
        super().__init__(timeout=timeout, context=ssl.create_default_context())

    def _get_socket(self, host: str, port: int, timeout: float) -> socket.socket:
        raw = socket.create_connection((self._address, port), timeout)
        return self.context.wrap_socket(raw, server_hostname=self._host)


def resolve_now(host: str, port: int) -> str:
    """The public address of a mail server, checked like outbound.public_address (worker side, no event loop)."""
    allow = outbound.local_allowed(get_settings().email_smtp_allow_local)
    name = host.strip().strip("[]").rstrip(".")
    try:
        addresses = [str(info[4][0]) for info in socket.getaddrinfo(name, port, type=socket.SOCK_STREAM)]
    except (socket.gaierror, UnicodeError):
        raise outbound.Unresolved(host) from None
    if not addresses:
        raise outbound.Unresolved(host)
    if not allow and any(outbound.blocked(a) for a in addresses):
        raise outbound.Refused(host)
    return addresses[0]


def open_server(address: str, host: str, port: int, security: str, username: str | None,
                password: str | None, timeout: float = SMTP_TIMEOUT_S) -> smtplib.SMTP:
    """Connected, greeted, TLS as asked and signed in. Raises smtplib / OS errors."""
    client: smtplib.SMTP = _PinnedSMTPS(address, timeout) if security == "tls" else _PinnedSMTP(address, timeout)
    code, _ = client.connect(host, port)
    if code != 220:
        client.close()
        raise smtplib.SMTPConnectError(code, b"not smtp")
    client.ehlo()
    if security == "starttls":
        client.starttls(context=ssl.create_default_context())
        client.ehlo()
    if username and password:
        client.login(username, password)
    return client


def probe(address: str, host: str, port: int, security: str, username: str | None, password: str | None,
          from_address: str, to: str) -> str | None:
    """The real test (blocking: run it in a thread) → problem or None."""
    try:
        client = open_server(address, host, port, security, username, password)
    except smtplib.SMTPAuthenticationError:
        return "auth_failed"
    except (TimeoutError, socket.timeout):
        return "timeout"
    except smtplib.SMTPServerDisconnected as error:
        # smtplib turns a read that timed out into "Connection unexpectedly closed: timed out"
        return "timeout" if "timed out" in str(error) else "not_smtp"
    except (smtplib.SMTPConnectError, smtplib.SMTPResponseException,
            smtplib.SMTPNotSupportedError, UnicodeError):
        return "not_smtp"
    except (ssl.SSLError, OSError):
        return "unreachable"
    try:
        code, _ = client.mail(from_address)
        if code >= 400:
            return "sender_refused"
        code, _ = client.rcpt(to)
        if code >= 400:
            return "sender_refused"
        client.rset()
        return None
    except (TimeoutError, socket.timeout):
        return "timeout"
    except (smtplib.SMTPException, OSError):
        return "not_smtp"
    finally:
        try:
            client.quit()
        except (smtplib.SMTPException, OSError):
            client.close()
