"""Access rules (port of shared/utils/apiService/access.ts, F13 M3, SECURITY-PROTOCOL §9), held to the frontend's
answers by tests/parity/test_api_rules.py: checking a rule's values (IP addresses and ranges, domains, countries,
regions, anonymous networks), matching a caller, and the decision: a matching block refuses; when allow rules apply,
the caller must match one of them. Domain rules use the browser's Origin (or Referer), so they only match browser
callers.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from app.modules.settings.catalogues import COUNTRY_CURRENCIES

API_RULE_KINDS = ("ip", "domain", "country", "region", "network")
API_NETWORKS = ("vpn", "proxy", "tor", "hosting")
# Rate limit choices (calls per minute; None = no limit).
RATE_LIMIT_CHOICES: list[int | None] = [30, 60, 120, 300, 600, 1200, 3000, None]

_JS_SPACE = "".join(chr(c) for c in (0x09, 0x0A, 0x0B, 0x0C, 0x0D, 0x20, 0xA0, 0x1680, *range(0x2000, 0x200B),
                                     0x2028, 0x2029, 0x202F, 0x205F, 0x3000, 0xFEFF))
_DOMAIN = re.compile(r"(\*\.)?(?=.{1,253}\Z)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}")
_V4 = re.compile(r"([0-9]{1,3})\.([0-9]{1,3})\.([0-9]{1,3})\.([0-9]{1,3})")
_MAPPED = re.compile(r"::ffff:([0-9]{1,3}(?:\.[0-9]{1,3}){3})", re.IGNORECASE)
_HEXCOLON = re.compile(r"[0-9a-fA-F:]+")
_GROUP = re.compile(r"[0-9a-fA-F]{1,4}")
_PREFIX = re.compile(r"[0-9]{1,3}")

# Regions by continent (UN geoscheme; the Americas split North / Central / Caribbean and South).
REGIONS: dict[str, list[str]] = {
    "AF": "DZ AO BJ BW BF BI CV CM CF TD KM CG CD CI DJ EG GQ ER SZ ET GA GM GH GN GW KE LS LR LY MG MW ML MR MU YT MA MZ NA NE NG RE RW SH ST SN SC SL SO ZA SS SD TZ TG TN UG EH ZM ZW IO".split(" "),
    "AS": "AF AM AZ BH BD BT BN KH CN CY GE HK IN ID IR IQ IL JP JO KZ KW KG LA LB MO MY MV MN MM NP KP OM PK PS PH QA SA SG KR LK SY TW TJ TH TL TR TM AE UZ VN YE CC CX".split(" "),
    "EU": "AX AL AD AT BY BE BA BG HR CZ DK EE FO FI FR DE GI GR GG VA HU IS IE IM IT JE XK LV LI LT LU MT MD MC ME NL MK NO PL PT RO RU SM RS SK SI ES SE CH UA GB".split(" "),
    "NA": "AG AI AW BS BB BZ BM BQ VG CA KY CR CU CW DM DO SV GL GD GP GT HT HN JM MQ MX MS NI PA PR BL KN LC MF PM VC SX TT TC US VI".split(" "),
    "OC": "AS AU CK FJ PF GU KI MH FM NR NC NZ NU NF MP PW PG PN WS SB TK TO TV VU WF".split(" "),
    "SA": "AR BO BR CL CO EC FK GF GY PY PE SR UY VE".split(" "),
}


def js_trim(text: str) -> str:
    return text.strip(_JS_SPACE)


@dataclass
class AccessCaller:
    ip: str
    domain: str | None = None  # host of the Origin / Referer header (browser callers), lower case
    country: str | None = None  # ISO country of the IP address (GeoIP)
    networks: list[str] = field(default_factory=list)  # VPN, proxy, Tor, hosting; empty when none


def check_rule_value(kind: str, value: str) -> str | None:
    """Problems with one value of a rule: `required`, `ip`, `domain`, `country`, `region` or `network`."""
    text = js_trim(value)
    if not text:
        return "required"
    if kind == "ip":
        return None if parse_cidr(text) else "ip"
    if kind == "domain":
        return None if _DOMAIN.fullmatch(text.lower()) else "domain"
    if kind == "country":
        return None if text.upper() in COUNTRY_CURRENCIES else "country"
    if kind == "network":
        return None if text.lower() in API_NETWORKS else "network"
    return None if text.upper() in REGIONS else "region"


def normalise_rule_value(kind: str, value: str) -> str:
    """A value as stored: IPs as typed, domains and networks in lower case, countries and regions in upper case."""
    text = js_trim(value)
    if kind in ("domain", "network"):
        return text.lower()
    if kind in ("country", "region"):
        return text.upper()
    return text


def region_of(country: str | None) -> str | None:
    """The region (continent) a country is in, or None."""
    if not country:
        return None
    code = country.upper()
    return next((region for region, codes in REGIONS.items() if code in codes), None)


def matches_value(kind: str, value: str, caller: AccessCaller) -> bool:
    """Whether a caller matches one value of a rule."""
    if kind == "ip":
        return ip_in_cidr(caller.ip, value)
    if kind == "domain":
        if not caller.domain:
            return False
        domain = caller.domain.lower()
        if value.startswith("*."):
            return domain.endswith(value[1:]) and domain != value[2:]
        return domain == value
    if kind == "country":
        return bool(caller.country) and caller.country.upper() == value  # type: ignore[union-attr]
    if kind == "network":
        return value in (caller.networks or [])
    return region_of(caller.country) == value


def decide_access(rules: list[dict[str, Any]], caller: AccessCaller) -> dict[str, Any]:
    """The decision for a caller against the rules that apply to an endpoint (enabled ones only):
    {allowed, reason: blocked | not_allowed | None, rule: {id, action, value} | None}."""
    active = [r for r in rules if r["enabled"]]
    for rule in (r for r in active if r["action"] == "block"):
        value = next((v for v in rule["values"] if matches_value(rule["kind"], v, caller)), None)
        if value:
            return {"allowed": False, "reason": "blocked", "rule": {"id": rule["id"], "action": "block", "value": value}}
    allows = [r for r in active if r["action"] == "allow"]
    if not allows:
        return {"allowed": True, "reason": None, "rule": None}
    for rule in allows:
        value = next((v for v in rule["values"] if matches_value(rule["kind"], v, caller)), None)
        if value:
            return {"allowed": True, "reason": None, "rule": {"id": rule["id"], "action": "allow", "value": value}}
    return {"allowed": False, "reason": "not_allowed", "rule": None}


def rules_for(rules: list[Any], endpoint_id: str, service_id: str, scope: Any = None) -> list[Any]:
    """The rules that apply to an endpoint: everywhere, its service, itself. `scope(rule)` → (type, id)."""
    get = scope or (lambda r: (r["scope"]["type"], r["scope"]["id"]))
    out = []
    for rule in rules:
        kind, target = get(rule)
        if kind == "all" or (kind == "service" and target == service_id) or (kind == "endpoint" and target == endpoint_id):
            out.append(rule)
    return out


# ── IP addresses ──────────────────────────────────────────────────────────────────

def parse_ip(text: str) -> tuple[int, int] | None:
    """An IP address as (family, number)."""
    v4 = _V4.fullmatch(text)
    if v4:
        parts = [int(p) for p in v4.groups()]
        if any(p > 255 for p in parts):
            return None
        value = 0
        for p in parts:
            value = (value << 8) + p
        return 4, value
    mapped = _MAPPED.fullmatch(text)
    if mapped:
        return parse_ip(mapped.group(1))
    if not _HEXCOLON.fullmatch(text) or ":" not in text or text.count("::") > 1:
        return None
    halves = text.split("::")
    head = halves[0]
    tail = halves[1] if len(halves) > 1 else ""
    left = head.split(":") if head else []
    double = "::" in text
    right = (tail.split(":") if tail else []) if double else []
    if double:
        fill = 8 - len(left) - len(right)
        if fill < 0:
            return None  # the browser throws here (Array(-1)); no such address either way
        groups = [*left, *(["0"] * fill), *right]
    else:
        groups = left
    if len(groups) != 8 or any(not _GROUP.fullmatch(g) for g in groups):
        return None
    value = 0
    for g in groups:
        value = (value << 16) + int(g, 16)
    return 6, value


def parse_cidr(text: str) -> tuple[int, int, int] | None:
    """An address or a range (`203.0.113.0/24`, `2001:db8::/32`) as (family, number, bits)."""
    pieces = js_trim(text).split("/")
    ip = parse_ip(pieces[0])
    if not ip:
        return None
    family, value = ip
    top = 32 if family == 4 else 128
    if len(pieces) < 2:
        bits = top
    else:
        bits = int(pieces[1]) if _PREFIX.fullmatch(pieces[1]) else -1
    if bits < 0 or bits > top:
        return None
    return family, value, bits


def ip_in_cidr(ip: str, cidr: str) -> bool:
    caller = parse_ip(ip)
    target = parse_cidr(cidr)
    if not caller or not target or caller[0] != target[0]:
        return False
    shift = (32 if target[0] == 4 else 128) - target[2]
    return caller[1] >> shift == target[1] >> shift
