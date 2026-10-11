"""Who may open a form (mock: data/formAccess.ts; decisions 92 and 96), one mechanism for every access mode:

    public        everyone
    password      after the right password
    invite        with a personal invitation link (one person, one response)
    organisation  signed-in members of the workspace (a 2-minute sign-in pass from the portal)

Passes and unlock values are Fernet tokens (encrypted, authenticated, time-limited) instead of the mock's HMAC
strings. An unlock is bound to the form's access version (mode + password version), so changing the mode or the
password locks everyone out; a revoked invitation or a disabled member is checked on every use.
"""

from __future__ import annotations

import hashlib
import secrets
import uuid
from typing import Any

from app.core.security.fernet_tokens import make_token, read_token
from app.modules.forms.models import Form

PASS_TTL_S = 120
UNLOCK_TTL_S = 12 * 3600


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def new_invite_token() -> str:
    return secrets.token_urlsafe(24)


def access_version(form: Form) -> str:
    return f"{form.access}:{form.password_version}"


# ── Sign-in passes (organisation-only forms) ────────────────────────────────────

def issue_pass(form: Form, user_id: uuid.UUID) -> str:
    return make_token({"t": "form_pass", "f": str(form.id), "u": str(user_id)})


def read_pass(form: Form, value: str) -> uuid.UUID | None:
    """The member behind a pass for this form (checked again against People by the caller)."""
    data = read_token(value, PASS_TTL_S)
    if not data or data.get("t") != "form_pass" or data.get("f") != str(form.id):
        return None
    try:
        return uuid.UUID(data["u"])
    except (KeyError, ValueError):
        return None


# ── Unlocks (`who` = pw | inv~{id} | usr~{id}) ──────────────────────────────────

def unlock_value(form: Form, who: str) -> str:
    return make_token({"t": "unlock", "f": str(form.id), "v": access_version(form), "w": who})


def read_unlock(form: Form, value: str | None) -> tuple[str, str | None] | None:
    """(kind, id) behind an unlock value still valid for this form's access version, else None."""
    data: dict[str, Any] | None = read_token(value or "", UNLOCK_TTL_S)
    if not data or data.get("t") != "unlock" or data.get("f") != str(form.id) or data.get("v") != access_version(form):
        return None
    kind, _, ref = str(data.get("w", "")).partition("~")
    return kind, ref or None
