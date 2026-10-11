"""The ported rules against what the frontend's own shared/ code answered (tests/vectors/frontend_rules.json,
recorded by scripts/dump_frontend_rules.py): permissions, roles, audit catalogue, plans, passwords, hosts."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.core.middleware.tenant import RESERVED_SUBDOMAINS
from app.core.security.passwords import DEFAULT_PASSWORD_POLICY, PASSWORD_LENGTH_RANGE, check_password, \
    meets_password_policy, password_score
from app.modules.audit.events import AUDIT_AREAS, AUDIT_EVENTS
from app.modules.billing.plans import PLANS
from app.modules.rbac import catalogue
from app.modules.rbac.permissions import ALL_GRANTS, areas_of, permission_for, reach_of, set_grant, with_needs

pytestmark = pytest.mark.parity

R = json.loads((Path(__file__).parents[1] / "vectors" / "frontend_rules.json").read_text(encoding="utf-8"))


def test_generated_catalogues_are_current() -> None:
    assert list(catalogue.ALL_PERMISSIONS) == R["all_permissions"]
    assert catalogue.DEFAULT_ROLE_GRANTS == R["default_role_grants"]
    assert catalogue.PERMISSION_NEEDS == R["permission_needs"]
    assert list(AUDIT_AREAS) == R["audit_areas"] and AUDIT_EVENTS == R["audit_events"]
    assert PLANS == R["plans"]
    assert ALL_GRANTS == {p: "all" for p in R["all_permissions"]}


@pytest.mark.parametrize(("method", "path", "expected"), R["permission_for"], ids=lambda v: str(v))
def test_permission_for_every_endpoint(method: str, path: str, expected: str | None) -> None:
    assert permission_for(method, path) == expected


def test_with_needs_cases() -> None:
    mismatches = [(given, expected, with_needs(given)) for given, expected in R["with_needs"] if with_needs(given) != expected]
    assert not mismatches, mismatches[:3]


def test_set_grant_cases() -> None:
    mismatches = [c for c in R["set_grant"] if set_grant(c["base"], c["permission"], c["scope"]) != c["result"]]
    assert not mismatches, mismatches[:3]


def test_reach_and_areas() -> None:
    for grants, reach, areas in R["reach"]:
        assert reach_of(grants) == pytest.approx(reach) and areas_of(grants) == areas


def test_password_policy_cases() -> None:
    assert DEFAULT_PASSWORD_POLICY == R["default_password_policy"] and PASSWORD_LENGTH_RANGE == R["password_length_range"]
    for case in R["password_cases"]:
        pw, policy = case["password"], case["policy"]
        assert check_password(pw, policy) == case["checks"], pw
        assert meets_password_policy(pw, policy) == case["meets"], pw
        assert password_score(pw, policy) == case["score"], pw


def test_reserved_subdomains() -> None:
    assert list(RESERVED_SUBDOMAINS) == R["reserved_subdomains"]


def test_locales() -> None:
    from app.core.locales import APP_LOCALE_CODES, APP_LOCALES

    assert APP_LOCALES == R["app_locales"] and list(APP_LOCALE_CODES) == [x["code"] for x in R["app_locales"]]


def test_signin_methods() -> None:
    from app.modules.settings.service import SIGNIN_METHODS

    assert list(SIGNIN_METHODS) == R["signin_methods"]
