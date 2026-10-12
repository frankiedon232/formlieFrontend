"""Webhook rules (port of shared/utils/integrations/webhooks.ts, F13 M6), held to the frontend's answers by
tests/parity/test_webhook_rules.py: which addresses may receive deliveries, when a delivery is retried and when a
webhook pauses itself.

The frontend reads the address with the browser's URL parser (WHATWG URL); `parse_url` (api_service/origins.py) reads
it the same way for what matters here, with the IPv6 host written as the browser writes it and the characters a host
can never hold refused (the browser throws on them). The worker checks again, on every address the name resolves to,
right before each try (tasks.py).
"""

from __future__ import annotations

import ipaddress
import re

from app.modules.api_service.access import ip_in_cidr, js_trim, parse_ip
from app.modules.api_service.origins import parse_url
from app.modules.data_sources.engines import is_blocked_host

WEBHOOK_EVENTS = ("response.created", "response.updated", "response.status_changed", "response.deleted")
WEBHOOK_STATUSES = ("active", "failing", "paused")
WEBHOOK_DELIVERY_STATUSES = ("delivered", "retrying", "failed")

# Private and reserved networks a webhook never calls (server-side request forgery).
PRIVATE = ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16", "100.64.0.0/10", "169.254.0.0/16", "0.0.0.0/8", "fc00::/7",
           "fe80::/10")
LOCAL = frozenset({"localhost", "127.0.0.1", "[::1]", "::1"})

# Minutes to wait before each retry (then it is failed for good).
WEBHOOK_RETRY_MINUTES = (1, 5, 15, 60, 360)
# After this many failed deliveries in a row the webhook pauses itself (nothing is lost: they can be sent again).
WEBHOOK_AUTO_PAUSE = 20
# A receiver has this long to answer.
WEBHOOK_TIMEOUT_MS = 10_000

_OTHER_SPECIAL = ("ftp", "ws", "wss")
_FORMALIE = re.compile(r"(^|\.)formalie\.(dev|com)$")
# Characters the URL parser never accepts in a host name (forbidden domain code points)
_FORBIDDEN_HOST = re.compile(r"[\x00-\x20#%/:<>?@\[\\\]^|\x7f]")


def _ipv6_text(inner: str) -> str | None:
    """An IPv6 host as the browser writes it: lower case, the longest run of zero groups (two or more) as `::`."""
    try:
        address = ipaddress.IPv6Address(inner)
    except ValueError:
        return None
    groups = [(address.packed[i] << 8) | address.packed[i + 1] for i in range(0, 16, 2)]
    best_start, best_len, start = -1, 1, -1
    for i in range(9):
        if i < 8 and groups[i] == 0:
            start = i if start < 0 else start
            continue
        if start >= 0 and i - start > best_len:
            best_start, best_len = start, i - start
        start = -1
    if best_start < 0:
        return ":".join(f"{g:x}" for g in groups)
    head = ":".join(f"{g:x}" for g in groups[:best_start])
    tail = ":".join(f"{g:x}" for g in groups[best_start + best_len:])
    return f"{head}::{tail}"


def webhook_url_parts(value: str) -> dict[str, object] | None:
    """scheme, host (as the browser's `hostname`), port, user; None when the browser would not read it as an address."""
    scheme = re.match(r"([a-zA-Z][a-zA-Z0-9+.-]*):", value)
    other = scheme.group(1).lower() if scheme and scheme.group(1).lower() in _OTHER_SPECIAL else None
    # ftp, ws and wss are read like http(s) by the browser (special schemes)
    url = parse_url(f"https{value[len(other):]}" if other else value)
    if url is None:
        return None
    if other:
        url = {**url, "scheme": other}
    host = str(url["host"])
    if host.startswith("["):
        written = _ipv6_text(host[1:-1])
        if written is None:
            return None
        host = f"[{written}]"
    elif _FORBIDDEN_HOST.search(host):
        return None
    if url["scheme"] in ("http", "https") and not host:
        return None
    return {**url, "host": host}


def check_webhook_url(value: str, allow_local: bool = False) -> str | None:
    """An address that may receive webhooks: HTTPS, a public host, never Formalie itself. `allow_local` (development
    only) lets `http://localhost` through so a receiver on the developer's machine works. Problems: required · url ·
    https · host · private."""
    text = js_trim(value)
    if not text:
        return "required"
    url = webhook_url_parts(text)
    if url is None:
        return "url"
    host = str(url["host"]).lower()
    if allow_local and host in LOCAL and url["scheme"] in ("http", "https"):
        return None
    if url["scheme"] != "https":
        return "https"
    if url["user"]:
        return "url"
    if _FORMALIE.search(host):
        return "host"
    if is_blocked_host(host):
        return "private"
    bare = re.sub(r"^\[|\]$", "", host)
    if parse_ip(bare) and any(ip_in_cidr(bare, network) for network in PRIVATE):
        return "private"
    return None


def signed_payload(timestamp: int, body: str) -> str:
    """What was signed before webhook tokens (`{timestamp}.{body}`); kept for parity, deliveries are not signed."""
    return f"{timestamp}.{body}"


def webhook_status_of(enabled: bool, consecutive_failures: int) -> str:
    """active · failing (the last delivery failed, retries running) · paused (by someone, or after failures)."""
    if not enabled:
        return "paused"
    return "failing" if consecutive_failures > 0 else "active"


def event_label_key(event: str) -> str:
    return f"integrations.webhooks.event.{event.replace('.', '_', 1)}"
