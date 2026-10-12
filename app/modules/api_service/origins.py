"""Allowed websites of an API service (port of shared/utils/apiService/origins.ts, F13, leftovers L6, owner
2026-10-10): the sites whose pages may call its endpoints straight from a visitor's browser (CORS). A website is an
origin: `https://` + host (+ port), no path. Plain `http://` only for localhost, for trying things out. Server apps,
mobile apps and Postman send no Origin and are not affected. Held to the frontend's answers (tests/parity).

The frontend reads the address with the browser's URL parser (WHATWG URL); `parse_url` reads it the same way for what
matters here: scheme, user info, host (numbers as IPv4, other names in punycode), port, path, query and fragment.
"""

from __future__ import annotations

import re

MAX_ALLOWED_ORIGINS = 20
_HOST = re.compile(r"[a-z0-9-]+(\.[a-z0-9-]+)+")
_SCHEME = re.compile(r"([a-zA-Z][a-zA-Z0-9+.-]*):")
_DEFAULT_PORTS = {"http": 80, "https": 443}


def _ipv4_part(part: str) -> int | None:
    if part[:2] in ("0x", "0X"):
        digits, base = part[2:], 16
        if digits == "":
            return 0
    elif len(part) > 1 and part[0] == "0":
        digits, base = part[1:], 8
    else:
        digits, base = part, 10
    allowed = {16: "0123456789abcdefABCDEF", 8: "01234567", 10: "0123456789"}[base]
    if not digits or any(c not in allowed for c in digits):
        return None
    return int(digits, base)


def _host(raw: str) -> str | None:
    """The host as the URL parser leaves it, or None when it refuses it."""
    if not raw:
        return None
    if raw.startswith("["):
        return raw if raw.endswith("]") else None
    try:
        host = ".".join(label.encode("idna").decode("ascii") if not label.isascii() else label
                        for label in raw.split(".")) if not raw.isascii() else raw
    except UnicodeError:
        return None
    host = host.lower()
    # Ends in a number: read as an IPv4 address (decimal, octal or hex parts, like the browser)
    parts = host.split(".")
    if parts and parts[-1] == "" and len(parts) > 1:
        parts = parts[:-1]
    last = parts[-1]
    if last and (last.isdigit() and last.isascii() or (last[:2] == "0x" and all(c in "0123456789abcdef" for c in last[2:]))):
        if len(parts) > 4:
            return None
        numbers = [_ipv4_part(p) for p in parts]
        if any(n is None for n in numbers):
            return None
        if any(n > 255 for n in numbers[:-1]) or numbers[-1] >= 256 ** (5 - len(numbers)):  # type: ignore[operator]
            return None
        value = 0
        for n in numbers[:-1]:
            value = value * 256 + n  # type: ignore[operator]
        value = value * 256 ** (5 - len(numbers)) + numbers[-1]  # type: ignore[operator]
        return ".".join(str((value >> s) & 255) for s in (24, 16, 8, 0))
    return host


def parse_url(url: str) -> dict[str, object] | None:
    m = _SCHEME.match(url)
    if not m:
        return None
    scheme, rest = m.group(1).lower(), url[m.end():]
    special = scheme in ("http", "https")
    rest = rest.lstrip("/\\") if special else rest
    cut = re.search(r"[/\\?#]" if special else r"[/?#]", rest)
    authority, after = (rest[:cut.start()], rest[cut.start():]) if cut else (rest, "")
    userinfo, _, authority = authority.rpartition("@")
    username, _, password = userinfo.partition(":")
    user = bool(username or password)
    port_text: str | None = None
    if not authority.endswith("]") and ":" in authority:
        authority, port_text = authority.rsplit(":", 1) if not authority.startswith("[") or "]:" in authority else (authority, None)
    host = _host(authority)
    if host is None:
        return None
    port: int | None = None
    if port_text:
        if not port_text.isdigit() or not port_text.isascii() or int(port_text) > 65535:
            return None
        port = int(port_text)
    if port is not None and port == _DEFAULT_PORTS.get(scheme):
        port = None
    path, query, fragment = after, "", ""
    if "#" in path:
        path, fragment = path.split("#", 1)
    if "?" in path:
        path, query = path.split("?", 1)
    segments: list[str] = []
    for segment in re.split(r"[/\\]", path)[1:] if path else []:
        if segment in (".", "%2e", "%2E"):
            continue
        if segment in ("..", ".%2e", "%2e.", "%2e%2e", ".%2E", "%2E.", "%2E%2E"):
            segments = segments[:-1]
            continue
        segments.append(segment)
    # "/a/." keeps a trailing slash, "/a/" too: only "" or "/" is no path at all
    pathname = "/" + "/".join(segments)
    return {"scheme": scheme, "host": host, "port": port, "pathname": pathname, "search": query, "hash": fragment,
            "user": user}


def normalise_origin(value: str) -> str | None:
    """The origin in its one form (`https://shop.example.com`), or None when it isn't a website address."""
    text = re.sub(r"/+$", "", value.strip().lower())
    if not text or re.search(r"\s", text):
        return None
    url = parse_url(text if "://" in text else f"https://{text}")
    if url is None:
        return None
    host = str(url["host"])
    local = host in ("localhost", "127.0.0.1") or host.endswith(".localhost")
    if url["scheme"] != "https" and not (url["scheme"] == "http" and local):
        return None
    # A website, not a page: nothing after the host
    if url["pathname"] != "/" or url["search"] or url["hash"] or url["user"]:
        return None
    if not local and not _HOST.fullmatch(host):
        return None
    return f"{url['scheme']}://{host}" + (f":{url['port']}" if url["port"] is not None else "")


def origin_allowed(origin: str | None, allowed: list[str] | None) -> bool:
    """May a page on `origin` call this service from a browser?"""
    if not origin or not allowed:
        return False
    normal = normalise_origin(origin)
    return bool(normal) and normal in allowed
