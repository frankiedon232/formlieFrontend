"""Encrypted references (SECURITY-PROTOCOL §10, owner 2026-10-03): no database id leaves the server as it is.

Port of the mock's server/mock/core/ids.ts:
    ref = base64url( AES-256-ECB(16-byte id block) ‖ HMAC-SHA256(ct)[0..3] )  → 27 URL-safe characters
- AES on one block is a keyed permutation: the same id always gives the same ref (bookmarks keep working),
  a ref reveals nothing about the id, and nobody without the key can make one for another record.
- The 4-byte tag rejects typed-in or altered refs before any lookup.
- Id blocks: a UUID's 16 bytes, or a workspace template key (`ws_` + 12 hex) in a marked block.
Keys: ID_REF_ENC_KEY and ID_REF_MAC_KEY (32 bytes each, base64), server only.

`decode_ids` remembers which ids really came in as references (`RequestContext.ref_ids`), so a route that
takes an id (`RefId`, app/core/refs_types.py) refuses a raw id typed into a body or query.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import re
from typing import Any

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

from app.core.config import get_settings

UUID_RX = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.IGNORECASE)
UUID_IN_TEXT = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", re.IGNORECASE)
WS_KEY = re.compile(r"^ws_([0-9a-f]{12})$")
REF_RX = re.compile(r"^[A-Za-z0-9_-]{27}$")
REF_IN_TEXT = re.compile(r"(?<![A-Za-z0-9_-])[A-Za-z0-9_-]{27}(?![A-Za-z0-9_-])")
WS_MARK = bytes([0x77, 0x73, 0, 0, 0, 0, 0, 0, 0, 0])
INVALID_REFERENCE = "invalid-reference"

# Keys whose values are never ids, so they are left as they are (the mock encodes everything; the trace id stays
# readable here so support can find the request in the logs).
SKIP_KEYS = frozenset({"trace_id"})


def _block(id_: str) -> bytes | None:
    if UUID_RX.match(id_):
        return bytes.fromhex(id_.replace("-", ""))
    ws = WS_KEY.match(id_)
    return WS_MARK + bytes.fromhex(ws.group(1)) if ws else None


def _from_block(raw: bytes) -> str:
    if raw[:10] == WS_MARK:
        return f"ws_{raw[10:].hex()}"
    h = raw.hex()
    return f"{h[0:8]}-{h[8:12]}-{h[12:16]}-{h[16:20]}-{h[20:]}"


class RefCodec:
    def __init__(self, enc_key: bytes, mac_key: bytes) -> None:
        if len(enc_key) != 32 or len(mac_key) != 32:
            raise ValueError("ID_REF_ENC_KEY and ID_REF_MAC_KEY must be 32 bytes each (base64)")
        self._cipher = Cipher(algorithms.AES(enc_key), modes.ECB())
        self._mac_key = mac_key
        self._encode_cache: dict[str, str] = {}
        self._decode_cache: dict[str, str | None] = {}

    def _tag(self, ct: bytes) -> bytes:
        return hmac.new(self._mac_key, ct, hashlib.sha256).digest()[:4]

    def encode_id(self, id_: str) -> str:
        """The reference for an id (anything the codec doesn't handle is returned unchanged)."""
        hit = self._encode_cache.get(id_)
        if hit:
            return hit
        plain = _block(id_.lower() if UUID_RX.match(id_) else id_)
        if plain is None:
            return id_
        encryptor = self._cipher.encryptor()
        ct = encryptor.update(plain) + encryptor.finalize()
        ref = base64.urlsafe_b64encode(ct + self._tag(ct)).decode("ascii").rstrip("=")
        if len(self._encode_cache) > 50_000:
            self._encode_cache.clear()
        self._encode_cache[id_] = ref
        return ref

    def decode_id(self, ref: str) -> str | None:
        """The id behind a reference, or None when it isn't a valid one (wrong tag, typed-in, altered)."""
        if ref in self._decode_cache:
            return self._decode_cache[ref]
        if not REF_RX.match(ref):
            return None
        raw = base64.urlsafe_b64decode(ref + "=")
        ct = raw[:16]
        if len(raw) != 20 or not hmac.compare_digest(self._tag(ct), raw[16:]):
            return None
        decryptor = self._cipher.decryptor()
        id_ = _from_block(decryptor.update(ct) + decryptor.finalize())
        if len(self._decode_cache) > 50_000:
            self._decode_cache.clear()
        self._decode_cache[ref] = id_
        return id_

    def encode_ids(self, value: Any) -> Any:
        """Every id in a reply → its reference, also ids inside text such as `/api/v1/files/{id}`."""
        if isinstance(value, str):
            if UUID_RX.match(value) or WS_KEY.match(value):
                return self.encode_id(value)
            return UUID_IN_TEXT.sub(lambda m: self.encode_id(m.group(0)), value) if len(value) > 36 else value
        if isinstance(value, list):
            return [self.encode_ids(v) for v in value]
        if isinstance(value, dict):
            return {k: (v if k in SKIP_KEYS else self.encode_ids(v)) for k, v in value.items()}
        return value

    def decode_ids(self, value: Any, seen: set[str] | None = None) -> Any:
        """Every reference in a request → the real id (anything else stays as it is). Decoded ids go in `seen`."""
        if isinstance(value, str):
            if REF_RX.match(value):
                id_ = self.decode_id(value)
                if id_ is not None:
                    if seen is not None:
                        seen.add(id_)
                    return id_
                return value
            if len(value) > 27:
                def swap(m: re.Match[str]) -> str:
                    id_ = self.decode_id(m.group(0))
                    if id_ is not None and seen is not None:
                        seen.add(id_)
                    return id_ or m.group(0)
                return REF_IN_TEXT.sub(swap, value)
            return value
        if isinstance(value, list):
            return [self.decode_ids(v, seen) for v in value]
        if isinstance(value, dict):
            return {k: self.decode_ids(v, seen) for k, v in value.items()}
        return value

    def decode_path(self, path: str, seen: set[str] | None = None) -> str:
        """Route params carry references: each one becomes its id; a raw id typed into the address becomes
        `invalid-reference`, so it never matches anything (mock: decodeRouteParams)."""
        out = []
        for segment in path.split("/"):
            id_ = self.decode_id(segment) if REF_RX.match(segment) else None
            if id_ is not None:
                if seen is not None:
                    seen.add(id_)
                out.append(id_)
            elif UUID_RX.match(segment) or WS_KEY.match(segment):
                out.append(INVALID_REFERENCE)
            else:
                out.append(segment)
        return "/".join(out)


_codec: RefCodec | None = None


def get_codec() -> RefCodec:
    global _codec
    if _codec is None:
        settings = get_settings()
        if settings.id_ref_enc_key is None or settings.id_ref_mac_key is None:
            raise RuntimeError("ID_REF_ENC_KEY and ID_REF_MAC_KEY are not set (scripts/gen_keys.py)")
        _codec = RefCodec(base64.b64decode(settings.id_ref_enc_key.get_secret_value()),
                          base64.b64decode(settings.id_ref_mac_key.get_secret_value()))
    return _codec


def set_codec(codec: RefCodec | None) -> None:
    global _codec
    _codec = codec
