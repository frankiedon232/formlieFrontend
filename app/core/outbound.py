"""Outgoing connections to addresses a workspace typed in (B11: its own mail server, its identity provider).

Like webhooks (B10), the name is resolved here and every address it resolves to must be public, then the
connection goes to that checked address, so nobody can point Formalie at its own network. `blocked()` is the one
blocklist for every outgoing connection (mail servers, identity providers, webhooks, data sources): anything that is
not globally routable (`not ip.is_global`: private, loopback, link-local, carrier-grade NAT, unique local, reserved,
documentation and benchmark ranges), multicast, and the ranges that embed another address (6to4, NAT64, the 6to4
relay anycast). `allow_local` (development and tests only, never in staging or production) lets this machine and
private networks through.

Replies are read as a stream and capped (`max_bytes`), and every call has a total time limit (`total`), not only a
limit per read, so a slow or endless answer can't hold a worker.

Tests set `resolver` to a function (host, port) → addresses.
"""

from __future__ import annotations

import asyncio
import ipaddress
import socket
from collections.abc import Awaitable, Callable
from typing import Any

from app.core.config import get_settings

Resolver = Callable[[str, int], Awaitable[list[str]]]
resolver: Resolver | None = None  # tests only

_CGNAT = ipaddress.ip_network("100.64.0.0/10")
# Globally routable on paper, but they carry or reach another address: never connect to them.
_EMBEDDING = tuple(ipaddress.ip_network(n) for n in (
    "2002::/16",        # 6to4 (2002:7f00:1:: is 127.0.0.1)
    "64:ff9b::/96",     # NAT64, well known
    "64:ff9b:1::/48",   # NAT64, local use
    "192.88.99.0/24",   # 6to4 relay anycast
    "192.0.0.0/24",     # IETF protocol assignments
))
MAX_REPLY_BYTES = 1_000_000
TOTAL_SECONDS = 15.0


class Refused(Exception):
    """The name resolves to an address Formalie never connects to."""


class Unresolved(Exception):
    """The name doesn't resolve."""


def blocked(address: str) -> bool:
    """True for every address Formalie never connects to on someone's behalf (the one blocklist)."""
    try:
        ip = ipaddress.ip_address(address.split("%")[0].strip("[]"))
    except ValueError:
        return True
    if isinstance(ip, ipaddress.IPv6Address):
        if ip.ipv4_mapped:
            ip = ip.ipv4_mapped
        elif ip.sixtofour or ip.teredo:
            return True
    return (not ip.is_global or ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast
            or ip.is_unspecified or ip.is_reserved or (isinstance(ip, ipaddress.IPv4Address) and ip in _CGNAT)
            or any(ip.version == n.version and ip in n for n in _EMBEDDING))


def local_allowed(flag: bool) -> bool:
    """A *_ALLOW_LOCAL flag counts only in development and tests (APP_ENV development or test)."""
    return flag and get_settings().app_env in ("development", "test")


async def public_address(host: str, port: int, *, allow_local: bool = False) -> str:
    """The address to connect to for `host`, or Refused / Unresolved."""
    name = host.strip().strip("[]").rstrip(".")
    if not name:
        raise Unresolved(host)
    try:
        if resolver is not None:
            addresses = list(await resolver(name, port))
        else:
            infos = await asyncio.get_running_loop().getaddrinfo(name, port, type=socket.SOCK_STREAM)
            addresses = [str(info[4][0]) for info in infos]
    except (socket.gaierror, OSError, UnicodeError):
        raise Unresolved(host) from None
    if not addresses:
        raise Unresolved(host)
    if not allow_local and any(blocked(a) for a in addresses):
        raise Refused(host)
    return addresses[0]


transport: Any = None  # tests: an httpx.MockTransport (then the address is not pinned)


async def read_capped(answer: Any, max_bytes: int, *, cut: bool = False) -> bytes | None:
    """The decoded body of a streamed httpx response, or None once it passes `max_bytes` (`cut`: its first
    `max_bytes` instead). The rest is never read, so a compressed answer can't unpack into more than the cap."""
    body = bytearray()
    async for chunk in answer.aiter_bytes():
        body += chunk
        if len(body) > max_bytes:
            return bytes(body[:max_bytes]) if cut else None
    return bytes(body)


async def http(method: str, url: str, *, allow_local: bool = False, timeout: float = 6.0,
               total: float = TOTAL_SECONDS, max_bytes: int = MAX_REPLY_BYTES, **kwargs: Any) -> Any:
    """An HTTPS request to an address someone typed in → the httpx response (body read, at most `max_bytes`), or
    None when it can't be reached (refused address, unknown name, time-out, TLS or connection error, an answer
    larger than `max_bytes`, or longer than `total` seconds in all). No redirects are followed."""
    try:
        return await asyncio.wait_for(_http(method, url, allow_local=allow_local, timeout=timeout,
                                            max_bytes=max_bytes, **kwargs), total)
    except TimeoutError:
        return None


async def _http(method: str, url: str, *, allow_local: bool, timeout: float, max_bytes: int, **kwargs: Any) -> Any:
    import httpx

    try:
        target = httpx.URL(url)
    except (httpx.InvalidURL, ValueError, TypeError):
        return None
    if target.scheme != "https" and not (allow_local and target.scheme == "http"):
        return None
    host = target.host
    extensions: dict[str, object] = {}
    headers = dict(kwargs.pop("headers", None) or {})
    if transport is None:
        try:
            address = await public_address(host, target.port or (443 if target.scheme == "https" else 80),
                                           allow_local=allow_local)
        except (Refused, Unresolved):
            return None
        headers["Host"] = target.netloc.decode("ascii")
        extensions["sni_hostname"] = host
        target = target.copy_with(host=address)
    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=False, transport=transport,
                                     trust_env=False) as client:
            request = client.build_request(method, target, headers=headers, extensions=extensions, **kwargs)
            answer = await client.send(request, stream=True)
            try:
                raw = await read_capped(answer, max_bytes)
            finally:
                await answer.aclose()
            if raw is None:
                return None
            kept = [(k, v) for k, v in answer.headers.multi_items()
                    if k.lower() not in ("content-encoding", "content-length", "transfer-encoding")]
            return httpx.Response(answer.status_code, headers=kept, content=raw, request=request,
                                  extensions=answer.extensions)
    except (httpx.HTTPError, UnicodeError, ValueError):
        return None
