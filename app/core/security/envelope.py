"""The encryption envelope, server half (SECURITY-PROTOCOL §1 to §3). Port of shared/utils/crypto/envelope.ts.

ECDH P-256 → HKDF-SHA256 (salt = 32 random bytes, info = "formalie-envelope-v1") → 256-bit AES-GCM key.
Envelope = {kid, iv (12 bytes), ts (ms), nonce (16 bytes), ct}; AAD = "kid|ts|nonce"; standard base64;
`ct` carries the 16-byte GCM tag at its end (as WebCrypto does). Parity: tests/parity/test_envelope.py runs
fixed vectors that scripts/check_envelope_vectors.mjs checks against the frontend's own envelope.ts.
"""

from __future__ import annotations

import base64
import binascii
import json
import os
import time
from typing import Any

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

HKDF_INFO = b"formalie-envelope-v1"
ENVELOPE_HEADER = "x-formalie-envelope"
ENVELOPE_CONTENT_TYPE = "application/vnd.formalie.enc+json"
MAX_SKEW_MS = 60_000
NONCE_TTL_S = 120


class EnvelopeError(Exception):
    """Decryption failed: wrong key, altered ciphertext, AAD or tag (FRM-SEC-1005)."""


def b64encode(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


def b64decode(value: str) -> bytes:
    return base64.b64decode(value, validate=True)


def b64url_to_bytes(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def bytes_to_b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


# ── Handshake ─────────────────────────────────────────────────────────────────

def generate_key_pair() -> ec.EllipticCurvePrivateKey:
    return ec.generate_private_key(ec.SECP256R1())


def raw_public_key(private_key: ec.EllipticCurvePrivateKey) -> str:
    """The uncompressed point (65 bytes), base64: what WebCrypto exports as 'raw'."""
    return b64encode(private_key.public_key().public_bytes(Encoding.X962, PublicFormat.UncompressedPoint))


def load_peer_public_key(raw_b64: str) -> ec.EllipticCurvePublicKey:
    """Raises ValueError for anything that is not a valid P-256 point."""
    try:
        raw = b64decode(raw_b64)
    except (binascii.Error, ValueError) as exc:
        raise ValueError("not base64") from exc
    return ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(), raw)


def derive_session_key(private_key: ec.EllipticCurvePrivateKey, peer_public_b64: str, salt_b64: str) -> bytes:
    """Same as deriveSessionKey(): ECDH shared x-coordinate (256 bits) → HKDF-SHA256 → 32-byte AES key."""
    shared = private_key.exchange(ec.ECDH(), load_peer_public_key(peer_public_b64))
    return HKDF(algorithm=hashes.SHA256(), length=32, salt=b64decode(salt_b64), info=HKDF_INFO).derive(shared)


# ── Seal / open ───────────────────────────────────────────────────────────────

def _aad(kid: str, ts: int, nonce: str) -> bytes:
    return f"{kid}|{ts}|{nonce}".encode()


def to_json(payload: Any) -> bytes:
    """JSON.stringify: compact, UTF-8."""
    return json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def seal(key: bytes, kid: str, payload: Any, *, iv: bytes | None = None, nonce: bytes | None = None,
         ts: int | None = None) -> dict[str, Any]:
    """sealEnvelope(). `iv`, `nonce` and `ts` are only passed by the test vectors."""
    iv = iv if iv is not None else os.urandom(12)
    nonce_b64 = b64encode(nonce if nonce is not None else os.urandom(16))
    ts = ts if ts is not None else int(time.time() * 1000)
    ct = AESGCM(key).encrypt(iv, to_json(payload), _aad(kid, ts, nonce_b64))
    return {"kid": kid, "iv": b64encode(iv), "ts": ts, "nonce": nonce_b64, "ct": b64encode(ct)}


def open_envelope(key: bytes, envelope: dict[str, Any]) -> Any:
    """openEnvelope(): raises EnvelopeError when the key, AAD or ciphertext do not match."""
    try:
        plaintext = AESGCM(key).decrypt(
            b64decode(envelope["iv"]), b64decode(envelope["ct"]),
            _aad(envelope["kid"], envelope["ts"], envelope["nonce"]),
        )
        return json.loads(plaintext.decode("utf-8"))
    except (InvalidTag, KeyError, ValueError, binascii.Error, UnicodeDecodeError) as exc:
        raise EnvelopeError(str(exc) or type(exc).__name__) from exc


def is_fresh(ts: int, now_ms: int | None = None) -> bool:
    now_ms = now_ms if now_ms is not None else int(time.time() * 1000)
    return abs(now_ms - ts) <= MAX_SKEW_MS


def is_envelope(value: Any) -> bool:
    """isEnvelope(): the five fields with the right types."""
    return (isinstance(value, dict) and isinstance(value.get("kid"), str) and isinstance(value.get("iv"), str)
            and isinstance(value.get("ts"), (int, float)) and not isinstance(value.get("ts"), bool)
            and isinstance(value.get("nonce"), str) and isinstance(value.get("ct"), str))


def encode_header(envelope: dict[str, Any]) -> str:
    """encodeEnvelopeHeader(): base64url (no padding) of the JSON."""
    return bytes_to_b64url(to_json(envelope))


def decode_header(value: str) -> dict[str, Any] | None:
    """decodeEnvelopeHeader(): None when it isn't a well-formed envelope."""
    try:
        parsed = json.loads(b64url_to_bytes(value).decode("utf-8"))
    except (ValueError, binascii.Error, UnicodeDecodeError):
        return None
    return parsed if is_envelope(parsed) else None
