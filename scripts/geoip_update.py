"""Downloads MaxMind GeoLite2 City + ASN into GEOIP_DIR now (Celery Beat also does it weekly).

    fmly\\Scripts\\python.exe scripts\\geoip_update.py

Needs MAXMIND_ACCOUNT_ID and MAXMIND_LICENSE_KEY in .env (free account at maxmind.com, GeoLite2).
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import get_settings  # noqa: E402
from app.modules.logs.geoip import update_geoip  # noqa: E402

if __name__ == "__main__":
    for edition in update_geoip():
        print(f"{edition}: updated in {get_settings().geoip_dir}")
