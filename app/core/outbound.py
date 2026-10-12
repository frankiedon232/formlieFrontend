"""Outgoing connections to addresses a workspace typed in (B11: its own mail server, its identity provider).

Like webhooks (B10), the name is resolved here and every address it resolves to must be public (never loopback,
private, link-local, carrier-grade NAT, multicast or reserved), then the connection goes to that checked address,
so nobody can point Formalie at its own network. `allow_local` (development and tests only, never in production)
lets this machine and private networks through.

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


class Refused(Exception):
    """The name resolves to an address Formalie never connects to."""


class Unresolved(Exception):
    """The name doesn't resolve."""


def blocked(address: str) -> bool:
    ip = ipaddress.ip_address(address.split("%")[0])
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped:
        ip = ip.ipv4_mapped
    return (ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast or ip.is_unspecified
            or ip.is_reserved or (isinstance(ip, ipaddress.IPv4Address) and ip in _CGNAT))


def local_allowed(flag: bool) -> bool:
    return flag and not get_settings().is_production


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


async def http(method: str, url: str, *, allow_local: bool = False, timeout: float = 6.0,
               **kwargs: Any) -> Any:
    """An HTTPS request to an address someone typed in → the httpx response, or None when it can't be reached
    (refused address, unknown name, time-out, TLS or connection error). No redirects are followed."""
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
            return await client.request(method, target, headers=headers, extensions=extensions, **kwargs)
    except (httpx.HTTPError, UnicodeError, ValueError):
        return None
