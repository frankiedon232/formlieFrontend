"""Calculated fields and list details (port of shared/utils/forms/formula.ts and details.ts), held to the frontend's
answers by tests/parity/test_submission_rules.py. A small, safe formula language, never eval:

    {quantity} * {unit_price}            numbers, + - * / and brackets
    if({plan} = "premium", 50, 10)       conditions: = != > >= < <=, "text" literals
    {size} + {extras}                    choice fields count as their options' numbers (several chosen: the sum)
    round(max({a}, {b}) * 1.2, 2)        if and or not min max sum avg count round floor ceil abs days
    {product.price} * {quantity}         a detail of the chosen list option (several: their sum)

None when the formula is invalid or needs an answer that is still missing.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from datetime import date
from typing import Any

from app.core import js

FORMULA_FUNCTIONS = ("if", "and", "or", "not", "min", "max", "sum", "avg", "count", "days", "round", "floor", "ceil",
                     "abs")
COMPARE = {"=", "==", "!=", "<>", ">", ">=", "<", "<="}
_TOKEN = re.compile(r"\{[a-z][a-z0-9_]*(?:\.[a-z0-9_]+)?\}|\d+(?:\.\d+)?|\"[^\"]*\"|'[^']*'|[a-z_]+|>=|<=|!=|==|<>"
                    r"|[-+*/(),=<>]|[^\t\n\v\f\r \u00a0\u1680\u2000-\u200a\u2028\u2029\u202f\u205f\u3000\ufeff]",
                    re.IGNORECASE | re.ASCII)  # JavaScript: \d is ASCII, \s takes Unicode spaces
_KEYS = re.compile(r"\{([a-z][a-z0-9_]*)(?:\.[a-z0-9_]+)?\}", re.ASCII)
_DETAILS = re.compile(r"\{([a-z][a-z0-9_]*)\.([a-z0-9_]+)\}")


# ── List details (details.ts) ───────────────────────────────────────────────────

def _options_of(fld: dict[str, Any], picked: dict[str, Any] | None) -> list[dict[str, Any]]:
    options = fld.get("options") or []
    return options if options else list((picked or {}).get(fld.get("id"), []))


def _as_number(attr: Any) -> float:
    if isinstance(attr, (int, float)) and not isinstance(attr, bool):
        return float(attr)
    return js.to_number(js.trim(js.to_string(attr)).replace(",", ".", 1))


def _is_number(attr: Any) -> bool:
    return js.trim(js.to_string(attr)) != "" and math.isfinite(_as_number(attr))


def chosen_details(fld: dict[str, Any], answer: Any, column: str, picked: dict[str, Any] | None = None) -> list[Any] | None:
    """The details of the chosen option(s) for one column; None when nothing is chosen."""
    if isinstance(answer, list):
        chosen = [js.to_string(a) for a in answer]
    elif js.nullish(answer) or answer == "":
        chosen = []
    else:
        chosen = [js.to_string(answer)]
    if not chosen:
        return None
    options = _options_of(fld, picked)
    out = []
    for value in chosen:
        option = next((o for o in options if o.get("value") == value), None)
        attr = ((option or {}).get("attrs") or {}).get(column, js.UNDEFINED) if option else js.UNDEFINED
        if attr is not js.UNDEFINED and attr != "":
            out.append(attr)
    return out


def detail_answer(fld: dict[str, Any], answer: Any, column: str, picked: dict[str, Any] | None = None) -> Any:
    """What a condition on a detail tests: a number, a text, a list of texts (several chosen) or None."""
    details = chosen_details(fld, answer, column, picked)
    if not details:
        return None
    if all(_is_number(d) for d in details):
        return sum((_as_number(d) for d in details), 0.0)
    return [js.to_string(d) for d in details] if isinstance(answer, list) else js.to_string(details[0])


# ── Parsing ─────────────────────────────────────────────────────────────────────

def _tokenize(formula: str) -> list[str]:
    return _TOKEN.findall(formula)


def parse_formula(formula: str) -> tuple:
    """A tree of tuples: ('num', v) ('str', v) ('ref', key, detail) ('neg', a) ('bin', op, a, b) ('call', name, args).
    Raises ValueError on any syntax error."""
    tokens = _tokenize(formula)
    pos = 0

    def peek() -> str | None:
        return tokens[pos] if pos < len(tokens) else None

    def take() -> str | None:
        nonlocal pos
        token = peek()
        pos += 1
        return token

    def expect(t: str) -> None:
        if take() != t:
            raise ValueError(f"expected {t}")

    def primary() -> tuple:
        token = take()
        if token is None:
            raise ValueError("end")
        if token == "(":
            node = comparison()
            expect(")")
            return node
        if token == "-":
            return ("neg", primary())
        if token[0] in "0123456789":
            return ("num", float(token))
        if token[0] in "\"'":
            return ("str", token[1:-1])
        if token.startswith("{"):
            key, _, detail = token[1:-1].partition(".")
            return ("ref", key, detail or None)
        name = token.lower()
        if name in FORMULA_FUNCTIONS and peek() == "(":
            take()
            args: list[tuple] = []
            if peek() != ")":
                args.append(comparison())
                while peek() == ",":
                    take()
                    args.append(comparison())
            expect(")")
            return ("call", name, args)
        raise ValueError(f"token {token}")

    def product() -> tuple:
        node = primary()
        while peek() in ("*", "/"):
            op = take()
            node = ("bin", op, node, primary())
        return node

    def total() -> tuple:
        node = product()
        while peek() in ("+", "-"):
            op = take()
            node = ("bin", op, node, product())
        return node

    def comparison() -> tuple:
        node = total()
        while peek() is not None and peek() in COMPARE:
            op = take()
            node = ("bin", op, node, total())
        return node

    if not tokens:
        raise ValueError("empty")
    tree = comparison()
    if pos != len(tokens):
        raise ValueError("trailing")
    return tree


def is_valid_formula(formula: str) -> bool:
    try:
        parse_formula(formula)
        return True
    except (ValueError, RecursionError):
        return False


def formula_keys(formula: str) -> list[str]:
    return _KEYS.findall(formula)


def formula_details(formula: str) -> list[dict[str, str]]:
    return [{"key": k, "detail": d} for k, d in _DETAILS.findall(formula)]


# ── Evaluating ──────────────────────────────────────────────────────────────────

@dataclass
class Value:
    n: float | None
    s: list[str] = field(default_factory=list)
    literal: bool = False


class Missing(Exception):
    pass


class _Error(Exception):
    pass


def _num(n: float) -> Value:
    return Value(n, [js.number_to_string(n)])


def _resolve(key: str, answers: dict[str, Any], fields: dict[str, Any] | None, detail: str | None,
             picked: dict[str, Any] | None) -> Value:
    raw = answers.get(key, js.UNDEFINED)
    if js.nullish(raw) or raw == "" or (isinstance(raw, list) and not raw):
        raise Missing(key)
    fld = (fields or {}).get(key)
    if detail:
        details = chosen_details(fld, raw, detail, picked) if fld else None
        if not details:
            raise Missing(key)
        numbers = [float(a) if isinstance(a, (int, float)) and not isinstance(a, bool)
                   else js.to_number(js.to_string(a).replace(",", ".", 1)) for a in details]
        ok = all(math.isfinite(n) for n in numbers)
        return Value(sum(numbers, 0.0) if ok else None, [js.to_string(a) for a in details])
    options = (fld or {}).get("options") or []
    scored = any(isinstance(o.get("score"), (int, float)) and not isinstance(o.get("score"), bool) for o in options)
    if isinstance(raw, list):
        wanted = [js.to_string(r) for r in raw]
        chosen = [o for o in options if o.get("value") in wanted]
        n = float(sum(_score(o) for o in chosen)) if scored else float(len(raw))
        return Value(n, [t for o in chosen for t in (o.get("value"), o.get("label"))])  # type: ignore[misc]
    if options:
        option = next((o for o in options if o.get("value") == js.to_string(raw)), None)
        if scored:
            n: float | None = _score(option) if option else 0.0
        else:
            parsed = js.to_number(raw)
            n = None if js.is_nan(parsed) else parsed
        return Value(n, [option.get("value"), option.get("label")] if option else [js.to_string(raw)])  # type: ignore[list-item]
    if isinstance(raw, bool):
        return Value(1.0 if raw else 0.0, [js.to_string(raw)])
    parsed = float(raw) if isinstance(raw, (int, float)) else js.to_number(raw)
    return Value(None if js.is_nan(parsed) else parsed, [js.to_string(raw)])


def _score(option: dict[str, Any] | None) -> float:
    score = (option or {}).get("score")
    return float(score) if isinstance(score, (int, float)) and not isinstance(score, bool) else 0.0


def _days(text: str) -> float:
    """Date.parse of a `YYYY-MM-DD` (date-only ISO: UTC midnight), NaN otherwise."""
    m = re.fullmatch(r"([+-]\d{6}|\d{4})(?:-(\d{2})(?:-(\d{2}))?)?", text)
    if not m:
        return math.nan
    try:
        year = int(m.group(1))
        day = date(year, int(m.group(2) or 1), int(m.group(3) or 1))
    except ValueError:
        return math.nan
    return float((day - date(1970, 1, 1)).days) * 86_400_000


def _evaluate(node: tuple, answers: dict[str, Any], fields: dict[str, Any] | None, picked: dict[str, Any] | None) -> Value:
    def ev(n: tuple) -> Value:
        return _evaluate(n, answers, fields, picked)

    def number(n: tuple) -> float:
        value = ev(n).n
        if value is None:
            raise _Error("not a number")
        return value

    def answered(nodes: list[tuple]) -> list[float]:
        out = []
        for n in nodes:
            try:
                value = ev(n).n
            except Missing:
                continue
            if value is not None:
                out.append(value)
        return out

    def some(nodes: list[tuple]) -> list[float]:
        values = answered(nodes)
        if not values:
            raise Missing("all")
        return values

    kind = node[0]
    if kind == "num":
        return _num(node[1])
    if kind == "str":
        text = node[1]
        parsed = js.to_number(text)
        return Value(None if js.is_nan(parsed) or text == "" else parsed, [text], literal=True)
    if kind == "ref":
        return _resolve(node[1], answers, fields, node[2], picked)
    if kind == "neg":
        return _num(-number(node[1]))
    if kind == "bin":
        op = node[1]
        if op in COMPARE:
            a, b = ev(node[2]), ev(node[3])
            if op in ("=", "==", "!=", "<>"):
                textual = a.literal or b.literal or a.n is None or b.n is None
                same = (any(x.lower() == y.lower() for x in a.s for y in b.s) if textual else a.n == b.n)
                return _num(1 if (op in ("!=", "<>")) != same else 0)
            if a.n is None or b.n is None:
                raise _Error("not a number")
            result = a.n > b.n if op == ">" else a.n >= b.n if op == ">=" else a.n < b.n if op == "<" else a.n <= b.n
            return _num(1 if result else 0)
        x, y = number(node[2]), number(node[3])
        if op == "+":
            return _num(x + y)
        if op == "-":
            return _num(x - y)
        if op == "*":
            return _num(x * y)
        return _num(_divide(x, y))
    # call
    name, args = node[1], node[2]

    def truthy(n: tuple) -> bool:
        v = ev(n)
        return v.n != 0 if v.n is not None else any(s != "" and s != "false" for s in v.s)
    if name == "if":
        if len(args) != 3:
            raise _Error("if needs 3")
        return ev(args[1]) if truthy(args[0]) else ev(args[2])
    if name == "and":
        return _num(1 if all(truthy(a) for a in args) else 0)
    if name == "or":
        return _num(1 if any(truthy(a) for a in args) else 0)
    if name == "not":
        return _num(0 if args and truthy(args[0]) else 1)
    if name == "min":
        return _num(min(some(args)))
    if name == "max":
        return _num(max(some(args)))
    if name == "sum":
        return _num(_sum(some(args)))
    if name == "avg":
        values = some(args)
        return _num(_sum(values) / len(values))
    if name == "count":
        return _num(float(len(answered(args))))
    if name == "days":
        if len(args) != 2:
            raise _Error("days needs 2")
        start, end = (_days((ev(a).s[0] if ev(a).s else "")[:10]) for a in args)
        if math.isnan(start) or math.isnan(end):
            raise _Error("not a date")
        return _num(js.math_round((end - start) / 86_400_000))
    if name == "abs":
        return _num(abs(number(args[0])))
    if name == "floor":
        return _num(float(math.floor(number(args[0]))) if math.isfinite(number(args[0])) else number(args[0]))
    if name == "ceil":
        return _num(float(math.ceil(number(args[0]))) if math.isfinite(number(args[0])) else number(args[0]))
    if name == "round":
        digits = max(0.0, min(10.0, number(args[1]))) if len(args) > 1 else 0.0
        factor = 10 ** digits
        return _num(js.math_round(number(args[0]) * factor) / factor)
    raise _Error("unknown")


def _sum(values: list[float]) -> float:
    total = 0.0
    for v in values:  # left to right, like reduce (math.fsum would round differently)
        total += v
    return total


def _divide(x: float, y: float) -> float:
    if y == 0:
        if x == 0 or math.isnan(x):
            return math.nan
        return math.copysign(math.inf, x) * math.copysign(1.0, y)
    return x / y


def calculate_result(formula: str, answers: dict[str, Any], fields: dict[str, Any] | None = None,
                     picked: dict[str, Any] | None = None) -> float | str | None:
    """A number (rounded to 6 decimals), a text (e.g. a risk level "High"), or None."""
    try:
        value = _evaluate(parse_formula(formula), answers, fields, picked)
    except (ValueError, Missing, _Error, RecursionError, IndexError, OverflowError):
        return None
    if value.n is None:
        return value.s[0] if value.literal and value.s and value.s[0] else None
    if not math.isfinite(value.n):
        return None
    out = js.math_round(value.n * 1e6) / 1e6
    return 0.0 if out == 0 else out


def calculate(formula: str, answers: dict[str, Any], fields: dict[str, Any] | None = None,
              picked: dict[str, Any] | None = None) -> float | None:
    result = calculate_result(formula, answers, fields, picked)
    return result if isinstance(result, float) else None
