"""Who is calling the public API (mock: publicApi.ts `callerOf`): the IP address, the browser's Origin (or Referer)
host, the country and the anonymous networks the address belongs to, for the access rules (access.py).

- **IP:** the real client address from the request context (forwarding headers only from trusted proxies).
- **Country:** MaxMind GeoLite2 (app/core/logging/geo.py), with Cloudflare's country header from our own proxy as
  the fallback.
- **Anonymous networks** (vpn, proxy, tor, hosting): our own lists first (owner: built in before external services):
  `{API_NETWORKS_DIR or GEOIP_DIR/networks}/{vpn,proxy,tor,hosting}.txt`, one address or range per line (`#` starts
  a comment), read again when a file changes; and hosting providers known by their network number (ASN, from the
  GeoLite2 ASN database). An address no list knows is in no network.
- **Development and tests only:** `X-Debug-Country` and `X-Debug-Network` stand in for GeoIP, exactly like the mock,
  so rules can be tried from Postman. Production ignores both headers.
"""

from __future__ import annotations

import ipaddress
import logging
import re
import threading
from pathlib import Path
from typing import Any

from app.core.config import get_settings
from app.core.context import get_context
from app.core.logging.geo import get_geo
from app.modules.api_service.access import API_NETWORKS, AccessCaller
from app.modules.api_service.origins import parse_url

log = logging.getLogger("formalie.api.callers")

# Hosting and cloud providers by network number: calls from servers, not people (kept short and certain).
HOSTING_ASNS = frozenset({
    16509, 14618, 8987,  # Amazon Web Services
    396982, 19527,  # Google Cloud
    8075,  # Microsoft Azure
    14061,  # DigitalOcean
    16276,  # OVHcloud
    24940, 213230,  # Hetzner
    63949,  # Akamai Connected Cloud (Linode)
    20473,  # Vultr (Choopa)
    31898,  # Oracle Cloud
    45102,  # Alibaba Cloud
    132203,  # Tencent Cloud
    12876,  # Scaleway
    51167,  # Contabo
    9009,  # M247
    60068, 212238,  # Datacamp (CDN77)
})
_COUNTRY = re.compile(r"[A-Z]{2}")

Network = ipaddress.IPv4Network | ipaddress.IPv6Network


class NetworkLists:
    """The address lists per anonymous network, reloaded when a file changes."""

    def __init__(self, directory: Path | None = None) -> None:
        settings = get_settings()
        self.directory = Path(directory or settings.api_networks_dir or settings.geoip_dir / "networks")
        self._lock = threading.Lock()
        self._mtimes: dict[str, float] = {}
        self._lists: dict[str, list[Network]] = {}

    def _load(self) -> dict[str, list[Network]]:
        for kind in API_NETWORKS:
            path = self.directory / f"{kind}.txt"
            mtime = path.stat().st_mtime if path.exists() else 0.0
            if self._mtimes.get(kind) == mtime:
                continue
            with self._lock:
                networks: list[Network] = []
                if mtime:
                    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
                        text = line.split("#", 1)[0].strip()
                        if not text:
                            continue
                        try:
                            networks.append(ipaddress.ip_network(text, strict=False))
                        except ValueError:
                            log.warning("not an address or range in %s: %s", path.name, text[:60])
                self._lists[kind], self._mtimes[kind] = networks, mtime
        return self._lists

    def of(self, ip: str) -> list[str]:
        try:
            address = ipaddress.ip_address(ip)
        except ValueError:
            return []
        lists = self._load()
        return [kind for kind in API_NETWORKS if any(address.version == n.version and address in n
                                                     for n in lists.get(kind, []))]


_lists: NetworkLists | None = None


def network_lists() -> NetworkLists:
    global _lists
    if _lists is None:
        _lists = NetworkLists()
    return _lists


def set_network_lists(lists: NetworkLists | None) -> None:
    """Tests: lists from another folder (None: back to the settings)."""
    global _lists
    _lists = lists


def domain_of(origin: str | None) -> str | None:
    """The host of an Origin or Referer, lower case (mock: new URL(origin).hostname), or None."""
    if not origin:
        return None
    url = parse_url(origin.strip())
    if url is None or not url["host"]:
        return None
    return str(url["host"]).lower()


def caller_of(headers: Any) -> AccessCaller:
    """The caller of this request. `headers`: the request's headers (case-insensitive mapping)."""
    ctx = get_context()
    ip = re.sub(r"^::ffff:", "", (ctx.client_ip if ctx else None) or "0.0.0.0", flags=re.IGNORECASE)
    domain = domain_of(headers.get("origin") or headers.get("referer"))
    settings = get_settings()
    country: str | None = None
    networks: list[str] = []
    debug = settings.is_development
    if debug and headers.get("x-debug-country") is not None:
        wanted = headers.get("x-debug-country", "").strip().upper()
        country = wanted if _COUNTRY.fullmatch(wanted) else None
    else:
        geo = get_geo().lookup(ip, {k.lower(): v for k, v in headers.items()},
                               trusted_proxy=bool(ctx and ctx.proxy_trusted))
        found = geo.get("country")
        country = found.upper() if isinstance(found, str) and _COUNTRY.fullmatch(found.upper()) else None
        networks = network_lists().of(ip)
        if geo.get("asn") in HOSTING_ASNS and "hosting" not in networks:
            networks.append("hosting")
    if debug and headers.get("x-debug-network") is not None:
        sent = [item.strip().lower() for item in headers.get("x-debug-network", "").split(",")]
        networks = [item for item in sent if item in API_NETWORKS]
    return AccessCaller(ip=ip, domain=domain, country=country, networks=networks)
