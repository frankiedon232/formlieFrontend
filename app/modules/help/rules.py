"""The help centre's rules (F25), ported from the frontend with parity (tests/parity/test_help_rules.py):

- shared/types/help.ts `HELP_CATEGORIES`, shared/utils/help/categories.ts (icons, `helpArticlePath`),
  shared/utils/help/routes.ts `routeMatches`;
- the mock's search rules (server/mock/routes/help.ts): `words`, the little words `STOP`, the snippet and
  `answerFor`; helpStore.ts `articleText`.

`search_terms` is the backend's own: the mock's words, but whole words in every script (the mock's NFKD splits
Arabic, Indic and Japanese words at their combining marks) and Chinese and Japanese runs as pairs of characters
plus the whole run (they have no spaces between words). PostgreSQL full text search matches them (app/modules/help/search.py).
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any

from app.core.js import utf16_len, utf16_slice

HELP_CATEGORIES = ("start", "forms", "builder", "design", "templates", "sharing", "responses", "analytics", "lists",
                   "data", "api", "people", "settings", "audit", "ai")

HELP_CATEGORY_ICONS = {
    "start": "i-lucide-rocket",
    "forms": "i-lucide-file-text",
    "builder": "i-lucide-layout-panel-top",
    "design": "i-lucide-palette",
    "templates": "i-lucide-layout-template",
    "sharing": "i-lucide-share-2",
    "responses": "i-lucide-inbox",
    "analytics": "i-lucide-chart-line",
    "lists": "i-lucide-list",
    "data": "i-lucide-database",
    "api": "i-lucide-boxes",
    "people": "i-lucide-users",
    "settings": "i-lucide-settings",
    "audit": "i-lucide-scroll-text",
    "ai": "i-lucide-sparkles",
}

# Little words (how, do, a, my …) don't decide what an answer is about; kept only if nothing else is left
STOP = frozenset(("a an and are as at be by can do does for from get how i in is it me my of on or our the their there "
                  "this to was we what when where which who why will with you your").split(" "))

_ACCENTS = re.compile("[̀-ͯ]")
_JS_WORD = "A-Za-z0-9_"
# JavaScript's \b without the u flag: a boundary between an ASCII word character and anything else
_B = f"(?:(?<=[{_JS_WORD}])(?![{_JS_WORD}])|(?<![{_JS_WORD}])(?=[{_JS_WORD}]))"
_HOW = re.compile(_B + r"(how|where|steps?|create|add|make|set|change|wie|comment|cómo|como|come|hoe|jak|как|як)" + _B,
                  re.IGNORECASE)
# Sentence ends (`/(?<=[.!?])\s+/`; JavaScript's \s)
_SENTENCES = re.compile(r"(?<=[.!?])[\t\n\v\f\r    -     　﻿]+")


def help_article_path(article: dict[str, Any]) -> str:
    """An article's address in the portal: /help/{area}/{article}."""
    return f"/help/{article['category']}/{article['id']}"


def route_matches(pattern: str, path: str) -> bool:
    """Help content is tied to pages by address patterns: `/forms/:id/build` matches any form's builder.
    (The pattern is a regular expression like the frontend's: `^pattern/?$`, `$` only at the very end.)"""
    try:
        return re.search("^" + re.sub(r":[a-z]+", "[^/]+", pattern) + r"/?\Z", path) is not None
    except re.error:
        return False


def _letters_or_numbers(char: str) -> bool:
    return unicodedata.category(char)[0] in "LN"


def _split(text: str, keep: Any) -> list[str]:
    parts, current = [], []
    for char in text:
        if keep(char):
            current.append(char)
        else:
            parts.append("".join(current))
            current = []
    parts.append("".join(current))
    return parts


def words(text: str) -> list[str]:
    """The mock's words: lower case, accents off (NFKD), split at anything not a letter or digit, 2 or more long."""
    folded = _ACCENTS.sub("", unicodedata.normalize("NFKD", text.lower()))
    return [word for word in _split(folded, _letters_or_numbers) if utf16_len(word) > 1]


def asked_words(found: list[str]) -> list[str]:
    meaningful = [word for word in found if word not in STOP]
    return meaningful or found


def fold(text: str) -> str:
    """What the search compares: lower case, Latin accents off, then composed again (NFC) so letters with their
    own marks (Arabic hamza, Indic vowel signs, Japanese voicing marks, Hangul) stay whole. The database folds
    the content the same way (platform.help_fold)."""
    return unicodedata.normalize("NFC", _ACCENTS.sub("", unicodedata.normalize("NFKD", text.lower())))


def _cjk(char: str) -> bool:
    code = ord(char)
    return (0x3040 <= code <= 0x30FF or 0x3400 <= code <= 0x4DBF or 0x4E00 <= code <= 0x9FFF
            or 0xF900 <= code <= 0xFAFF or 0x20000 <= code <= 0x2FA1F)


def is_cjk(word: str) -> bool:
    return any(_cjk(char) for char in word)


def search_terms(text: str) -> list[str]:
    """The words a search looks for: whole words in every script (letters, digits and their marks), Chinese and
    Japanese runs as overlapping pairs of characters plus the whole run, the little words dropped unless nothing
    else is left."""
    found: list[str] = []
    for word in _split(fold(text), lambda c: unicodedata.category(c)[0] in "LNM"):
        if not word:
            continue
        if not is_cjk(word):
            if utf16_len(word) > 1:
                found.append(word)
            continue
        run, kind = "", None
        for char in word + "\0":
            this = _cjk(char) if char != "\0" else None
            if this != kind and run:
                if kind and len(run) >= 2:
                    found.extend(run[i:i + 2] for i in range(len(run) - 1))
                    if len(run) > 2:
                        found.append(run)  # the whole run too: an exact phrase counts more
                elif not kind and utf16_len(run) > 1:
                    found.append(run)
                run = ""
            run += char
            kind = this
    return asked_words(found)


def block_text(block: dict[str, Any]) -> str:
    if "text" in block:
        return block["text"]
    if "items" in block:
        return " ".join(block["items"])
    if "label" in block:
        return block["label"]
    if "caption" in block:
        return block["caption"]
    return ""


def article_text(blocks: list[dict[str, Any]]) -> str:
    """The readable text of an article (for search and snippets)."""
    return " ".join(block_text(block) for block in blocks).replace("**", "")


def snippet(text: str, asked: list[str], summary: str) -> str:
    """The first sentence holding a word that was asked for, else the summary; at most 200 characters."""
    sentence = next((part for part in _SENTENCES.split(text) if any(word in part.lower() for word in asked)), summary)
    return utf16_slice(sentence, 200)


def answer_for(q: str, asked: list[str], article: dict[str, Any] | None,
               summary: dict[str, Any] | None) -> dict[str, Any] | None:
    """The short answer from the best article: its steps for a "how" question, else its paragraph matching the
    question best and what follows it (headings, links and media left out)."""
    if not article or len(asked) < 1:
        return None
    blocks = article["blocks"]
    steps = next((block for block in blocks if block.get("type") == "steps"), None)
    if _HOW.search(q) and steps:
        return {"article": summary, "blocks": [steps]}
    best: tuple[int, int] | None = None
    for index, block in enumerate(blocks):
        value = sum(1 for word in asked if word in block["text"].lower()) if "text" in block else 0
        if value > 0 and (best is None or value > best[1]):
            best = (index, value)
    at = best[0] if best else next((i for i, block in enumerate(blocks) if block.get("type") == "p"), -1)
    if at < 0:
        return None
    return {"article": summary,
            "blocks": [block for block in blocks[at:at + 2] if block.get("type") not in ("h", "show", "media")]}
