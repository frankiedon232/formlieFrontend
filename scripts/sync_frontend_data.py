"""Copies data files the backend serves from the frontend's mock into this project (the frontend is only read):

    server/mock/data/emailDefaults/*.json  →  app/modules/emails/defaults/   (email templates, 20 languages)
    shared/templates/messages/*.json       →  app/modules/templates/data/messages/    (template text per language)
    shared/templates/vocabulary/*.json     →  app/modules/templates/data/vocabulary/  (everyday form words)
    i18n/locales/*.json (template names, categories, the builder's default texts) → app/modules/templates/data/ui/
    server/mock/data/libraryStore.ts (DEFAULT_OPTION_TRANSLATIONS) → app/modules/lists/data/option_translations.json
    server/mock/data/help/*.json           →  app/modules/help/data/      (help centre: articles, FAQs, glossary, tours;
                                              then `scripts/seed_help.py` loads them into the global help tables)

    fmly\\Scripts\\python.exe scripts\\sync_frontend_data.py [path\\to\\formalieFrontend]

Run again when the frontend changes them. Later phases add their data here.
"""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FRONTEND = Path(sys.argv[1] if len(sys.argv) > 1 else os.environ.get("FORMALIE_FRONTEND_DIR",
                                                                      r"C:\UNETPROJECTS\formalieFrontend"))
TEMPLATES = ROOT / "app" / "modules" / "templates" / "data"
COPIES = [
    (FRONTEND / "server" / "mock" / "data" / "emailDefaults", ROOT / "app" / "modules" / "emails" / "defaults", "*.json"),
    (FRONTEND / "shared" / "templates" / "messages", TEMPLATES / "messages", "*.json"),
    (FRONTEND / "shared" / "templates" / "vocabulary", TEMPLATES / "vocabulary", "*.json"),
    (FRONTEND / "server" / "mock" / "data" / "help", ROOT / "app" / "modules" / "help" / "data", "*.json"),
]


def ui_texts() -> None:
    """From each locale file, only what templates need: their names and descriptions, category names, and the
    builder's default texts (field names, "Option {n}", "Row {n}", "Page {n}")."""
    import json

    target = TEMPLATES / "ui"
    target.mkdir(parents=True, exist_ok=True)
    files = sorted((FRONTEND / "i18n" / "locales").glob("*.json"))
    for file in files:
        data = json.loads(file.read_text(encoding="utf-8"))
        templates, builder = data.get("templates") or {}, data.get("builder") or {}
        kept = {"templates": {"items": templates.get("items") or {}, "categories": templates.get("categories") or {}},
                "builder": {"field": builder.get("field") or {}, "defaults": builder.get("defaults") or {},
                            "page": builder.get("page") or {}}}
        (target / file.name).write_text(json.dumps(kept, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"{target.relative_to(ROOT)}: {len(files)} files")


def option_translations() -> None:
    """The options of Formalie's sample lists in every language (the mock's DEFAULT_OPTION_TRANSLATIONS)."""
    import json
    import re

    source = (FRONTEND / "server" / "mock" / "data" / "libraryStore.ts").read_text(encoding="utf-8")
    found = re.search(r"DEFAULT_OPTION_TRANSLATIONS[^=]*=\s*(\{.*?\n\})", source, re.S)
    if not found:
        raise SystemExit("DEFAULT_OPTION_TRANSLATIONS not found in libraryStore.ts")
    data = json.loads(re.sub(r",\s*\}$", "}", found.group(1)))
    target = ROOT / "app" / "modules" / "lists" / "data" / "option_translations.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"{target.relative_to(ROOT)}: {len(data)} labels")


def main() -> None:
    for source, target, pattern in COPIES:
        target.mkdir(parents=True, exist_ok=True)
        files = sorted(source.glob(pattern))
        if not files:
            raise SystemExit(f"Nothing found in {source}")
        for file in files:
            shutil.copyfile(file, target / file.name)
        print(f"{target.relative_to(ROOT)}: {len(files)} files")
    ui_texts()
    option_translations()


if __name__ == "__main__":
    main()
