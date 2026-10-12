"""Webhook rules give the frontend's own answers (tests/vectors/webhook_rules.json, recorded by
scripts/dump_webhook_rules.py): addresses that may receive deliveries, retry waits, the pause, statuses and labels."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.modules.webhooks import rules as W

RULES = json.loads((Path(__file__).parents[1] / "vectors" / "webhook_rules.json").read_text(encoding="utf-8"))


def test_constants() -> None:
    assert list(W.WEBHOOK_EVENTS) == RULES["events"]
    assert list(W.WEBHOOK_RETRY_MINUTES) == RULES["retry_minutes"]
    assert W.WEBHOOK_AUTO_PAUSE == RULES["auto_pause"] and W.WEBHOOK_TIMEOUT_MS == RULES["timeout_ms"]


@pytest.mark.parametrize("case", RULES["checks"], ids=lambda c: f"{c['value'][:40]!r}-{c['allowLocal']}")
def test_webhook_addresses(case: dict) -> None:
    assert W.check_webhook_url(case["value"], allow_local=case["allowLocal"]) == case["problem"]


def test_statuses_labels_and_signed_payload() -> None:
    for case in RULES["statuses"]:
        assert W.webhook_status_of(case["enabled"], case["consecutive_failures"]) == case["status"], case
    for case in RULES["labels"]:
        assert W.event_label_key(case["event"]) == case["key"], case
    for case in RULES["signed"]:
        assert W.signed_payload(case["timestamp"], case["body"]) == case["payload"], case
