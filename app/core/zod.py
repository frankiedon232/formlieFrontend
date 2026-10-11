"""A small zod-compatible validator, so the frontend's shared zod schemas are ported one to one (CLAUDE.md rule 17).

The frontend validates with zod (v4) in the browser and the mock validates with the same schemas, answering
FRM-GEN-1002 with each problem's `field` (path joined with dots) and `message`. Porting those schemas to Pydantic
would change the messages, the cleaned values and which problems are reported. This module follows zod's rules
instead: unknown object keys are dropped, every field is checked and every problem reported, transforms and
refinements run only on valid input, and the built-in messages are zod's own ("Too small: expected string to have
>=2 characters"). Each port is held to the answers zod gives (tests/vectors/*_rules.json).

    schema = obj(name=string().trim().min(2).max(80), size=enum(["1-10", "11-50"]).nullable())
    value = schema.parse(body)          # raises FrmError("FRM-GEN-1002", details) on any problem
"""

from __future__ import annotations

import math
import re
from collections.abc import Callable, Sequence
from typing import Any

from app.core.errors import FrmError

# String.prototype.trim(): WhiteSpace and LineTerminator
_JS_SPACE = "".join(chr(c) for c in (0x09, 0x0A, 0x0B, 0x0C, 0x0D, 0x20, 0xA0, 0x1680, *range(0x2000, 0x200B),
                                     0x2028, 0x2029, 0x202F, 0x205F, 0x3000, 0xFEFF))

MISSING: Any = type("Missing", (), {"__repr__": lambda self: "undefined"})()


class _StopChecks(Exception):
    """A format problem that ends the value's other checks."""


class Invalid(Exception):
    """Raised inside parsing when a value can't be used further (the issues are already recorded)."""


def received(value: Any) -> str:
    """zod's name for the type it got."""
    if value is MISSING:
        return "undefined"
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, (int, float)):
        return "NaN" if isinstance(value, float) and math.isnan(value) else "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "array"
    return "object"


def _same(value: Any, option: Any) -> bool:
    """=== in JavaScript: True is not 1, 5.0 is 5."""
    if isinstance(value, bool) or isinstance(option, bool):
        return value is option
    if isinstance(value, (int, float)) and isinstance(option, (int, float)):
        return value == option
    return type(value) is type(option) and value == option


def _quote(value: Any) -> str:
    return f'"{value}"' if isinstance(value, str) else str(value).lower() if isinstance(value, bool) else str(value)


Issues = list[dict[str, str]]
Path = tuple[Any, ...]


def _issue(issues: Issues, path: Path, message: str, *, check: bool = False) -> None:
    """A wrong type stops that value's later checks; a failed check (length, pattern, refinement) does not, as in
    zod, where such issues are "continuable"."""
    issue = {"field": ".".join(str(p) for p in path), "message": message}
    if check:
        issue["_check"] = "1"
    issues.append(issue)


def _aborted(issues: Issues, start: int) -> bool:
    return any("_check" not in issue for issue in issues[start:])


class Schema:
    def __init__(self) -> None:
        self._after: list[tuple[str, Any]] = []  # ("refine", (fn, message, path)) | ("transform", fn)

    # Subclasses: the type and its own checks. Return the value, or raise Invalid after recording issues.
    def _base(self, value: Any, path: Path, issues: Issues) -> Any:
        raise NotImplementedError

    def run(self, value: Any, path: Path, issues: Issues) -> Any:
        start = len(issues)
        out = self._base(value, path, issues)
        for kind, step in self._after:
            if kind == "transform":
                if len(issues) > start:  # a transform never sees a value with problems
                    raise Invalid
                out = step(out)
                continue
            if _aborted(issues, start):
                raise Invalid
            fn, message, at = step
            try:
                passed = fn(out)
            except (KeyError, TypeError, AttributeError):
                passed = True  # a refinement looking at a part that already has its own problem
            if not passed:
                _issue(issues, path + at, message, check=True)
        if len(issues) > start:
            raise Invalid
        return out

    def refine(self, fn: Callable[[Any], bool], message: str = "Invalid input", path: Sequence[Any] = ()) -> Schema:
        self._after.append(("refine", (fn, message, tuple(path))))
        return self

    def transform(self, fn: Callable[[Any], Any]) -> Schema:
        self._after.append(("transform", fn))
        return self

    def nullable(self) -> Schema:
        return Nullable(self)

    def optional(self) -> Schema:
        return Optional(self)

    def parse(self, value: Any) -> Any:
        """The cleaned value, or FRM-GEN-1002 with every problem (field, message), like the mock's parseBody()."""
        ok, result = self.safe_parse(value)
        if not ok:
            raise FrmError("FRM-GEN-1002", result)
        return result

    def safe_parse(self, value: Any) -> tuple[bool, Any]:
        issues: Issues = []
        try:
            return True, self.run(value, (), issues)
        except Invalid:
            return False, [{"field": i["field"], "message": i["message"]} for i in issues]


class Nullable(Schema):
    def __init__(self, inner: Schema) -> None:
        super().__init__()
        self.inner = inner

    def _base(self, value: Any, path: Path, issues: Issues) -> Any:
        if value is None:
            return None
        try:
            return self.inner.run(value, path, issues)
        except Invalid:
            return None


class Optional(Nullable):
    def _base(self, value: Any, path: Path, issues: Issues) -> Any:
        if value is MISSING:
            return MISSING
        try:
            return self.inner.run(value, path, issues)
        except Invalid:
            return None


class String(Schema):
    def __init__(self) -> None:
        super().__init__()
        self._checks: list[Callable[[str, Path, Issues], str]] = []

    def _base(self, value: Any, path: Path, issues: Issues) -> Any:
        if not isinstance(value, str):
            _issue(issues, path, f"Invalid input: expected string, received {received(value)}")
            return None
        for check in self._checks:
            value = check(value, path, issues)
        return value

    def trim(self) -> String:
        self._checks.append(lambda v, p, i: v.strip(_JS_SPACE))
        return self

    def lower(self) -> String:
        self._checks.append(lambda v, p, i: v.lower())
        return self

    def min(self, n: int, message: str | None = None) -> String:
        def check(v: str, p: Path, i: Issues) -> str:
            if _length(v) < n:
                _issue(i, p, message or f"Too small: expected string to have >={n} characters", check=True)
            return v
        self._checks.append(check)
        return self

    def max(self, n: int, message: str | None = None) -> String:
        def check(v: str, p: Path, i: Issues) -> str:
            if _length(v) > n:
                _issue(i, p, message or f"Too big: expected string to have <={n} characters", check=True)
            return v
        self._checks.append(check)
        return self

    def regex(self, pattern: str | re.Pattern[str], message: str | None = None) -> String:
        rx = re.compile(pattern) if isinstance(pattern, str) else pattern

        def check(v: str, p: Path, i: Issues) -> str:
            if not rx.search(v):
                _issue(i, p, message or f"Invalid string: must match pattern /{rx.pattern}/", check=True)
            return v
        self._checks.append(check)
        return self


    def email(self, message: str = "Invalid email address") -> String:
        """z.email() (zod 4's own pattern, app/core/validation.py)."""
        from app.core.validation import ZOD_EMAIL

        def check(v: str, p: Path, i: Issues) -> str:
            if not ZOD_EMAIL.match(v):
                _issue(i, p, message, check=True)
            return v
        self._checks.append(check)
        return self

    def url(self, schemes: Sequence[str] = ("http", "https"), message: str = "Invalid URL") -> String:
        """z.url(), trimmed like zod does, but only web addresses (zod also takes javascript:, mailto: … which a
        page must never link to)."""
        from urllib.parse import urlsplit

        def check(v: str, p: Path, i: Issues) -> str:
            v = v.strip(_JS_SPACE)
            try:
                parts = urlsplit(v)
                good = (parts.scheme.lower() in schemes and bool(parts.hostname) and not any(c.isspace() for c in v)
                        and (parts.port is None or 0 <= parts.port <= 65535))
            except ValueError:
                good = False
            if not good:
                _issue(i, p, message, check=True)
            return v
        self._checks.append(check)
        return self


def _length(value: str) -> int:
    """JavaScript's length: UTF-16 code units (an emoji counts 2)."""
    return len(value.encode("utf-16-le")) // 2


class Number(Schema):
    def __init__(self) -> None:
        super().__init__()
        self._checks: list[Callable[[float, Path, Issues], None]] = []

    def _base(self, value: Any, path: Path, issues: Issues) -> Any:
        if isinstance(value, bool) or not isinstance(value, (int, float)) or (
                isinstance(value, float) and not math.isfinite(value)):
            _issue(issues, path, f"Invalid input: expected number, received {received(value)}")
            return None
        try:
            for check in self._checks:
                check(value, path, issues)
        except _StopChecks:
            pass
        return int(value) if isinstance(value, float) and value.is_integer() else value

    def int(self) -> Number:
        """Not a whole number: that is the only problem reported for it (zod's int is a format, not a check)."""
        def check(v: float, p: Path, i: Issues) -> None:
            if not float(v).is_integer():
                _issue(i, p, "Invalid input: expected int, received number")
                raise _StopChecks
        self._checks.append(check)
        return self

    def min(self, n: float) -> Number:
        def check(v: float, p: Path, i: Issues) -> None:
            if v < n:
                _issue(i, p, f"Too small: expected number to be >={_js(n)}", check=True)
        self._checks.append(check)
        return self

    def positive(self) -> Number:
        def check(v: float, p: Path, i: Issues) -> None:
            if v <= 0:
                _issue(i, p, "Too small: expected number to be >0", check=True)
        self._checks.append(check)
        return self

    def max(self, n: float) -> Number:
        def check(v: float, p: Path, i: Issues) -> None:
            if v > n:
                _issue(i, p, f"Too big: expected number to be <={_js(n)}", check=True)
        self._checks.append(check)
        return self


def _js(n: float) -> str:
    return str(int(n)) if float(n).is_integer() else repr(n)


class Boolean(Schema):
    def _base(self, value: Any, path: Path, issues: Issues) -> Any:
        if not isinstance(value, bool):
            _issue(issues, path, f"Invalid input: expected boolean, received {received(value)}")
        return value


class Enum(Schema):
    def __init__(self, options: Sequence[Any]) -> None:
        super().__init__()
        self.options = list(options)

    def _base(self, value: Any, path: Path, issues: Issues) -> Any:
        if not any(_same(value, o) for o in self.options):
            _issue(issues, path, "Invalid option: expected one of " + "|".join(_quote(o) for o in self.options))
        return value


class Literals(Schema):
    """z.union([z.literal(a), z.literal(b), …]): a value outside them is just "Invalid input"."""

    def __init__(self, options: Sequence[Any]) -> None:
        super().__init__()
        self.options = list(options)

    def _base(self, value: Any, path: Path, issues: Issues) -> Any:
        if not any(_same(value, o) for o in self.options):
            _issue(issues, path, "Invalid input")
        return int(value) if isinstance(value, float) and value.is_integer() else value


class Array(Schema):
    def __init__(self, item: Schema) -> None:
        super().__init__()
        self.item = item
        self._min: tuple[int, str | None] | None = None
        self._max: tuple[int, str | None] | None = None

    def min(self, n: int, message: str | None = None) -> Array:
        self._min = (n, message)
        return self

    def max(self, n: int, message: str | None = None) -> Array:
        self._max = (n, message)
        return self

    def _base(self, value: Any, path: Path, issues: Issues) -> Any:
        if not isinstance(value, list):
            _issue(issues, path, f"Invalid input: expected array, received {received(value)}")
            return None
        out = []
        for index, element in enumerate(value):
            try:
                out.append(self.item.run(element, path + (index,), issues))
            except Invalid:
                pass
        if self._min and len(value) < self._min[0]:
            _issue(issues, path, self._min[1] or f"Too small: expected array to have >={self._min[0]} items", check=True)
        if self._max and len(value) > self._max[0]:
            _issue(issues, path, self._max[1] or f"Too big: expected array to have <={self._max[0]} items", check=True)
        return out


class Object(Schema):
    def __init__(self, shape: dict[str, Schema]) -> None:
        super().__init__()
        self.shape = shape

    def _base(self, value: Any, path: Path, issues: Issues) -> Any:
        if not isinstance(value, dict):
            _issue(issues, path, f"Invalid input: expected object, received {received(value)}")
            return None
        out: dict[str, Any] = {}
        for key, schema in self.shape.items():
            raw = value.get(key, MISSING)
            try:
                parsed = schema.run(raw, path + (key,), issues)
            except Invalid:
                parsed = raw
            if parsed is not MISSING:
                out[key] = parsed
        return out  # unknown keys are dropped


class PartialRecord(Schema):
    """z.partialRecord(z.enum(keys), value): only those keys, each optional."""

    def __init__(self, keys: Sequence[str], value: Schema) -> None:
        super().__init__()
        self.keys = list(keys)
        self.value = value

    def _base(self, value: Any, path: Path, issues: Issues) -> Any:
        if not isinstance(value, dict):
            _issue(issues, path, f"Invalid input: expected record, received {received(value)}")
            return None
        out: dict[str, Any] = {}
        for key, item in value.items():
            if key not in self.keys:
                _issue(issues, path, f'Unrecognized key: "{key}"')
                continue
            try:
                out[key] = self.value.run(item, path + (key,), issues)
            except Invalid:
                pass
        return out


class Preprocess(Schema):
    def __init__(self, fn: Callable[[Any], Any], inner: Schema) -> None:
        super().__init__()
        self.fn, self.inner = fn, inner

    def _base(self, value: Any, path: Path, issues: Issues) -> Any:
        try:
            return self.inner.run(self.fn(value), path, issues)
        except Invalid:
            return None


def string() -> String:
    return String()


def number() -> Number:
    return Number()


def boolean() -> Boolean:
    return Boolean()


def enum(options: Sequence[Any]) -> Enum:
    return Enum(options)


def literals(options: Sequence[Any]) -> Literals:
    return Literals(options)


def array(item: Schema) -> Array:
    return Array(item)


def obj(shape: dict[str, Schema] | None = None, /, **fields: Schema) -> Object:
    return Object({**(shape or {}), **fields})


def partial_record(keys: Sequence[str], value: Schema) -> PartialRecord:
    return PartialRecord(keys, value)


class Record(Schema):
    """z.record(keySchema, valueSchema): a bad key is "Invalid key in record" at that key."""

    def __init__(self, key: Schema, value: Schema) -> None:
        super().__init__()
        self.key, self.value = key, value

    def _base(self, value: Any, path: Path, issues: Issues) -> Any:
        if not isinstance(value, dict):
            _issue(issues, path, f"Invalid input: expected record, received {received(value)}")
            return None
        out: dict[str, Any] = {}
        for key, item in value.items():
            ok, _ = self.key.safe_parse(key)
            if not ok:
                _issue(issues, path + (key,), "Invalid key in record")
                continue
            try:
                out[key] = self.value.run(item, path + (key,), issues)
            except Invalid:
                pass
        return out


class Literal(Schema):
    def __init__(self, value: Any) -> None:
        super().__init__()
        self.value = value

    def _base(self, value: Any, path: Path, issues: Issues) -> Any:
        if not _same(value, self.value):
            _issue(issues, path, f"Invalid input: expected {_quote(self.value)}")
        return value


class Union(Schema):
    """z.union([...]): the first option that takes the value; none → "Invalid input"."""

    def __init__(self, options: Sequence[Schema]) -> None:
        super().__init__()
        self.options = list(options)

    def _base(self, value: Any, path: Path, issues: Issues) -> Any:
        for option in self.options:
            ok, result = option.safe_parse(value)
            if ok:
                return result
        _issue(issues, path, "Invalid input")
        return None


def record(key: Schema, value: Schema) -> Record:
    return Record(key, value)


def literal(value: Any) -> Literal:
    return Literal(value)


def union(options: Sequence[Schema]) -> Union:
    return Union(options)


class Unknown(Schema):
    def _base(self, value: Any, path: Path, issues: Issues) -> Any:
        return value


def unknown() -> Unknown:
    return Unknown()


def preprocess(fn: Callable[[Any], Any], inner: Schema) -> Preprocess:
    return Preprocess(fn, inner)
