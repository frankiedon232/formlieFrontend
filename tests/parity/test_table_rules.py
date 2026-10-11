"""Response table rules give the frontend's own answers (tests/vectors/table_rules.json, recorded by
scripts/dump_table_rules.py)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from app.core import js
from app.modules.data_sources import tables as T

RULES = json.loads((Path(__file__).parents[1] / "vectors" / "table_rules.json").read_text(encoding="utf-8"))
FIELDS = RULES["fields"]
PLAIN = RULES["plain"]
ENGINES = ("mysql", "mariadb", "postgresql", "sqlserver", "oracle")
META = ("response_id", "submitted_at", "form_version", "language", "response_number", "respondent_email", "review_status")


def test_names() -> None:
    prefixes = ["formalie_", "fm_", "", "very_long_prefix_" + "p" * 40]
    for case in RULES["names"]:
        if "text" in case:
            assert T.snake(case["text"]) == case["snake"], case["text"]
            assert [T.table_name_for(case["engine"], p, case["text"]) for p in prefixes] == case["tables"], case
        else:
            taken: set[str] = set()
            assert [T.column_name_for(case["engine"], k, taken) for k in case["keys"]] == case["columns"], case["engine"]
            assert sorted(taken) == sorted(case["taken"])
    for case in RULES["restChecks"]:
        assert T.check_table_rest(case["engine"], case["prefix"], case["rest"]) == case["problem"], case
        assert T.table_rest_max(case["engine"], case["prefix"]) == case["max"]
    for case in RULES["normalised"]:
        assert T.normalise_table_rest(case["engine"], case["text"]) == case["out"], case


def test_types_and_columns() -> None:
    from_keys = [f["type"] for f in FIELDS]
    for case in RULES["types"]:
        assert [T.column_type_for(case["engine"], {"type": t}, case["multi"]) for t in from_keys] == case["types"]
        assert [T.meta_type_for(case["engine"], m) for m in META] == case["meta"]
    for case in RULES["forms"]:
        e, multi = case["engine"], case["multi"]
        assert T.columns_for_form(e, FIELDS, {"multi_value": multi}) == case["columns"]
        meta = ("response_id", "submitted_at", "response_number", "review_status", "respondent_email")
        assert T.columns_for_form(e, PLAIN[:5], {"multi_value": multi}, meta) == case["extra"]
        assert T.typed_for_engine(e, case["messed"], FIELDS, "text" if multi == "json" else "json") == case["typed"]


def test_sql() -> None:
    for case in RULES["sql"]:
        e, schema, table, columns = case["engine"], case["schema"], case["table"], case["columns"]
        assert T.create_table_sql(e, schema, table, columns) == case["create"]
        assert T.index_sql(e, schema, table, "submitted_at") == case["index"]
        assert T.add_column_sql(e, schema, table, columns[5]) == case["add"]
        assert T.unique_key_sql(e, schema, table, "response_id") == case["unique"]
        assert T.view_sql(e, schema, table, columns, dict(case["labels"])) == case["view"], (e, table)
        assert T.standard_settings({"write_mode": "insert", "key_column": "x", "multi_value": "json", "choices": "value"},
                                   columns) == case["standard"]
        assert T.standard_settings({"write_mode": "insert", "key_column": "x"}, columns[2:]) == case["standardNone"]


def test_matching_and_checks() -> None:
    for case in RULES["matched"]:
        assert T.match_columns(case["columns"], case["fields"]) == case["out"]
    for case in RULES["checks"]:
        assert T.check_mapping(case["columns"], case["fields"], case["settings"]) == case["issues"], case["settings"]


def _link(value: Any) -> list[str]:
    if isinstance(value, list):
        return [js.to_string(x.get("id", x) if isinstance(x, dict) and not js.nullish(x.get("id")) else x) for x in value]
    return [js.to_string(value)]


@pytest.mark.parametrize("case", RULES["rows"], ids=lambda c: f"{c['multi']}:{c['choices']}")
def test_rows(case: dict) -> None:
    got = T.row_for(case["columns"], FIELDS + PLAIN, case["answers"], case["facts"],
                    {"multi_value": case["multi"], "choices": case["choices"]}, _link)
    assert got == case["row"]


def test_value_kinds() -> None:
    for case in RULES["kinds"]:
        assert (T.kind_of_type(case["type"]), T.length_of(case["type"])) == (case["kind"], case["length"]), case
