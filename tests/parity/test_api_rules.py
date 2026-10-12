"""API service rules give the frontend's own answers (tests/vectors/api_rules.json, recorded by scripts/dump_api_rules.py):
tokens, allowed websites, access rules, choices and endpoint fields, names and examples."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pytest

from app.modules.api_service import access as A
from app.modules.api_service import choices as C
from app.modules.api_service import endpoints as E
from app.modules.api_service import origins as O
from app.modules.api_service import tokens as T
from app.modules.api_service.labels import icon_from_label, key_from_label

RULES = json.loads((Path(__file__).parents[1] / "vectors" / "api_rules.json").read_text(encoding="utf-8"))
TOK, ORI, ACC, CHO, END = RULES["tokens"], RULES["origins"], RULES["access"], RULES["choices"], RULES["endpoints"]


def test_token_prefixes_previews_and_masks() -> None:
    for case in TOK["prefixes"]:
        assert T.token_prefix(case["kind"], case["mode"]) == case["prefix"], case
    for case in TOK["previews"]:
        assert T.secret_preview(case["secret"]) == case["preview"], case
    for case in TOK["masks"]:
        assert T.mask_value(case["value"]) == case["masked"], case
    secret = T.new_secret("static", "live")
    assert secret.startswith("formalie_live_") and len(secret) == len("formalie_live_") + 32
    assert len(T.new_secret("client_id", "test")) == len("formalie_client_test_") + 16
    assert len(T.new_secret("client", "test")) == len("formalie_secret_test_") + 40


def test_token_status_scopes_and_reach() -> None:
    for case in TOK["statuses"]:
        now = datetime.fromisoformat(case["now"].replace("Z", "+00:00"))
        assert T.token_status_of(case["revoked_at"], case["expires_at"], now) == case["status"], case
    for case in TOK["scopes"]:
        t = case["target"]
        assert T.scope_allows(case["scopes"], t["endpoint_id"], t["service_id"], t["method"]) is case["allows"], case
        assert T.token_reach(case["scopes"], t["endpoint_id"], t["service_id"]) == case["reach"], case


def test_headers_call_keys_and_canonical_json() -> None:
    for case in TOK["headerNames"]:
        assert T.check_header_name(case["name"]) == case["problem"], case
    for case in TOK["headerValues"]:
        assert T.check_header_value(case["value"]) == case["problem"], case
    for case in TOK["callKeys"]:
        assert T.check_call_key(case["key"]) == case["problem"], case
    for case in TOK["canon"]:
        assert T.canonical_json(case["value"]) == case["json"], case


@pytest.mark.parametrize("case", ORI["origins"], ids=lambda c: repr(c["value"])[:40])
def test_allowed_websites(case: dict) -> None:
    assert O.normalise_origin(case["value"]) == case["origin"]


def test_origin_allowed() -> None:
    for case in ORI["originAllowed"]:
        assert O.origin_allowed(case["origin"], case["allowed"]) is case["ok"], case


def test_rule_values_regions_and_ranges() -> None:
    for case in ACC["valueChecks"]:
        assert A.check_rule_value(case["kind"], case["value"]) == case["problem"], case
        assert A.normalise_rule_value(case["kind"], case["value"]) == case["normal"], case
    for case in ACC["regions"]:
        assert A.region_of(case["country"]) == case["region"], case
    for case in ACC["cidrs"]:
        got = A.parse_cidr(case["text"])
        want = case["cidr"]
        assert (None if got is None else {"family": got[0], "value": str(got[1]), "bits": got[2]}) == want, case
    for case in ACC["ipPairs"]:
        assert A.ip_in_cidr(case["ip"], case["cidr"]) is case["inside"], case


def _caller(raw: dict) -> A.AccessCaller:
    return A.AccessCaller(ip=raw["ip"], domain=raw.get("domain"), country=raw.get("country"), networks=raw.get("networks") or [])


def test_matching_and_decisions() -> None:
    for case in ACC["matches"]:
        assert A.matches_value(case["kind"], case["value"], _caller(case["caller"])) is case["match"], case
    for case in ACC["decisions"]:
        assert A.decide_access(case["rules"], _caller(case["caller"])) == case["decision"], case
    rules = [{"id": i, "scope": s} for i, s in (("a", {"type": "all", "id": None}), ("b", {"type": "service", "id": "s1"}),
                                                ("c", {"type": "endpoint", "id": "e1"}), ("d", {"type": "service", "id": "s2"}),
                                                ("e", {"type": "endpoint", "id": "e2"}))]
    for case in ACC["rulesFor"]:
        got = A.rules_for(rules, case["endpoint"]["id"], case["endpoint"]["service_id"])
        assert [r["id"] for r in got] == case["ids"], case


def test_choices_in_and_out() -> None:
    for case in CHO["outCases"]:
        assert C.choice_out(case["field"], case["value"]) == case["out"], case
    fields = [CHO["outCases"][0]["field"], CHO["outCases"][-1]["field"], CHO["outCases"][4]["field"], CHO["outCases"][5]["field"]]
    for case in CHO["inCases"]:
        assert C.choices_in(fields, case["answers"]) == case["out"], case
    for case in CHO["filterCases"]:
        assert C.choice_filter(case["field"], case["wanted"]) == case["out"], case


@pytest.mark.parametrize("case", END["fieldCases"], ids=lambda c: f"{len(c['fields'])}:{json.dumps(c['saved'])[:30]}")
def test_endpoint_fields_and_examples(case: dict) -> None:
    fields = E.endpoint_fields_of(case["schema"], case["saved"])
    assert fields == case["fields"]
    assert [E.not_accepted_reason(f) for f in fields] == case["reasons"]
    assert E.example_request_body(fields) == case["body"]
    assert E.example_record(fields) == case["record"]
    assert E.with_level_samples(fields) == case["levels"]


def test_samples_labels_and_icons() -> None:
    for case in END["samples"]:
        assert E.sample_value(case["field"]) == case["value"], case
    for case in END["forLabel"]:
        assert E.sample_for_label({"key": case.get("key", "k"), "label": case["label"]}) == case["value"], case
    for case in END["icons"]:
        assert icon_from_label(case["label"], case["key"]) == case["icon"], case
    for case in END["keys"]:
        assert key_from_label(case["label"], case["taken"]) == case["key"], case


def test_names_and_version_changes() -> None:
    for case in END["endpointNames"]:
        assert E.check_endpoint_name(case["name"]) == case["problem"], case
    for case in END["nameFrom"]:
        assert E.endpoint_name_from(case["text"]) == case["name"], case
    for case in END["apiNames"]:
        assert E.check_api_name(case["name"]) == case["problem"], case
    for case in END["changes"]:
        assert E.api_changes(case["live"], case["draft"]) == case["changes"], case
