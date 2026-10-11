"""Encrypted references, behaving like the mock's server/mock/core/ids.ts."""

from __future__ import annotations

import os
import re
import uuid

import pytest

from app.core.security.refs import INVALID_REFERENCE, RefCodec

pytestmark = pytest.mark.parity

CODEC = RefCodec(os.urandom(32), os.urandom(32))
ID = "0190f0b2-1111-7222-8333-444455556666"


def test_reference_is_27_url_safe_characters_and_stable() -> None:
    ref = CODEC.encode_id(ID)
    assert re.fullmatch(r"[A-Za-z0-9_-]{27}", ref)
    assert CODEC.encode_id(ID) == ref and CODEC.decode_id(ref) == ID
    assert ID.replace("-", "")[:8] not in ref  # reveals nothing readable


def test_workspace_template_keys_round_trip() -> None:
    ref = CODEC.encode_id("ws_0123456789ab")
    assert len(ref) == 27 and CODEC.decode_id(ref) == "ws_0123456789ab"


def test_altered_typed_in_or_foreign_references_are_refused() -> None:
    ref = CODEC.encode_id(ID)
    altered = ref[:-1] + ("A" if ref[-1] != "A" else "B")
    assert CODEC.decode_id(altered) is None
    assert CODEC.decode_id("A" * 27) is None
    assert RefCodec(os.urandom(32), os.urandom(32)).decode_id(ref) is None  # another key
    assert CODEC.decode_id("short") is None


def test_every_id_in_a_reply_becomes_a_reference() -> None:
    other = str(uuid.uuid4())
    reply = {"data": {"id": ID, "items": [{"form_id": other}], "url": f"/api/v1/files/{ID}", "name": "Survey",
                      "count": 3}, "error": {"trace_id": ID}}
    out = CODEC.encode_ids(reply)
    assert out["data"]["id"] == CODEC.encode_id(ID) and out["data"]["items"][0]["form_id"] == CODEC.encode_id(other)
    assert out["data"]["url"] == f"/api/v1/files/{CODEC.encode_id(ID)}"
    assert out["data"]["name"] == "Survey" and out["data"]["count"] == 3
    assert out["error"]["trace_id"] == ID  # kept readable for support


def test_references_in_a_request_become_ids_and_are_remembered() -> None:
    ref = CODEC.encode_id(ID)
    seen: set[str] = set()
    body = CODEC.decode_ids({"form_id": ref, "ids": [ref], "note": f"see {ref} here", "raw": ID, "x": "y"}, seen)
    assert body == {"form_id": ID, "ids": [ID], "note": f"see {ID} here", "raw": ID, "x": "y"}
    assert seen == {ID}  # the raw id was not seen as a reference


def test_route_params_take_references_only() -> None:
    seen: set[str] = set()
    ref = CODEC.encode_id(ID)
    assert CODEC.decode_path(f"/api/v1/forms/{ref}/versions", seen) == f"/api/v1/forms/{ID}/versions"
    assert seen == {ID}
    assert CODEC.decode_path(f"/api/v1/forms/{ID}") == f"/api/v1/forms/{INVALID_REFERENCE}"
    assert CODEC.decode_path("/api/v1/settings/security") == "/api/v1/settings/security"
