"""Where a request comes from: MaxMind GeoLite2 City + ASN, with Cloudflare's location headers as the fallback.

The databases are `{GEOIP_DIR}/GeoLite2-City.mmdb` and `GeoLite2-ASN.mmdb`, refreshed weekly by
`logs.update_geoip` (Celery Beat) or `scripts/geoip_update.py`. Without them, and without Cloudflare headers
from a trusted proxy, location fields stay empty (`geo_source = none`). Private and loopback addresses are
never looked up (`geo_source = private`).
"""

from __future__ import annotations

import ipaddress
import logging
import threading
from pathlib import Path
from typing import Any

import geoip2.database
import geoip2.errors

from app.core.config import get_settings

log = logging.getLogger("formalie.geo")

CITY_DB = "GeoLite2-City.mmdb"
ASN_DB = "GeoLite2-ASN.mmdb"

# Cloudflare "visitor location headers" (managed transform), trusted only from our own proxy.
_CF_FIELDS = {
    "cf-ipcountry": "country",
    "cf-ipcontinent": "continent",
    "cf-ipcity": "city",
    "cf-region": "region",
    "cf-region-code": "region_code",
    "cf-postal-code": "postal_code",
    "cf-timezone": "timezone",
    "cf-iplatitude": "latitude",
    "cf-iplongitude": "longitude",
}


def _is_public(ip: str) -> bool:
    try:
        address = ipaddress.ip_address(ip)
    except ValueError:
        return False
    return address.is_global


class GeoLookup:
    def __init__(self, directory: Path | None = None) -> None:
        self.directory = Path(directory or get_settings().geoip_dir)
        self._lock = threading.Lock()
        self._city: geoip2.database.Reader | None = None
        self._asn: geoip2.database.Reader | None = None
        self._loaded_mtimes: tuple[float, float] = (0.0, 0.0)

    def _readers(self) -> tuple[geoip2.database.Reader | None, geoip2.database.Reader | None]:
        """Opens the databases, and reopens them after a weekly update replaced the files."""
        city_path, asn_path = self.directory / CITY_DB, self.directory / ASN_DB
        mtimes = (city_path.stat().st_mtime if city_path.exists() else 0.0,
                  asn_path.stat().st_mtime if asn_path.exists() else 0.0)
        if mtimes != self._loaded_mtimes:
            with self._lock:
                if mtimes != self._loaded_mtimes:
                    for reader in (self._city, self._asn):
                        if reader is not None:
                            reader.close()
                    self._city = geoip2.database.Reader(str(city_path)) if mtimes[0] else None
                    self._asn = geoip2.database.Reader(str(asn_path)) if mtimes[1] else None
                    self._loaded_mtimes = mtimes
        return self._city, self._asn

    def lookup(self, ip: str | None, headers: dict[str, str] | None = None, *, trusted_proxy: bool = False) -> dict[str, Any]:
        if not ip or not _is_public(ip):
            return {"geo_source": "private" if ip else "none"}
        result: dict[str, Any] = {"geo_source": "none"}
        try:
            city_reader, asn_reader = self._readers()
            if city_reader is not None:
                try:
                    city = city_reader.city(ip)
                    sub = city.subdivisions.most_specific
                    result.update({
                        "geo_source": "maxmind",
                        "continent": city.continent.code,
                        "country": city.country.iso_code,
                        "country_name": city.country.name,
                        "region": sub.name,
                        "region_code": sub.iso_code,
                        "city": city.city.name,
                        "postal_code": city.postal.code,
                        "timezone": city.location.time_zone,
                        "latitude": city.location.latitude,
                        "longitude": city.location.longitude,
                        "accuracy_km": city.location.accuracy_radius,
                    })
                except geoip2.errors.AddressNotFoundError:
                    pass
            if asn_reader is not None:
                try:
                    asn = asn_reader.asn(ip)
                    result["asn"] = asn.autonomous_system_number
                    result["as_org"] = asn.autonomous_system_organization
                except geoip2.errors.AddressNotFoundError:
                    pass
        except Exception as exc:  # noqa: BLE001 (a broken database file must never break logging)
            log.warning("geoip lookup failed", extra={"error": str(exc)})

        if result["geo_source"] == "none" and trusted_proxy and headers:
            cf = {field: headers.get(name) for name, field in _CF_FIELDS.items() if headers.get(name)}
            if cf.get("country") and cf["country"] not in ("XX", "T1"):
                for key in ("latitude", "longitude"):
                    if key in cf:
                        try:
                            cf[key] = float(cf[key])
                        except ValueError:
                            cf.pop(key)
                result.update(cf, geo_source="cloudflare")
        return result


_lookup: GeoLookup | None = None


def get_geo() -> GeoLookup:
    global _lookup
    if _lookup is None:
        _lookup = GeoLookup()
    return _lookup
