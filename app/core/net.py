"""IP addresses and ranges exactly as the frontend reads them (shared/utils/apiService/access.ts: parseIp,
parseCidr, ipInCidr). Python's ipaddress module accepts things the frontend refuses (zone ids, leading zeros in a
different way), so the settings and access rules use these instead."""

from __future__ import annotations

import re

_V4 = re.compile(r"^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$")
_MAPPED = re.compile(r"^::ffff:(\d{1,3}(?:\.\d{1,3}){3})$", re.IGNORECASE)
_HEX = re.compile(r"^[0-9a-f:]+$", re.IGNORECASE)
_GROUP = re.compile(r"^[0-9a-f]{1,4}$", re.IGNORECASE)


def parse_ip(text: str) -> tuple[int, int] | None:
    """(family, value) or None."""
    v4 = _V4.match(text)
    if v4:
        parts = [int(p) for p in v4.groups()]
        if any(p > 255 for p in parts):
            return None
        value = 0
        for p in parts:
            value = (value << 8) + p
        return 4, value
    mapped = _MAPPED.match(text)
    if mapped:
        return parse_ip(mapped.group(1))
    if not _HEX.match(text) or ":" not in text or text.count("::") > 1:
        return None
    head, _, tail = text.partition("::")
    left = head.split(":") if head else []
    right = (tail.split(":") if tail else []) if "::" in text else []
    groups = [*left, *["0"] * (8 - len(left) - len(right)), *right] if "::" in text else left
    if len(groups) != 8 or not all(_GROUP.match(g) for g in groups):
        return None
    value = 0
    for g in groups:
        value = (value << 16) + int(g, 16)
    return 6, value


def parse_cidr(text: str) -> tuple[int, int, int] | None:
    """(family, value, prefix bits) of an address or a range (`203.0.113.0/24`, `2001:db8::/32`), or None."""
    parts = text.strip().split("/")
    ip = parse_ip(parts[0])
    if ip is None:
        return None
    top = 32 if ip[0] == 4 else 128
    prefix = parts[1] if len(parts) > 1 else None
    bits = top if prefix is None else int(prefix) if re.fullmatch(r"\d{1,3}", prefix) else -1
    if bits < 0 or bits > top:
        return None
    return ip[0], ip[1], bits


def ip_in_cidr(ip: str, cidr: str) -> bool:
    caller, block = parse_ip(ip), parse_cidr(cidr)
    if caller is None or block is None or caller[0] != block[0]:
        return False
    shift = (32 if block[0] == 4 else 128) - block[2]
    return caller[1] >> shift == block[1] >> shift


def ip_bucket(ip: str | None) -> str:
    """The rate-limit key of a caller (B17 review M15): an IPv4 address as it is, an IPv6 address by its /64 (one
    customer network holds 2^64 addresses, so counting single addresses lets a caller rotate past every limit).
    IPv4-mapped IPv6 addresses count as their IPv4 address. Anything unreadable is kept as it came."""
    text = (ip or "").strip()
    if not text:
        return "unknown"
    parsed = parse_ip(text.split("%", 1)[0])  # a zone id (fe80::1%eth0) does not make a new network
    if parsed is None:
        return text[:64]
    family, value = parsed
    if family == 4:
        return ".".join(str((value >> shift) & 0xFF) for shift in (24, 16, 8, 0))
    network = value >> 64
    return ":".join(f"{(network >> shift) & 0xFFFF:x}" for shift in (48, 32, 16, 0)) + "::/64"
