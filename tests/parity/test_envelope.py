"""The envelope against the fixed vectors (tests/vectors/envelope.json). scripts/check_envelope_vectors.py runs the
same vectors through the frontend's own envelope.ts, so both sides are held to the same bytes."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from cryptography.hazmat.primitives.asymmetric import ec

from app.core.security import envelope as env

pytestmark = pytest.mark.parity

VECTORS = json.loads((Path(__file__).parents[1] / "vectors" / "envelope.json").read_text(encoding="utf-8"))
KEY = bytes.fromhex(VECTORS["session_key_hex"])


def test_both_sides_derive_the_same_session_key() -> None:
    server = ec.derive_private_key(int(VECTORS["server_private_scalar"], 16), ec.SECP256R1())
    assert env.raw_public_key(server) == VECTORS["server_public_key"]
    assert env.derive_session_key(server, VECTORS["client_public_key"], VECTORS["salt"]) == KEY


@pytest.mark.parametrize("case", VECTORS["cases"], ids=lambda c: c["name"])
def test_seal_open_and_header_match_the_vectors(case: dict) -> None:
    e = case["envelope"]
    sealed = env.seal(KEY, e["kid"], case["payload"], iv=env.b64decode(e["iv"]), nonce=env.b64decode(e["nonce"]),
                      ts=e["ts"])
    assert sealed == e
    assert env.open_envelope(KEY, e) == case["payload"]
    assert env.encode_header(e) == case["header"]
    assert env.decode_header(case["header"]) == e


def test_anything_altered_fails_to_open() -> None:
    e = VECTORS["cases"][0]["envelope"]
    for field, value in (("ts", e["ts"] + 1), ("nonce", env.b64encode(bytes(16))), ("kid", "another-kid-000"),
                         ("ct", e["ct"][:-4] + ("AAAA" if not e["ct"].endswith("AAAA") else "BBBB"))):
        with pytest.raises(env.EnvelopeError):
            env.open_envelope(KEY, {**e, field: value})
    with pytest.raises(env.EnvelopeError):
        env.open_envelope(bytes(32), e)


def test_freshness_window_is_sixty_seconds() -> None:
    assert env.is_fresh(1_000_000, now_ms=1_060_000) and env.is_fresh(1_060_000, now_ms=1_000_000)
    assert not env.is_fresh(1_000_000, now_ms=1_060_001)


def test_invalid_public_keys_are_refused() -> None:
    server = env.generate_key_pair()
    for bad in ("not base64!", env.b64encode(b"\x04" + bytes(64)), env.b64encode(bytes(33))):
        with pytest.raises(ValueError):
            env.derive_session_key(server, bad, VECTORS["salt"])
