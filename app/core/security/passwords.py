"""Passwords: the workspace policy (port of shared/utils/auth/password.ts) and Argon2id hashing (SECURITY-PROTOCOL §8).

Default policy: at least 10 characters, lower and upper case and a number; symbols raise the score when they are
not required. Each workspace sets its own in Settings → Security. A password that misses it is FRM-AUTH-1007.
"""

from __future__ import annotations

import re
from typing import Any, TypedDict

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

PASSWORD_MIN_LENGTH = 10
PASSWORD_LENGTH_RANGE = {"min": 8, "max": 64}


class PasswordPolicy(TypedDict):
    min_length: int
    lower: bool
    upper: bool
    number: bool
    symbol: bool


DEFAULT_PASSWORD_POLICY: PasswordPolicy = {"min_length": PASSWORD_MIN_LENGTH, "lower": True, "upper": True,
                                           "number": True, "symbol": False}

_LOWER, _UPPER, _DIGIT, _SYMBOL = re.compile(r"[a-z]"), re.compile(r"[A-Z]"), re.compile(r"\d"), re.compile(r"[^A-Za-z0-9]")


def _js_length(value: str) -> int:
    """String length as JavaScript counts it (UTF-16 code units), so limits match the frontend exactly."""
    return len(value.encode("utf-16-le")) // 2


def check_password(value: str, policy: PasswordPolicy | dict[str, Any] = DEFAULT_PASSWORD_POLICY) -> list[dict[str, Any]]:
    return [
        {"key": "length", "passed": _js_length(value) >= policy["min_length"], "required": True},
        {"key": "lower", "passed": bool(_LOWER.search(value)), "required": policy["lower"]},
        {"key": "upper", "passed": bool(_UPPER.search(value)), "required": policy["upper"]},
        {"key": "number", "passed": bool(_DIGIT.search(value)), "required": policy["number"]},
        {"key": "symbol", "passed": bool(_SYMBOL.search(value)), "required": policy["symbol"]},
    ]


def password_score(value: str, policy: PasswordPolicy | dict[str, Any] = DEFAULT_PASSWORD_POLICY) -> int:
    """0 (empty) to 4 (strong); meets the policy at 3."""
    if not value:
        return 0
    checks = check_password(value, policy)
    required = [c for c in checks if c["required"]]
    if not all(c["passed"] for c in required):
        return 2 if sum(1 for c in required if c["passed"]) >= max(1, len(required) - 1) else 1
    kinds = sum(1 for c in checks if c["key"] != "length" and c["passed"])
    return 4 if _js_length(value) >= max(14, policy["min_length"] + 4) or kinds == 4 else 3


def meets_password_policy(value: str, policy: PasswordPolicy | dict[str, Any] = DEFAULT_PASSWORD_POLICY) -> bool:
    return all(not c["required"] or c["passed"] for c in check_password(value, policy))


# ── Hashing ────────────────────────────────────────────────────────────────────

_hasher = PasswordHasher()  # Argon2id, library defaults (RFC 9106 low-memory profile)


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password_hash: str | None, password: str) -> bool:
    if not password_hash:
        return False
    try:
        return _hasher.verify(password_hash, password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def needs_rehash(password_hash: str) -> bool:
    return _hasher.check_needs_rehash(password_hash)


# A real Argon2id hash of a random password, checked when an email is unknown so the answer takes as long as for a
# known one (no account discovery by timing).
DUMMY_HASH = _hasher.hash("timing-equaliser-not-a-password")
