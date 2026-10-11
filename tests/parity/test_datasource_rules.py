"""Data source rules give the frontend's own answers (tests/vectors/datasource_rules.json, recorded by
scripts/dump_datasource_rules.py)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.modules.data_sources import engines as E

RULES = json.loads((Path(__file__).parents[1] / "vectors" / "datasource_rules.json").read_text(encoding="utf-8"))


def test_defaults_and_cleaning() -> None:
    for case in RULES["defaults"]:
        assert E.default_settings(case["engine"]) == case["settings"], case["engine"]
    for case in RULES["cleaned"]:
        got = {k: None if isinstance(v, float) and v != v else v for k, v in E.clean_settings(case["engine"], case["input"]).items()}
        assert got == case["settings"], case  # NaN is null once written, as JSON.stringify writes it


@pytest.mark.parametrize("case", RULES["fields"], ids=lambda c: f"{c['engine']}:{json.dumps(c['settings'])[:40]}")
def test_fields(case: dict) -> None:
    assert [f.key for f in E.fields_for(case["engine"], case["settings"])] == case["keys"]
    assert [f.key for f in E.fields_for(case["engine"], case["settings"], "server")] == case["server"]


@pytest.mark.parametrize("case", RULES["checks"], ids=lambda c: c["engine"])
def test_checks(case: dict) -> None:
    got = E.check_config(case["engine"], case["settings"], case["secrets"], case["kept"], case.get("step"))
    assert got == case["problems"], (case["settings"], case["secrets"])


def test_secrets_names_operations_hosts() -> None:
    for case in RULES["secrets"]:
        assert E.clean_secrets(case["engine"], case["settings"], case["secrets"]) == case["clean"], case
    for case in RULES["names"]:
        e, s = case["engine"], case["settings"]
        assert (E.address_of(e, s), E.database_name_of(e, s), E.default_schema_of(e, s), E.is_encrypted(e, s)) == \
            (case["address"], case["database"], case["schema"], case["encrypted"]), case
    for case in RULES["operations"]:
        assert E.operations_for(case["engine"], case["access"]) == case["ops"]
        assert E.levels_for(case["access"]) == case["levels"] and E.has_tables_schema(case["engine"]) is case["has"]
        assert E.tables_schema_of(case["engine"], {"database": "db", "username": "App"}, case["access"]) == case["schema"]
    for case in RULES["blocked"]:
        assert E.is_blocked_host(case["host"]) is case["blocked"], case
