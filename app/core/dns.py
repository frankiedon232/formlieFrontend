"""DNS lookups for workspaces' own domains (B11: the sending address and the web address), with dnspython.

`lookup(name, "TXT" | "CNAME")` → the values found (TXT strings joined, CNAME targets without the final dot, lower
case). "No such name" and "no such record" are an empty answer, not an error (the mock's ENODATA / ENOTFOUND);
anything else (time-out, no name server answers) raises DnsError, which the checks report as `dns_error`.

Tests set `resolver` to a function (name, type) → list of values, so they never depend on the internet.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from app.core.config import get_settings

Resolver = Callable[[str, str], Awaitable[list[str]]]
resolver: Resolver | None = None  # tests only


class DnsError(Exception):
    pass


def clean(value: str) -> str:
    return value.strip().rstrip(".").lower()


async def lookup(name: str, rdtype: str) -> list[str]:
    if resolver is not None:
        return list(await resolver(name, rdtype))
    import dns.asyncresolver
    import dns.exception
    import dns.resolver

    lookup_ = dns.asyncresolver.Resolver()
    lookup_.lifetime = get_settings().dns_timeout_seconds
    try:
        answer = await lookup_.resolve(name, rdtype, raise_on_no_answer=False)
    except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer):
        return []
    except dns.exception.DNSException as error:
        raise DnsError(type(error).__name__) from None
    if answer.rrset is None:
        return []
    if rdtype == "TXT":
        return [b"".join(item.strings).decode("utf-8", "replace") for item in answer.rrset]
    return [clean(item.to_text()) for item in answer.rrset]
