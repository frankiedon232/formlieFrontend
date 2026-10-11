"""Writes tests/vectors/envelope.json: fixed keys, salt, iv, nonce and time, and what the envelope must be.

    fmly\\Scripts\\python.exe scripts\\make_envelope_vectors.py

tests/parity/test_envelope.py checks the backend against it; scripts/check_envelope_vectors.py checks the
frontend's own shared/utils/crypto/envelope.ts against it (and the other way round). Test keys only.
"""

from __future__ import annotations

import base64
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cryptography.hazmat.primitives.asymmetric import ec  # noqa: E402

from app.core.security import envelope as env  # noqa: E402

OUT = Path(__file__).resolve().parents[1] / "tests" / "vectors" / "envelope.json"


def _b64url_int(value: int) -> str:
    return base64.urlsafe_b64encode(value.to_bytes(32, "big")).decode().rstrip("=")


def main() -> None:
    client = ec.derive_private_key(0x1F2E3D4C5B6A79880102030405060708090A0B0C0D0E0F101112131415161718, ec.SECP256R1())
    server = ec.derive_private_key(0x2A3B4C5D6E7F8091A2B3C4D5E6F708192A3B4C5D6E7F8091A2B3C4D5E6F70819, ec.SECP256R1())
    salt = env.b64encode(bytes(range(32)))
    key = env.derive_session_key(server, env.raw_public_key(client), salt)
    assert key == env.derive_session_key(client, env.raw_public_key(server), salt)
    numbers = client.private_numbers()

    cases = []
    payloads = [
        ("get with query", {"method": "GET", "path": "/api/v1/forms", "query": {"page": 2, "q": "café ✓"}, "body": None}),
        ("post with body", {"method": "POST", "path": "/api/v1/auth/login", "query": {},
                            "body": {"email": "ada@example.com", "password": "Correct-Horse-9"}}),
        ("reply", {"success": True, "data": {"id": "Xb7QmV2kP0aZr9LwE4tYh1sN3cU", "items": [1, 2.5, None, True]},
                   "meta": {}}),
    ]
    for i, (name, payload) in enumerate(payloads):
        iv = bytes([i + 1] * 12)
        nonce = bytes([0xA0 + i] * 16)
        ts = 1_790_000_000_000 + i
        sealed = env.seal(key, "0190f0b2-1111-4222-8333-444455556666", payload, iv=iv, nonce=nonce, ts=ts)
        cases.append({"name": name, "payload": payload, "envelope": sealed, "header": env.encode_header(sealed)})

    vectors = {
        "about": "Fixed test vectors for the encryption envelope (SECURITY-PROTOCOL 1 to 3). Test keys only.",
        "client_private_jwk": {"kty": "EC", "crv": "P-256", "d": _b64url_int(numbers.private_value),
                               "x": _b64url_int(numbers.public_numbers.x), "y": _b64url_int(numbers.public_numbers.y)},
        "client_public_key": env.raw_public_key(client),
        "server_private_scalar": hex(server.private_numbers().private_value),
        "server_public_key": env.raw_public_key(server),
        "salt": salt,
        "session_key_hex": key.hex(),
        "cases": cases,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(vectors, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
