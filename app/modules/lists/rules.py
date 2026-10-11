"""Option list rules (port of shared/utils/forms/options.ts and the helpers of translations.ts), held to the
frontend's answers by tests/parity/test_forms_rules.py.

A list is a dict like the frontend's OptionList: `options` (value, label, score?, active?, level?, parent?, attrs?,
translations?), `levels` (two to four named levels, else a plain list), `columns` (details), `large`.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable
from typing import Any

from app.core.locales import APP_LOCALE_CODES

MAX_LIST_LEVELS = 4
SEARCH_FROM = 50
LIVE_FROM = 20  # lists above this many active options live only in the database: forms keep no copy
LONG_FROM = 100
MAX_OPTIONS = 20_000
MAX_LARGE_OPTIONS = 200_000
LARGE_LIST_TYPES = ("dropdown", "multi_select")


def kept_on_server(lst: dict[str, Any]) -> bool:
    """Large, or above LIVE_FROM active options (or the builder's copy, which carries `level_counts`)."""
    return bool(lst.get("large")) or bool(lst.get("level_counts")) or \
        sum(1 for o in lst.get("options", []) if o.get("active") is not False) > LIVE_FROM


def value_from_label(label: str) -> str:
    """Lower case, accents dropped, a-z / 0-9 and "_"; "option" when nothing Latin is left."""
    base = unicodedata.normalize("NFKD", label)
    base = re.sub(r"[̀-ͯ]", "", base).lower()
    base = re.sub(r"[^a-z0-9]+", "_", base)
    base = re.sub(r"^_+|_+$", "", base)[:60]
    return base or "option"


def unique_value(wanted: str, taken: Iterable[str]) -> str:
    used = {t.lower() for t in taken}
    if wanted.lower() not in used:
        return wanted
    n = 2
    while f"{wanted}_{n}".lower() in used:
        n += 1
    return f"{wanted}_{n}"


def levels_of(lst: dict[str, Any]) -> list[dict[str, Any]] | None:
    levels = lst.get("levels")
    return levels if levels and len(levels) > 1 else None


def _offered_at(lst: dict[str, Any], level: int) -> list[dict[str, Any]]:
    """Active options at a level whose whole path above is active too."""
    open_parents: set[Any] = {None}
    result: list[dict[str, Any]] = []
    for at in range(level + 1):
        result = [o for o in lst.get("options", [])
                  if (o.get("level") or 0) == at and o.get("active") is not False
                  and (at == 0 or o.get("parent") in open_parents)]
        open_parents = {o["value"] for o in result}
    return result


def _details(attrs: dict[str, Any] | None, columns: list[dict[str, Any]] | None) -> dict[str, Any] | None:
    if not attrs or not columns:
        return None
    kept = {c["key"]: attrs[c["key"]] for c in columns if c["key"] in attrs and attrs[c["key"]] != ""}
    return kept or None


def offered_options(lst: dict[str, Any], level: int = 0) -> list[dict[str, Any]]:
    """What a level field gets from a list: value, label, score, the option it sits under, its details."""
    out = []
    for o in _offered_at(lst, level):
        item: dict[str, Any] = {"value": o["value"], "label": o["label"]}
        if o.get("score") is not None:
            item["score"] = o["score"]
        if level > 0 and o.get("parent") is not None:
            item["parent"] = o["parent"]
        details = _details(o.get("attrs"), lst.get("columns"))
        if details:
            item["attrs"] = details
        out.append(item)
    return out


def matches_list(options: list[dict[str, Any]] | None, lst: dict[str, Any], level: int = 0) -> bool:
    """A field's options still match its list at its level (same values, labels, scores, parents, details, order)."""
    wanted = offered_options(lst, level)
    if not options or len(options) != len(wanted):
        return False
    return all(o.get("value") == w["value"] and o.get("label") == w["label"]
               and o.get("score") == w.get("score") and o.get("parent") == w.get("parent")
               and (o.get("attrs") or None) == (w.get("attrs") or None)
               for o, w in zip(options, wanted, strict=True))


def level_counts(lst: dict[str, Any]) -> list[int]:
    return [len(_offered_at(lst, level)) for level in range(len(levels_of(lst) or [None]))]


def _fold(text: str) -> str:
    return re.sub(r"[̀-ͯ]", "", unicodedata.normalize("NFKD", text)).lower()


def match_options(options: list[dict[str, Any]], q: str, limit: int = 50) -> dict[str, Any]:
    """Labels containing `q` without minding case or accents; those starting with it first; at most `limit`."""
    wanted = _fold(q.strip())[:100]
    if not wanted:
        return {"items": options[:limit], "total": len(options)}
    matches = [o for o in options if wanted in _fold(o["label"])]
    first = [o for o in matches if _fold(o["label"]).startswith(wanted)]
    rest = [o for o in matches if not _fold(o["label"]).startswith(wanted)]
    return {"items": (first + rest)[:limit], "total": len(matches)}


def lookup_options(options: list[dict[str, Any]], *, q: str = "", values: list[str] | None = None,
                   parents: list[str] | None = None) -> dict[str, Any]:
    """`values` gives the labels of chosen options, `parents` keeps a lower level to what is under the choices
    above, `q` searches. Details come along, so auto-fill works in the browser too."""
    under = set(parents) if parents is not None else None
    pool = [{"value": o["value"], "label": o["label"], **({"attrs": o["attrs"]} if o.get("attrs") else {})}
            for o in options if under is None or (o.get("parent") is not None and o["parent"] in under)]
    if values is not None:
        wanted = set(values)
        return {"items": [o for o in pool if o["value"] in wanted], "total": len(values)}
    return match_options(pool, q)


# ── Translations helpers (shared/utils/forms/translations.ts) ───────────────────

def main_language(schema: dict[str, Any] | None) -> str:
    main = ((schema or {}).get("settings") or {}).get("language") or "en"
    return main if main in APP_LOCALE_CODES else "en"


def form_languages(schema: dict[str, Any] | None) -> list[str]:
    """The form's main language first, then the others it offers."""
    main = main_language(schema)
    others = ((schema or {}).get("settings") or {}).get("languages") or []
    return [main, *dict.fromkeys(c for c in others if c != main and c in APP_LOCALE_CODES)]


def text_hash(text: str) -> str:
    """FNV-1a over UTF-16 code units, in base 36: notices when an original text changes after translating."""
    value = 0x811C9DC5
    for unit in text.encode("utf-16-le").hex(" ", 2).split():
        code = int(unit[2:4] + unit[0:2], 16)
        value = ((value ^ code) * 0x01000193) & 0xFFFFFFFF
    digits = "0123456789abcdefghijklmnopqrstuvwxyz"
    out = ""
    while True:
        value, rest = divmod(value, 36)
        out = digits[rest] + out
        if value == 0:
            return out
