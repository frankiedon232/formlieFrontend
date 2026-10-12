"""Public addresses of forms (port of shared/utils/urls/public.ts and embed-domains.ts), held to the frontend's
answers by tests/parity/test_links_rules.py: custom links, short codes, the websites allowed to embed a form and the
`frame-ancestors` rule built from them, and the links Formalie hands out.
"""

from __future__ import annotations

import re
import secrets
import unicodedata

from app.core.config import get_settings

FORM_KEY_PATTERN = re.compile(r"^[A-Za-z0-9]{10}$")
CUSTOM_LINK_PATTERN = re.compile(r"^[a-z0-9](?:[a-z0-9]|-(?=[a-z0-9])){2,59}$")
SHORT_CODE_PATTERN = re.compile(r"^[a-hjkmnp-z2-9]{5}$")
SHORT_ALPHABET = "abcdefghjkmnpqrstuvwxyz23456789"

RESERVED_LINKS = frozenset({
    "admin", "ai", "analytics", "api", "api-service", "app", "audit", "auth", "billing", "dashboard", "data-sources",
    "email", "embed", "fill", "files", "folders", "form", "forms", "formalie", "help", "login", "logout", "manage", "new",
    "no-access", "onboarding", "option-sets", "people", "profile", "public", "responses", "s", "settings", "signin",
    "signup", "static", "storage", "support", "templates", "workspace-not-found", "www",
})

MAX_EMBED_DOMAINS = 20
_HOST = re.compile(r"^(\*\.)?(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}$")
_LOCAL = re.compile(r"^(localhost|127\.0\.0\.1)$")


def custom_link_problem(value: str) -> str | None:
    """Why a custom link can't be used: 'invalid', 'reserved', or None (fine to check for availability)."""
    if not CUSTOM_LINK_PATTERN.fullmatch(value):
        return "invalid"
    return "reserved" if value in RESERVED_LINKS else None


def tidy_custom_link(value: str) -> str:
    """A typed custom link tidied up: lower case, spaces and other characters → hyphens."""
    text = unicodedata.normalize("NFKD", value)
    text = re.sub(r"[̀-ͯ]", "", text).lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = re.sub(r"^-+|-+$", "", text)[:60]
    return re.sub(r"-+$", "", text)


def is_form_address(value: str) -> bool:
    return bool(FORM_KEY_PATTERN.fullmatch(value) or CUSTOM_LINK_PATTERN.fullmatch(value))


def new_short_code() -> str:
    return "".join(SHORT_ALPHABET[b % len(SHORT_ALPHABET)] for b in secrets.token_bytes(5))


def normalise_embed_domain(raw: str) -> str | None:
    """A typed website → `host` / `*.host` / `host:port`, or None when it isn't one."""
    value = raw.strip().lower()
    if not value:
        return None
    value = re.sub(r"^[a-z][a-z0-9+.-]*://", "", value)
    value = re.split(r"[/?#]", value)[0]
    value = re.sub(r"^[^@]*@", "", value)
    value = re.sub(r"\.$", "", value)
    host, *rest = value.split(":")
    port = rest[0] if rest else None
    if len(rest) > 1 or (port is not None and not re.fullmatch(r"\d{1,5}", port)):
        return None
    bare = host[4:] if host.startswith("www.") else host
    if not _HOST.fullmatch(bare) and not _LOCAL.fullmatch(bare):
        return None
    return f"{bare}:{port}" if port else bare


def frame_ancestors(domains: list[str], root_domain: str) -> str:
    """The `frame-ancestors` value: Formalie's own hosts always, then each allowed site (with and without www)."""
    if not domains:
        return "*"
    sources = ["'self'", f"https://{root_domain}", f"https://*.{root_domain}"]

    def add(source: str) -> None:
        if source not in sources:
            sources.append(source)
    for domain in domains:
        local = bool(_LOCAL.fullmatch(domain.split(":")[0]))
        add(f"{'http' if local else 'https'}://{domain}")
        if local:
            add(f"https://{domain}")
        if not domain.startswith("*.") and not local:
            add(f"https://www.{domain}")
    return " ".join(sources)


# ── Links Formalie hands out ────────────────────────────────────────────────────

def _port() -> str:
    """The port the browser used (development: :2202 through the Nuxt proxy)."""
    from app.modules.tenants.router import host_port

    return host_port()


def form_link(subdomain: str | None, address: str, kind: str = "fill") -> str:
    settings = get_settings()
    host = f"{subdomain}.{settings.root_domain}" if subdomain else f"forms.{settings.root_domain}"
    return f"https://{host}{_port()}/{address}/{kind}"


def short_link(code: str) -> str:
    return f"https://forms.{get_settings().root_domain}{_port()}/s/{code}"
