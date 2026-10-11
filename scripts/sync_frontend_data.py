"""Copies data files the backend serves from the frontend's mock into this project (the frontend is only read):

    server/mock/data/emailDefaults/*.json  →  app/modules/emails/defaults/   (email templates, 20 languages)

    fmly\\Scripts\\python.exe scripts\\sync_frontend_data.py [path\\to\\formalieFrontend]

Run again when the frontend changes them. Later phases add their data here (system lists, templates, help).
"""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FRONTEND = Path(sys.argv[1] if len(sys.argv) > 1 else os.environ.get("FORMALIE_FRONTEND_DIR",
                                                                      r"C:\UNETPROJECTS\formalieFrontend"))
COPIES = [(FRONTEND / "server" / "mock" / "data" / "emailDefaults", ROOT / "app" / "modules" / "emails" / "defaults", "*.json")]


def main() -> None:
    for source, target, pattern in COPIES:
        target.mkdir(parents=True, exist_ok=True)
        files = sorted(source.glob(pattern))
        if not files:
            raise SystemExit(f"Nothing found in {source}")
        for file in files:
            shutil.copyfile(file, target / file.name)
        print(f"{target.relative_to(ROOT)}: {len(files)} files")


if __name__ == "__main__":
    main()
