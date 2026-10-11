"""JavaScript's own answers for the few operations ported rules rely on (shared/utils/forms/*): `String(x)`,
`Number(x)`, `Math.round`, text comparison by UTF-16 code units, `trim()`. Answers arrive as JSON, so values are
None (null), bool, int, float, str, list or dict; `UNDEFINED` stands for a missing value where it matters.
"""

from __future__ import annotations

import math
import re
from typing import Any


class _Undefined:
    def __repr__(self) -> str:
        return "undefined"

    def __bool__(self) -> bool:
        return False


UNDEFINED: Any = _Undefined()

# String.prototype.trim(): WhiteSpace and LineTerminator
_WS = "\t\n\v\f\r\u0020\u00a0\u1680\u2000\u2001\u2002\u2003\u2004\u2005\u2006\u2007\u2008\u2009\u200a\u2028\u2029\u202f\u205f\u3000\ufeff"
_DECIMAL = re.compile(r"^[+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?$")
_PREFIXED = re.compile(r"^0([xXoObB])([0-9a-fA-F]+)$")


def trim(text: str) -> str:
    return text.strip(_WS)


def trim_start(text: str) -> str:
    return text.lstrip(_WS)


def trim_end(text: str) -> str:
    return text.rstrip(_WS)


def nullish(value: Any) -> bool:
    """`value == null`: null or undefined."""
    return value is None or value is UNDEFINED


def number_to_string(n: float) -> str:
    """Number.prototype.toString(): shortest round-trip digits, exponent from 1e21 and below 1e-6."""
    if isinstance(n, bool):
        return "true" if n else "false"
    if isinstance(n, int) and abs(n) < 2**53:
        return str(n)
    n = float(n)
    if math.isnan(n):
        return "NaN"
    if math.isinf(n):
        return "Infinity" if n > 0 else "-Infinity"
    if n == 0:
        return "0"
    sign = "-" if n < 0 else ""
    digits, exponent = _shortest(abs(n))
    k, point = len(digits), exponent  # value = 0.digits × 10^point
    if k <= point <= 21:
        return sign + digits + "0" * (point - k)
    if 0 < point <= 21:
        return sign + digits[:point] + "." + digits[point:]
    if -6 < point <= 0:
        return sign + "0." + "0" * (-point) + digits
    e = point - 1
    mantissa = digits[0] + ("." + digits[1:] if k > 1 else "")
    return f"{sign}{mantissa}e{'+' if e >= 0 else '-'}{abs(e)}"


def _shortest(x: float) -> tuple[str, int]:
    """Digits and decimal point position (value = 0.digits × 10^point) of the shortest round-trip form; Python's
    repr gives the same digits as JavaScript."""
    from decimal import Decimal

    _, digits, exponent = Decimal(repr(x)).normalize().as_tuple()
    text = "".join(map(str, digits))
    return text, len(text) + int(exponent)


def to_string(value: Any) -> str:
    """String(value)."""
    if value is None:
        return "null"
    if value is UNDEFINED:
        return "undefined"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return number_to_string(value)
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return ",".join("" if nullish(v) else to_string(v) for v in value)
    return "[object Object]"


def to_number(value: Any) -> float:
    """Number(value) (NaN as float('nan'))."""
    if value is None:
        return 0.0
    if value is UNDEFINED:
        return math.nan
    if isinstance(value, bool):
        return 1.0 if value else 0.0
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, list):
        return to_number(to_string(value))
    if isinstance(value, dict):
        return math.nan
    text = trim(str(value))
    if not text:
        return 0.0
    if text in ("Infinity", "+Infinity"):
        return math.inf
    if text == "-Infinity":
        return -math.inf
    prefixed = _PREFIXED.match(text)
    if prefixed:
        base = {"x": 16, "o": 8, "b": 2}[prefixed.group(1).lower()]
        try:
            return float(int(prefixed.group(2), base))
        except ValueError:
            return math.nan
    if _DECIMAL.match(text):
        try:
            return float(text)
        except (ValueError, OverflowError):
            return math.nan
    return math.nan


def is_nan(n: float) -> bool:
    return isinstance(n, float) and math.isnan(n)


def math_round(x: float) -> float:
    """Math.round: the nearest integer, halves toward +∞."""
    if math.isnan(x) or math.isinf(x):
        return x
    low = math.floor(x)
    return float(low + 1 if x - low >= 0.5 else low)


def utf16_key(text: str) -> bytes:
    """Sort / compare key giving JavaScript's `<` on strings (UTF-16 code units)."""
    return text.encode("utf-16-be")


def js_less(a: str, b: str) -> bool:
    return utf16_key(a) < utf16_key(b)


def utf16_len(text: str) -> int:
    return len(text.encode("utf-16-le")) // 2


def stringify(value: Any) -> str:
    """JSON.stringify(value): numbers as JavaScript writes them (7 not 7.0, NaN and Infinity as null), keys in
    their order, undefined left out of objects and null in lists."""
    import json

    if value is None or value is UNDEFINED:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return "null" if isinstance(value, float) and not math.isfinite(value) else number_to_string(value)
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, list):
        return "[" + ",".join(stringify(v) for v in value) + "]"
    if isinstance(value, dict):
        return "{" + ",".join(f"{json.dumps(str(k), ensure_ascii=False)}:{stringify(v)}" for k, v in value.items()
                              if v is not UNDEFINED) + "}"
    return "null"
