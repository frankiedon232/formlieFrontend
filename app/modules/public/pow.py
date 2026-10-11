"""Invisible spam check for public forms (port of shared/utils/forms/proof-of-work.ts; decision 89): the server hands
out a challenge when the form opens; the browser finds a number whose SHA-256 with the challenge's salt starts with
`difficulty` zero bits. No third-party captcha, no tracking, nothing for people to click."""

from __future__ import annotations

import hashlib


def has_leading_zero_bits(digest: bytes, bits: int) -> bool:
    left = bits
    for byte in digest:
        if left <= 0:
            return True
        if left >= 8:
            if byte != 0:
                return False
            left -= 8
        else:
            return byte >> (8 - left) == 0
    return left <= 0


def check_work(salt: str, difficulty: int, nonce: object) -> bool:
    if not isinstance(nonce, int) or isinstance(nonce, bool) or nonce < 0:
        if not (isinstance(nonce, float) and nonce.is_integer() and nonce >= 0):
            return False
        nonce = int(nonce)
    return has_leading_zero_bits(hashlib.sha256(f"{salt}:{nonce}".encode()).digest(), difficulty)


def solve_work(salt: str, difficulty: int, limit: int = 5_000_000) -> int | None:
    """Tests and tools only (browsers solve it themselves)."""
    for nonce in range(limit):
        if has_leading_zero_bits(hashlib.sha256(f"{salt}:{nonce}".encode()).digest(), difficulty):
            return nonce
    return None
