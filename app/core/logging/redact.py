"""Redaction for everything that is logged (B17 review M8, M9): secrets found by their value, and tokens in URL paths.

Pure functions, no I/O, no app imports, so the JSON log formatter, the request log and the API service log share them.

- `redact_text` replaces values that look like a secret whatever their field is called: Fernet tokens (access,
  refresh, tickets), JWTs, Formalie's own secrets (`formalie_live_…`, `formalie_secret_…`, `formalie_hook_…` …),
  bearer / basic credentials, passwords inside connection URLs and PEM private keys.
- `mask_path` replaces path parameters that are a credential (`{token}`, `{code}`, `{ticket}` …) with `***`, using
  the matched route template when there is one, else the known token-bearing addresses.
"""

from __future__ import annotations

import re

MASK = "***"

# Values that are a secret whatever field they sit in
_SECRET_VALUES = re.compile(
    r"gAAAAA[A-Za-z0-9_\-]{40,}={0,2}"  # Fernet tokens (access, refresh, tickets, invites)
    r"|eyJ[A-Za-z0-9_\-]{8,}\.[A-Za-z0-9_\-]{8,}\.[A-Za-z0-9_\-]*"  # JWTs (id tokens, SSO assertions)
    r"|formalie_(?:[a-z]+_)?(?:live|test)_[A-Za-z0-9]{8,}"  # Formalie's own secrets and tokens (api_service/tokens.py prefixes)
    r"|-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]*?(?:-----END [A-Z ]*PRIVATE KEY-----|$)"
)
# Credentials with a scheme word in front: `Bearer abc…`, `Basic dXNl…`
_SCHEMED = re.compile(r"\b(Bearer|bearer|BEARER|Basic)\s+[A-Za-z0-9._~+/=\-]{8,}")
# user:password@ in a connection URL (postgresql://, mysql://, https:// …)
_URL_PASSWORD = re.compile(r"(\b[a-z][a-z0-9+.\-]*://[^/\s:@]*:)[^@/\s]+@", re.IGNORECASE)


def redact_text(value: str) -> str:
    """The string with every secret-looking value replaced by `***` (the rest kept)."""
    if len(value) < 8:
        return value
    out = _SECRET_VALUES.sub(MASK, value)
    out = _SCHEMED.sub(lambda m: f"{m.group(1)} {MASK}", out)
    return _URL_PASSWORD.sub(lambda m: f"{m.group(1)}{MASK}@", out)


# ── Tokens in URL paths ──────────────────────────────────────────────────────────

# Path parameters that are a credential (a pending invite, a resume draft, a file or export link, a short code)
SECRET_PATH_PARAMS = frozenset({"token", "code", "ticket", "secret", "signature", "otp"})
# Without a matched route (refused before routing, the JSON formatter): the segment after these words is a credential.
# tests/core/test_log_redaction.py checks that every route with such a parameter is covered here.
_TOKEN_SEGMENT = re.compile(
    r"(/(?:invites|sessions|response-files|response-exports|datasource-exports|downloads|storage|short|links)/)"
    r"([^/?#]+)"
)
_PARAM = re.compile(r"^\{([A-Za-z_][A-Za-z0-9_]*)(?::[a-z]+)?\}$")


def mask_path(path: str | None, template: str | None = None) -> str | None:
    """The path with its credential segments as `***`. With the route template (e.g. /api/v1/public/invites/{token})
    the segments are found by parameter name; without one, by the known token-bearing addresses."""
    if not path:
        return path
    if template:
        concrete, pattern = path.split("/"), template.split("/")
        if len(concrete) == len(pattern):
            out = []
            for segment, part in zip(concrete, pattern, strict=True):
                param = _PARAM.match(part)
                out.append(MASK if param and param.group(1).lower() in SECRET_PATH_PARAMS else segment)
            return "/".join(out)
    return _TOKEN_SEGMENT.sub(lambda m: f"{m.group(1)}{MASK}", path)
