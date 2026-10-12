"""Rules of the public form page (ports of shared/utils/forms/availability.ts, identity.ts, translations.ts,
options.ts and file-types.ts, and the mock's fingerprintOf), held to the frontend's answers by
tests/parity/test_public_rules.py.
"""

from __future__ import annotations

import copy
import hashlib
import re
import unicodedata
from datetime import UTC, datetime
from typing import Any, Callable

from app.core import js
from app.core.locales import APP_LOCALE_CODES
from app.modules.public.submit import all_fields

# ── When a form takes responses (availability.ts) ───────────────────────────────

def availability_of(opens_at: datetime | None, closes_at: datetime | None, now: datetime | None = None) -> str:
    """always · open (within the dates) · scheduled (before opens_at) · expired (after closes_at)."""
    moment = now or datetime.now(UTC)
    if closes_at is not None and moment >= closes_at:
        return "expired"
    if opens_at is not None and moment < opens_at:
        return "scheduled"
    return "always" if opens_at is None and closes_at is None else "open"


# ── Telling people apart (identity.ts) ──────────────────────────────────────────

_OTHER_PERSON = re.compile(
    r"\b(reference|referee|manager|supervisor|guardian|parent|emergency|contact person|next of kin|friend|partner|"
    r"spouse|colleague|employer|company|business|billing|invoice|sponsor|assistant|secretary|recipient|cc)\b",
    re.IGNORECASE | re.ASCII)
_NAME_FIELD = re.compile(r"\b(first|last|given|family|sur)\s*name\b|\bname\b", re.IGNORECASE | re.ASCII)
_GMAIL = {"gmail.com", "googlemail.com"}


def _text_of(fld: dict[str, Any]) -> str:
    label = fld.get("label")
    return f"{'' if js.nullish(label) else js.to_string(label)} {fld['key'].replace('_', ' ')}"


def suggest_email_field(fields: list[dict[str, Any]]) -> str | None:
    return next((f["key"] for f in fields if f.get("type") == "email" and not _OTHER_PERSON.search(_text_of(f))), None)


def identity_of(schema: dict[str, Any]) -> dict[str, Any]:
    """{ email: key | None, verify }: the stored settings, or a suggestion when the form never chose."""
    stored = (schema.get("settings") or {}).get("identity")
    fields = all_fields(schema)

    def exists(key: Any) -> str | None:
        return key if key and any(f["key"] == key and f.get("type") == "email" for f in fields) else None
    if stored:
        email = exists(stored.get("email"))
        return {"email": email, "verify": bool(stored.get("verify")) and bool(email)}
    return {"email": suggest_email_field(fields), "verify": False}


def normalise_email(value: Any) -> str | None:
    """Case, spaces, plus-tags; Gmail also ignores dots in the name part."""
    if not isinstance(value, str) or "@" not in value:
        return None
    parts = js.trim(value).lower().split("@")
    raw_local, raw_domain = parts[0], parts[1]
    domain = "gmail.com" if raw_domain == "googlemail.com" else raw_domain
    local = raw_local.split("+")[0]
    if domain in _GMAIL:
        local = local.replace(".", "")
    return f"{local}@{domain}" if local and domain else None


def normalise_name(value: Any) -> str:
    """Accents, case, punctuation and word order don't matter."""
    if isinstance(value, str):
        text = value
    elif isinstance(value, dict):
        text = " ".join(v for v in value.values() if isinstance(v, str))
    elif isinstance(value, list):
        text = " ".join(v for v in value if isinstance(v, str))
    else:
        text = ""
    text = re.sub(r"[̀-ͯ]", "", unicodedata.normalize("NFKD", text)).lower()
    text = re.sub(r"[^a-z\s]", " ", text)
    return " ".join(sorted(w for w in re.split(r"\s+", text) if w))


def edit_distance(a: str, b: str) -> int:
    """Edits to turn one text into the other (insert, delete, replace, swap neighbours)."""
    d = [[i] + [0] * len(b) for i in range(len(a) + 1)]
    for j in range(1, len(b) + 1):
        d[0][j] = j
    for i in range(1, len(a) + 1):
        for j in range(1, len(b) + 1):
            cost = 0 if a[i - 1] == b[j - 1] else 1
            d[i][j] = min(d[i - 1][j] + 1, d[i][j - 1] + 1, d[i - 1][j - 1] + cost)
            if i > 1 and j > 1 and a[i - 1] == b[j - 2] and a[i - 2] == b[j - 1]:
                d[i][j] = min(d[i][j], d[i - 2][j - 2] + 1)
    return d[len(a)][len(b)]


def name_similarity(a: Any, b: Any) -> float:
    x, y = normalise_name(a), normalise_name(b)
    if not x or not y:
        return 0.0
    if x == y:
        return 1.0
    return 1 - edit_distance(x, y) / max(len(x), len(y))


def _emails_near(a: str, b: str) -> bool:
    la, da = (a.split("@") + [""])[:2]
    lb, db = (b.split("@") + [""])[:2]
    domain_close = da == db or edit_distance(da, db) <= 1
    allowed = 2 if max(len(la), len(lb)) >= 8 else 1
    return domain_close and edit_distance(la, lb) <= allowed


emails_near = _emails_near  # public/duplicates.py picks the candidates with it


def _name_of(fields: list[dict[str, Any]], data: dict[str, Any]) -> str:
    full = next((f for f in fields if f.get("type") == "full_name"), None)
    if full:
        return normalise_name(data.get(full["key"]))
    parts = [f for f in fields if f.get("type") == "short_text" and _NAME_FIELD.search(_text_of(f))
             and not _OTHER_PERSON.search(_text_of(f))]
    return normalise_name(" ".join("" if js.nullish(data.get(f["key"], js.UNDEFINED)) else js.to_string(data[f["key"]])
                                   for f in parts))


def match_identity(schema: dict[str, Any], answers: dict[str, Any], earlier: list[dict[str, Any]],
                   identity: dict[str, Any] | None = None) -> dict[str, Any]:
    """{ level: none | likely | clear, reason?, record? } against earlier responses ({ id, submitted_at, data })."""
    identity = identity or identity_of(schema)
    key = identity["email"]
    email = normalise_email(answers.get(key)) if key else None
    if not key or not email:
        return {"level": "none"}
    for record in earlier:
        if normalise_email(record["data"].get(key)) == email:
            return {"level": "clear", "reason": "email", "record": record}
    fields = all_fields(schema)
    name = _name_of(fields, answers)
    for record in earlier:
        theirs = normalise_email(record["data"].get(key))
        similar = not name or name_similarity(name, _name_of(fields, record["data"])) >= 0.75
        if theirs and _emails_near(email, theirs) and similar:
            return {"level": "likely", "reason": "email_similar", "record": record}
    return {"level": "none"}


def mask_email(value: Any) -> str:
    """"sa•••@yahoo.com": enough to recognise your own email, never enough to learn someone else's."""
    email = js.trim(value) if isinstance(value, str) else ""
    parts = email.split("@")
    local, domain = parts[0], parts[1] if len(parts) > 1 else ""
    if not local or not domain:
        return ""
    return f"{local[:2]}•••@{domain}"


# ── Forms in several languages (translations.ts) ────────────────────────────────

_TEXT_PROPS = ("text", "html", "description", "min_label", "max_label", "link_label", "alt", "caption")
_LITERAL = re.compile(r'"([^"\\]*)"')


def main_language(schema: dict[str, Any] | None) -> str:
    main = ((schema or {}).get("settings") or {}).get("language")
    main = "en" if js.nullish(main) else main
    return main if main in APP_LOCALE_CODES else "en"


def form_languages(schema: dict[str, Any] | None) -> list[str]:
    """Languages the form offers: its main language first, then the others."""
    main = main_language(schema)
    out = [main]
    for code in ((schema or {}).get("settings") or {}).get("languages") or []:
        if code != main and code in APP_LOCALE_CODES and code not in out:
            out.append(code)
    return out


def _walk_literals(formula: str, key: str, visit: Callable[[str, str], str]) -> str:
    n = 0

    def swap(match: re.Match[str]) -> str:
        nonlocal n
        whole, inner, at = match.group(0), match.group(1), match.start()
        before = js.trim_end(formula[:at])[-1:]
        after = js.trim_start(formula[at + len(whole):])[:1]
        if not inner or (before or " ") in "=<>!" or (after or " ") in "=<>!":
            return whole
        out = f'"{visit(f"{key}.{n}", inner)}"'
        n += 1
        return out
    return _LITERAL.sub(swap, formula)


def walk_texts(schema: dict[str, Any], visit: Callable[[str, str], str]) -> None:
    """Every readable text of a form with its key; `visit` returns the replacement (in place)."""
    def swap(holder: Any, prop: str, key: str) -> None:
        if isinstance(holder, dict) and isinstance(holder.get(prop), str) and holder[prop]:
            holder[prop] = visit(key, holder[prop])
    settings = schema.get("settings")
    swap(settings, "title", "form.title")
    guide = settings.get("guide") if isinstance(settings, dict) else None
    swap(guide, "title", "guide.title")
    swap(guide, "html", "guide.html")
    theme = schema.get("theme")
    swap(theme.get("header") if isinstance(theme, dict) else None, "subtitle", "header.subtitle")
    for page in schema.get("pages", []):
        swap(page, "title", f"page.{page['id']}.title")
        for row in page.get("rows", []):
            for fld in row.get("fields", []):
                at = f"field.{fld['id']}"
                swap(fld, "label", f"{at}.label")
                swap(fld, "help", f"{at}.help")
                swap(fld, "placeholder", f"{at}.placeholder")
                for option in fld.get("options") or []:
                    swap(option, "label", f"{at}.option.{option.get('value')}")
                swap(fld.get("validation"), "pattern_message", f"{at}.pattern_message")
                props = fld.get("props")
                if not isinstance(props, dict):
                    continue
                for name in _TEXT_PROPS:
                    swap(props, name, f"{at}.{name}")
                if isinstance(props.get("rows"), list):
                    props["rows"] = [visit(f"{at}.row.{i}", r) if isinstance(r, str) and r else r
                                     for i, r in enumerate(props["rows"])]
                if isinstance(props.get("formula"), str):
                    props["formula"] = _walk_literals(props["formula"], f"{at}.formula", visit)
    swap(schema.get("thank_you"), "title", "thanks.title")
    swap(schema.get("thank_you"), "message", "thanks.message")


def translate_schema(schema: dict[str, Any], language: str) -> dict[str, Any]:
    """The form as respondents see it in one of its languages: translated texts swapped in, the rest in the main
    language. The main language (or one the form doesn't offer) = the form itself."""
    if language == main_language(schema) or language not in form_languages(schema):
        return schema
    saved = ((schema.get("translations") or {}).get(language)) or {}
    out = copy.deepcopy(schema)

    def visit(key: str, text: str) -> str:
        value = saved.get(key)
        return js.trim(value) if isinstance(value, str) and js.trim(value) else text
    walk_texts(out, visit)
    settings = out.get("settings") or {}
    saved_title = saved.get("form.title")
    title = settings.get("title") or (js.trim(saved_title) if isinstance(saved_title, str) else None)
    out["settings"] = {**settings, "language": language, **({"title": title} if title else {})}
    return out


# ── Long lists on the public page (options.ts) ──────────────────────────────────

REMOTE_FROM = 20


def served_remotely(fld: dict[str, Any]) -> bool:
    """Options served by the server on the public page (not sent with the form)."""
    return fld.get("type") in ("dropdown", "multi_select", "radio", "checkbox") and (
        bool(fld.get("options_large")) or (not fld.get("option_parent") and len(fld.get("options") or []) > REMOTE_FROM))


def _fold(text: str) -> str:
    return re.sub(r"[̀-ͯ]", "", unicodedata.normalize("NFKD", text)).lower()


def match_options(options: list[dict[str, Any]], q: str, limit: int = 50) -> dict[str, Any]:
    """Options whose label contains `q` (case and accents ignored), those that start with it first."""
    wanted = _fold(js.trim(q))[:100]
    if not wanted:
        return {"items": options[:limit], "total": len(options)}
    matches = [o for o in options if wanted in _fold(o["label"])]
    first = [o for o in matches if _fold(o["label"]).startswith(wanted)]
    rest = [o for o in matches if not _fold(o["label"]).startswith(wanted)]
    return {"items": (first + rest)[:limit], "total": len(matches)}


def lookup_options(options: list[dict[str, Any]], q: str = "", values: list[str] | None = None,
                   parents: list[str] | None = None) -> dict[str, Any]:
    under = set(parents) if parents is not None else None
    pool = [{"value": o["value"], "label": o["label"], **({"attrs": o["attrs"]} if o.get("attrs") else {})}
            for o in options if under is None or ("parent" in o and o["parent"] in under)]
    if values is not None:
        wanted = set(values)
        return {"items": [o for o in pool if o["value"] in wanted], "total": len(values)}
    return match_options(pool, q)


# ── File types (file-types.ts) ──────────────────────────────────────────────────

FILE_FAMILIES = {
    "image/*": ("image/*", ".jpg", ".jpeg", ".png", ".gif", ".webp", ".avif", ".heic", ".heif", ".bmp", ".tif", ".tiff",
                ".svg", ".ico", ".raw", ".cr2", ".nef", ".arw", ".dng", ".psd", ".ai", ".eps", ".xcf", ".jxl"),
    "audio/*": ("audio/*", ".mp3", ".wav", ".m4a", ".aac", ".ogg", ".oga", ".opus", ".flac", ".aiff", ".wma", ".amr",
                ".mid", ".midi"),
    "video/*": ("video/*", ".mp4", ".mov", ".avi", ".mkv", ".webm", ".wmv", ".flv", ".m4v", ".3gp", ".mpeg", ".mpg",
                ".ogv", ".mts"),
}
PICTURE_TYPES = ("image/*", ".jpg", ".jpeg", ".png", ".gif", ".webp", ".avif", ".heic", ".heif", ".bmp", ".tif", ".tiff")


def normalise_file_type(raw: str) -> str | None:
    value = js.trim(raw).lower()
    if re.fullmatch(r"[a-z0-9-]+/(\*|[a-z0-9.+-]+)", value):
        return value
    ext = re.sub(r"^\*?\.", "", value)
    return f".{ext}" if re.fullmatch(r"[a-z0-9][a-z0-9+_-]{0,15}", ext) else None


def parse_accept(accept: Any) -> list[str]:
    text = "" if js.nullish(accept) else js.to_string(accept)
    return [t for t in (normalise_file_type(item) for item in text.split(",")) if t]


def non_picture_types(accept: Any) -> list[str]:
    return [t for t in parse_accept(accept)
            if t not in PICTURE_TYPES and not (t.startswith("image/") and t != "image/svg+xml")]


def picture_accept(accept: Any) -> str:
    kept = [t for t in parse_accept(accept) if not non_picture_types(t)]
    return ",".join(kept) if kept else "image/*"


def _extension(name: str) -> str:
    found = re.search(r"\.[a-z0-9]+$", name)
    return found.group(0) if found else ""


def accepts_file(accept: Any, name: str, content_type: str) -> bool:
    types = parse_accept(accept)
    if not types:
        return True
    lower, mime = name.lower(), content_type.lower()
    extension = _extension(lower)
    unlabelled = not mime or mime == "application/octet-stream"

    def fits(t: str) -> bool:
        if t.startswith("."):
            return lower.endswith(t)
        if t.endswith("/*"):
            return mime.startswith(t[:-1]) or (unlabelled and extension in FILE_FAMILIES.get(t, ()))
        return mime == t
    return any(fits(t) for t in types)


def looks_like_picture(name: str, content_type: str) -> bool:
    return (content_type.startswith("image/") and content_type != "image/svg+xml") or (
        (not content_type or content_type == "application/octet-stream") and _extension(name.lower()) in PICTURE_TYPES)


# ── The same answers twice (responseStore.ts fingerprintOf) ─────────────────────

def fingerprint_of(answers: dict[str, Any]) -> str:
    stable = [[key, js.trim(answers[key]).lower() if isinstance(answers[key], str) else answers[key]]
              for key in sorted(answers, key=js.utf16_key)]
    return hashlib.sha256(js.stringify(stable).encode("utf-8")).hexdigest()
