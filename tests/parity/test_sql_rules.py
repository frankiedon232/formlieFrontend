"""Query editor and explorer rules give the frontend's own answers (tests/vectors/sql_rules.json, recorded by
scripts/dump_sql_rules.py)."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from app.core import js
from app.modules.data_sources import ddl as D
from app.modules.data_sources import sql as S
from app.modules.data_sources import tables as T
from app.modules.data_sources.activity import ACTIVITY_ACTIONS, kind_of_action

RULES = json.loads((Path(__file__).parents[1] / "vectors" / "sql_rules.json").read_text(encoding="utf-8"))


ISO_WITH_ZONE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}(T[0-9:.]+(Z|[+-][0-9]{2}:[0-9]{2}))?")


def _browser_only(case: dict) -> bool:
    """Date-times the browser's fallback parser reads in the machine's own time zone ("12", "2026-10-11T08:09"):
    the server takes ISO dates, and date-times with Z or an offset, only."""
    raw = case["raw"]
    return T.kind_of_type(case["column"]["type"]) == "datetime" and "value" in case["out"] and not (
        isinstance(raw, str) and ISO_WITH_ZONE.fullmatch(raw.strip()))


def _v(value):  # noqa: ANN001, ANN202
    return js.UNDEFINED if value == "__undefined__" else value


@pytest.mark.parametrize("case", RULES["split"], ids=lambda c: c["sql"][:30])
def test_split_kind_format(case: dict) -> None:
    assert [s.view() for s in S.split_statements(case["sql"])] == case["statements"]
    assert S.script_kind(case["sql"]) == case["kind"]
    if case["format"] is not None:
        assert S.format_sql(case["sql"]) == case["format"]


def test_statements_and_cursor() -> None:
    for case in RULES["statements"]:
        text = case["text"]
        assert (S.statement_kind(text), S.tables_in(text), S.parameters_in(text)) == (case["kind"], case["tables"], case["params"]), text
        if case["code"] is not None:
            assert S.code_only(text) == case["code"]
    for case in RULES["cursors"]:
        found = S.statement_at(case["sql"], case["cursor"])
        assert (found.view() if found else None) == case["at"], (case["sql"], case["cursor"])


def test_ddl() -> None:
    specs = RULES["specs"]
    for case in RULES["ddl"]:
        e = case["engine"]
        assert D.kinds_for(e) == case["kinds"]
        assert [D.type_for(e, s) for s in specs] == case["types"]
        assert [D.column_sql(e, "people", s) for s in specs] == case["columns"]
        assert D.create_table_statements(e, "app", "people", specs[:1] + specs[2:]) == case["create"]
        assert D.create_table_statements(e, "app", "pairs", [{**specs[0], "auto": False}, {**specs[2], "primary": True}]) == case["createTwoKeys"]
        for change in case["changes"]:
            assert D.change_statements(e, "app", "people", change["change"], change["current"]) == change["out"], (e, change["change"])
            assert D.change_statements(e, "app", "people", change["change"]) == change["none"], (e, change["change"])
    for case in RULES["specOf"]:
        assert {k: v for k, v in D.spec_of_type(case["type"]).items()} == case["spec"], case
    for case in RULES["risky"]:
        assert D.type_change_risky(case["from"], case["to"]) is case["risky"], case
    for case in RULES["checks"]:
        assert D.check_name(case["engine"], case["name"], case["what"]) == case["problem"], case
    for case in RULES["normal"]:
        assert D.normalise_db_name(case["engine"], case["text"]) == case["out"]


def test_export_formats() -> None:
    for case in RULES["literals"]:
        assert D.sql_literal(case["engine"], case["type"], _v(case["value"])) == case["out"], case
    assert D.json_export(RULES["exportColumns"], RULES["exportRows"]) == RULES["jsonOut"]
    for case in RULES["scriptsOut"]:
        got = D.sql_insert_script(case["engine"], {"schema": "app", "table": "people"}, RULES["exportColumns"],
                                  RULES["exportRows"], "2026-10-11T08:00:00.000Z")
        assert got == case["out"], case["engine"]


def test_values_and_activity() -> None:
    for case in RULES["parsed"]:
        if _browser_only(case):
            continue
        assert T.parse_value(case["column"], _v(case["raw"])) == case["out"], (case["column"], case["raw"])
    for case in RULES["activity"]:
        assert kind_of_action(case["action"]) == case["kind"]
    assert {k: list(v) for k, v in ACTIVITY_ACTIONS.items()} == RULES["actions"]
