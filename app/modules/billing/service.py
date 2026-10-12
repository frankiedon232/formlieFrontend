"""What a workspace's plan allows (port of the mock's core/plan.ts). Subscriptions and payments arrive in B15;
until then the plan is the directory's `tenants.plan_id` (the mirror the subscription keeps up to date)."""

from __future__ import annotations

from typing import Any

from app.core.errors import FrmError
from app.modules.billing.plans import PLANS

_BY_ID = {plan["id"]: plan for plan in PLANS}
FEATURES = ("sso", "custom_domain", "custom_email", "data_residency")


def plan_of(plan_id: str | None) -> dict[str, Any]:
    return _BY_ID.get(plan_id or "starter", _BY_ID["starter"])


def limits_of(plan_id: str | None) -> dict[str, Any]:
    return plan_of(plan_id)["limits"]


def has_feature(plan_id: str | None, feature: str) -> bool:
    """hasFeature(): single sign-on, own domain, own sending address, data residency."""
    limits = limits_of(plan_id)
    if feature == "custom_domain":
        return limits["custom_domains"] != 0
    return bool(limits[feature])


def require_feature(plan_id: str | None, feature: str) -> None:
    if not has_feature(plan_id, feature):
        raise FrmError("FRM-PLAN-1002", [{"field": feature, "message": feature}])
