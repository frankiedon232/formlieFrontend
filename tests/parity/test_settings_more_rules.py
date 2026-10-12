"""Settings, the rest (B11) give the frontend's own answers (tests/vectors/settings_more_rules.json, recorded by
scripts/dump_settings_more_rules.py): the catalogues, and the mock routes' request schemas (accepted or not, the
cleaned value, every problem's field and message)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.modules.address import router as address
from app.modules.emails import settings_router as emails
from app.modules.emails.catalogue import EMAIL_VARIABLES
from app.modules.privacy import router as privacy
from app.modules.settings.catalogues import RETENTION_DAYS
from app.modules.sso import router as sso_router
from app.modules.sso import service as sso

RULES = json.loads((Path(__file__).parents[1] / "vectors" / "settings_more_rules.json").read_text(encoding="utf-8"))
SCHEMAS = {"preview": emails.preview_schema, "address": emails.address_schema, "smtp": emails.smtp_schema,
           "mode": emails.mode_schema, "sso": sso.save_schema, "status": sso_router.status_schema,
           "subdomain": address.subdomain_schema, "domain": address.domain_schema, "email": privacy.email_schema,
           "delete": privacy.delete_schema}
CASES = [(name, i, case) for name, cases in RULES["schemas"].items() for i, case in enumerate(cases)]


def test_catalogues() -> None:
    assert EMAIL_VARIABLES == RULES["email_variables"]
    assert list(sso.SSO_PROVIDERS) == RULES["sso_providers"] and sso.SSO_PROTOCOL == RULES["sso_protocol"]
    assert list(privacy.DATA_REGIONS) == RULES["data_regions"]
    assert list(RETENTION_DAYS) == RULES["retention_days"]


@pytest.mark.parametrize(("name", "index", "case"), CASES, ids=[f"{n}-{i}" for n, i, _ in CASES])
def test_schema_answers_like_zod(name: str, index: int, case: dict) -> None:  # noqa: ARG001
    ok, result = SCHEMAS[name].safe_parse(case["input"])
    if case["ok"]:
        assert ok, result
        assert result == case["data"]
    else:
        assert not ok, result
        assert [(i["field"], i["message"]) for i in result] == [(i["path"], i["message"]) for i in case["issues"]]
