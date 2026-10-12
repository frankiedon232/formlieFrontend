"""The stand-in's writing help: ports of the mock's server/mock/ai/writing.ts (rewrite, readingAge) and translator.ts.

  rewrite(text, tone)   plain words for officialese, long sentences split, all-capitals calmed, and the tone asked
                        for (friendly adds "please" to instructions, formal drops contractions)
  reading_age(texts)    an estimate (Flesch-Kincaid grade + 5) to show the effect
  translator_for(code)  Formalie's own translations (template content, everyday form words, the builder's texts):
                        a text it knows (ignoring case and end punctuation) is translated, anything else is left
                        for the model (or a person), never guessed word by word.

Difference from the mock: its translator also reads the portal's interface texts (the frontend's i18n files, not in
the backend); here the model translates what the dictionary doesn't know.
"""

from __future__ import annotations

import re
from functools import lru_cache
from typing import Callable

from app.core import js
from app.modules.ai.engine_forms import I, rx

PLAIN: list[tuple[re.Pattern[str], str]] = [(rx(p, I), r) for p, r in [
    (r"\butili[sz]e\b", "use"), (r"\bcommence\b", "start"), (r"\bprior to\b", "before"), (r"\bin order to\b", "to"),
    (r"\bterminate\b", "end"), (r"\bsufficient\b", "enough"), (r"\bapproximately\b", "about"), (r"\bpurchase\b", "buy"),
    (r"\bendeavou?r\b", "try"), (r"\badditional\b", "more"), (r"\bdemonstrate\b", "show"), (r"\bfacilitate\b", "help"),
    (r"\bindividuals\b", "people"), (r"\bindividual\b", "person"), (r"\bobtain\b", "get"), (r"\bregarding\b", "about"),
    (r"\bin the event that\b", "if"), (r"\bat this point in time\b", "now"), (r"\bwhilst\b", "while"),
    (r"\bnumerous\b", "many"), (r"\bascertain\b", "find out"), (r"\bin respect of\b", "about"),
    (r"\bin accordance with\b", "under"), (r"\bkindly\b", "please"), (r"\bstate\b(?= (your|the|whether))", "tell us"),
    (r"\bprovide details of\b", "tell us about"), (r"\bis required to be\b", "must be"),
    (r"\bit is requested that you\b", "please"),
]]
CONTRACTIONS: list[tuple[re.Pattern[str], str]] = [(rx(p, I), r) for p, r in [
    (r"\bdon['’]t\b", "do not"), (r"\bcan['’]t\b", "cannot"), (r"\bwon['’]t\b", "will not"), (r"\bisn['’]t\b", "is not"),
    (r"\baren['’]t\b", "are not"), (r"\bdidn['’]t\b", "did not"), (r"\bwe['’]ll\b", "we will"),
    (r"\byou['’]ll\b", "you will"), (r"\bwe['’]re\b", "we are"), (r"\byou['’]re\b", "you are"), (r"\bit['’]s\b", "it is"),
]]
_IMPERATIVE = rx(r"^(enter|give|tell|choose|select|pick|add|upload|describe|list|write|provide|confirm|sign)\b", I)
_PASSIVE = rx(r"\b(is|are|was|were|be) (required|expected|requested)\b", I)
_LETTER = re.compile(r"[^\W\d_]")


def _keep_case(original: str, replacement: str) -> str:
    return replacement[0].upper() + replacement[1:] if original[:1] == original[:1].upper() else replacement


def words(text: str) -> list[str]:
    return [w for w in re.split(r"\s+", text) if _LETTER.search(w)]


def rewrite(text: str, tone: str, english: bool = True) -> dict[str, object]:
    """A plainer version of one text in the tone asked for, with why it changed (unchanged = no reasons)."""
    reasons: dict[str, None] = {}
    out = text
    if js.utf16_len(out) > 6 and out == out.upper() and _LETTER.search(out):
        out = out[:1] + out[1:].lower()
        reasons["caps"] = None
    for pattern, plain in PLAIN if english else []:
        if pattern.search(out):
            out = pattern.sub(lambda m, plain=plain: _keep_case(m.group(0), plain), out)
            reasons["plain_words"] = None

    def sentence_of(sentence: str) -> str:
        if len(words(sentence)) <= 25:
            return sentence
        parts = re.split(r";\s+|,\s+and\s+", sentence)
        if len(parts) < 2:
            return sentence
        reasons["long_sentence"] = None
        return " ".join(re.sub(r"[.;,]?\Z", ".", (p[:1].upper() + p[1:]) if i else p, count=1)
                        for i, p in enumerate(parts))
    out = " ".join(sentence_of(s) for s in re.split(r"(?<=[.!?])\s+", out))
    if _PASSIVE.search(out):
        reasons["passive"] = None
    if english and tone == "friendly" and _IMPERATIVE.search(out) and not rx(r"^please\b", I).search(out):
        out = f"Please {out[:1].lower()}{out[1:]}"
        reasons["tone_friendly"] = None
    if english and tone == "formal":
        for pattern, full in CONTRACTIONS:
            if pattern.search(out):
                out = pattern.sub(lambda m, full=full: _keep_case(m.group(0), full), out)
                reasons["tone_formal"] = None
    return {"text": out, "reasons": [] if out == text else list(reasons)}


def _syllables(word: str) -> int:
    w = re.sub(r"[^a-z]", "", word.lower())
    if not w:
        return 0
    w = re.sub(r"^y", "", re.sub(r"(?:[^laeiouy]es|ed|[^laeiouy]e)$", "", w, count=1), count=1)
    groups = re.findall(r"[aeiouy]{1,2}", w)
    return max(1, len(groups) if groups else 1)


def reading_age(texts: list[str]) -> int:
    """Reading age (years) of a set of texts: Flesch-Kincaid grade + 5, at least 6."""
    every = re.sub(r"<[^>]+>", " ", " ".join(texts))
    found = words(every)
    if not found:
        return 6
    sentences = max(1, sum(max(1, len([p for p in re.split(r"[.!?]+\s", re.sub(r"<[^>]+>", " ", t)) if words(p)]))
                           for t in texts))
    grade = 0.39 * (len(found) / sentences) + 11.8 * (sum(_syllables(w) for w in found) / len(found)) - 15.59
    return max(6, int(js.math_round(grade + 5)))


# ── Translating with Formalie's own dictionaries (translator.ts) ──────────────

_END = re.compile(r"[\s?:.!*]+$")


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", js.trim(text).lower())


@lru_cache(maxsize=32)
def _dictionary(code: str) -> dict[str, str]:
    from app.modules.templates.catalogue import translation_dict

    return {_norm(en): local for en, local in (translation_dict(code) or {}).items()}


def translator_for(code: str) -> Callable[[str], str | None]:
    """Translate one text into `code`, or None when Formalie's dictionaries don't know it."""
    known = None if code == "en" else _dictionary(code)

    def translate(text: str) -> str | None:
        if not known or not js.trim(text):
            return None
        exact = known.get(_norm(text))
        if exact:
            return exact
        ending = _END.search(text)
        core = known.get(_norm(_END.sub("", text, count=1)))
        if core:
            return f"{_END.sub('', core, count=1)}{js.trim(ending.group(0)) if ending else ''}"
        return None
    return translate
