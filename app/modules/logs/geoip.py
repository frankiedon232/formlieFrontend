"""Downloads MaxMind GeoLite2 City and ASN into GEOIP_DIR (weekly, Celery Beat; or scripts/geoip_update.py).

Needs a free MaxMind account: MAXMIND_ACCOUNT_ID and MAXMIND_LICENSE_KEY in .env. Files are swapped in
atomically, and GeoLookup reopens them when they change.
"""

from __future__ import annotations

import io
import logging
import os
import tarfile
from pathlib import Path

import httpx

from app.core.config import get_settings

log = logging.getLogger("formalie.geo")

EDITIONS = ("GeoLite2-City", "GeoLite2-ASN")
URL = "https://download.maxmind.com/geoip/databases/{edition}/download?suffix=tar.gz"


def update_geoip(directory: Path | None = None) -> list[str]:
    settings = get_settings()
    if not settings.maxmind_account_id or settings.maxmind_license_key is None:
        raise RuntimeError("MAXMIND_ACCOUNT_ID and MAXMIND_LICENSE_KEY are not set (see .env.example)")
    target = Path(directory or settings.geoip_dir)
    target.mkdir(parents=True, exist_ok=True)
    auth = (settings.maxmind_account_id, settings.maxmind_license_key.get_secret_value())
    updated: list[str] = []
    with httpx.Client(timeout=120, follow_redirects=True) as client:
        for edition in EDITIONS:
            response = client.get(URL.format(edition=edition), auth=auth)
            response.raise_for_status()
            with tarfile.open(fileobj=io.BytesIO(response.content), mode="r:gz") as archive:
                member = next(m for m in archive.getmembers() if m.name.endswith(f"{edition}.mmdb"))
                data = archive.extractfile(member).read()  # type: ignore[union-attr]
            temporary = target / f"{edition}.mmdb.tmp"
            temporary.write_bytes(data)
            os.replace(temporary, target / f"{edition}.mmdb")
            updated.append(edition)
            log.info("geoip database updated", extra={"edition": edition, "bytes": len(data)})
    return updated
