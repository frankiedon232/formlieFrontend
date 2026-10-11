"""Form slugs (mock: data/formStore.ts slugify, uniqueSlug)."""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable


def slugify(value: str) -> str:
    """Lower case, accents dropped, anything else a dash, at most 60 characters; 'form' when nothing is left."""
    text = unicodedata.normalize("NFKD", value.lower())
    text = re.sub(r"[̀-ͯ]", "", text)
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = re.sub(r"(^-|-$)", "", text)
    return text[:60] or "form"


def unique_slug(name: str, taken: Iterable[str]) -> str:
    """A slug not used by another form of this workspace (`name`, `name-2`, …)."""
    used = set(taken)
    base = slugify(name)
    if base not in used:
        return base
    n = 2
    while f"{base}-{n}" in used:
        n += 1
    return f"{base}-{n}"
