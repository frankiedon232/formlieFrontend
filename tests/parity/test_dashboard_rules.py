"""Dashboard and analytics rules give the frontend's own answers (tests/vectors/dashboard_rules.json, recorded by
scripts/dump_dashboard_rules.py): buckets, the period and its buckets, the forms filter, the analytics period, the
repeatable estimates of views and starts, totals and the funnel."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.modules.analytics import rules as A
from app.modules.dashboard import rules as R

RULES = json.loads((Path(__file__).parents[1] / "vectors" / "dashboard_rules.json").read_text(encoding="utf-8"))
DAY = 86_400_000


def today(now_ms: int) -> int:
    return now_ms // DAY


def test_bucket_starts_lists_and_groups() -> None:
    for case in RULES["starts"]:
        assert R.iso_day(R.bucket_start(case["time"] // DAY, case["group"])) == case["start"], case
    for case in RULES["buckets"]:
        assert R.buckets_of(case["from"] // DAY, case["to"] // DAY, case["group"]) == case["buckets"], case
    for case in RULES["groups"]:
        assert R.group_for(case["days"]) == case["group"], case


@pytest.mark.parametrize("chunk", range(8))
def test_period_from(chunk: int) -> None:
    for case in RULES["periods"][chunk::8]:
        p = R.period_from(case["query"], today(case["now"]))
        got = (R.iso_day(p.start), R.iso_day(p.end), p.days, p.group, R.iso_day(p.prev_start), p.buckets)
        assert got == (case["from"], case["to"], case["days"], case["group"], case["prev_from"], case["buckets"]), case


def test_scope_from() -> None:
    forms = [(None, "u1"), ("f1", "u1"), ("f2", "u2"), ("none", "none")]
    for case in RULES["scopes"]:
        scope = R.scope_from(case["query"])
        assert scope.filtered == case["filtered"], case
        assert [scope.matches(folder, owner) for folder, owner in forms] == case["matches"], case


def test_analytics_period_and_seeds() -> None:
    for case in RULES["analytics_periods"]:
        p = A.period_of(case["query"], today(case["now"]))
        b = p.before()
        assert (R.iso_day(p.start), R.iso_day(p.end), p.days) == (case["from"], case["to"], case["days"]), case
        assert [R.iso_day(b.start), R.iso_day(b.end), b.days] == case["before"], case
    for case in RULES["seeds"]:
        random = A.seeded(case["text"])
        assert [random() for _ in case["numbers"]] == case["numbers"], case


@pytest.mark.parametrize("index", range(len(RULES["analytics"])))
def test_days_totals_and_funnel(index: int) -> None:
    case = RULES["analytics"][index]
    form, period = case["form"], case["period"]
    start = R.parse_day(period["from"])
    assert start is not None
    p = A.Period(start, start + period["days"] - 1, period["days"])
    per_day: dict[int, int] = {}
    times = []
    for entry in case["entries"]:
        day = entry["at"] // DAY
        if p.start <= day <= p.end:
            per_day[day] = per_day.get(day, 0) + 1
            if entry["duration_seconds"] is not None:
                times.append(entry["duration_seconds"])
    daily = A.days_of(form["id"], form["status"], form["completion_rate"], per_day, p)
    assert daily == case["daily"]
    totals = A.totals_of(daily, A.median_of(times))
    assert totals == case["totals"]
    pages, fields = A.funnel_of(form["id"], case["schema"], totals)
    assert {"pages": pages, "fields": fields} == case["funnel"]
