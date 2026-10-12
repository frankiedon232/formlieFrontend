"""Ships what Formalie has today into the global tables (migration 0034), so the platform admin starts from it and
nothing changes for workspaces:

- platform settings: the legal pages, the support contact and the outgoing addresses (from the server's settings);
- reserved subdomains (the host rules' list);
- the plan catalogue (app/modules/billing/plans.py);
- the sample lists (app/modules/lists/samples.py), the email templates in 20 languages (app/modules/emails/defaults),
  the template catalogue (app/modules/templates/data/system_templates.json, English names), the themes and page
  designs (app/modules/design/catalogues.py). Default folders: none (new workspaces start without folders, like
  the mock's).

Rows are only added, never changed: what the Formalie team published later is never overwritten by a re-run.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import Connection

P = "platform"
SHIPPED_AT = datetime(2026, 10, 12, 9, 0, tzinfo=UTC)


def _insert(conn: Connection, table: str, keys: tuple[str, ...], rows: list[dict[str, Any]],
            casts: dict[str, str] | None = None) -> int:
    if not rows:
        return 0
    casts = casts or {}
    columns = list(rows[0])
    values = ", ".join(f"CAST(:{c} AS {casts[c]})" if c in casts else f":{c}" for c in columns)
    conn.execute(text(f"INSERT INTO {P}.{table} ({', '.join(columns)}) VALUES ({values}) "
                      f"ON CONFLICT ({', '.join(keys)}) DO NOTHING"), rows)
    return len(rows)


def _stamp() -> dict[str, Any]:
    return {"created_at": SHIPPED_AT, "updated_at": SHIPPED_AT}


def settings_rows() -> list[dict[str, Any]]:
    from app.core.config import get_settings

    s = get_settings()
    values = {
        "legal": ({"terms_url": s.legal_terms_url, "privacy_url": s.legal_privacy_url},
                  "Formalie's legal pages, linked from every public form"),
        "support": ({"email": getattr(s, "support_email", "support@formalie.com") or None,
                     "url": getattr(s, "support_url", None) or None},
                    "Where people reach Formalie's support team (help centre)"),
        "egress_ips": (list(s.egress_ips), "Formalie's outgoing addresses, shown on Data sources"),
        "status_page": ({"url": None}, "Formalie's status page"),
    }
    return [{"key": key, "value": json.dumps(value), "description": description, **_stamp()}
            for key, (value, description) in values.items()]


def seed_globals(conn: Connection) -> dict[str, int]:
    from app.core.middleware.tenant import RESERVED_SUBDOMAINS
    from app.modules.billing.plans import PLANS
    from app.modules.design.catalogues import PAGE_PRESETS, THEME_PRESETS
    from app.modules.lists.samples import sample_lists

    counts: dict[str, int] = {}
    counts["platform_settings"] = _insert(conn, "platform_settings", ("key",), settings_rows(), {"value": "jsonb"})
    counts["reserved_subdomains"] = _insert(conn, "reserved_subdomains", ("subdomain",), [
        {"subdomain": sub, "reason": "Formalie's own addresses", **_stamp()} for sub in RESERVED_SUBDOMAINS])

    counts["plans"] = _insert(conn, "plans", ("id",), [
        {"id": p["id"], "currency": p["currency"], "recommended": bool(p.get("recommended")), "sort": i, **_stamp()}
        for i, p in enumerate(PLANS)])
    counts["plan_prices"] = _insert(conn, "plan_prices", ("plan_id", "period"), [
        {"plan_id": p["id"], "period": period, "amount": Decimal(str(amount)), **_stamp()}
        for p in PLANS for period, amount in (p.get("prices") or {}).items()])
    counts["plan_limits"] = _insert(conn, "plan_limits", ("plan_id",), [
        {"plan_id": p["id"], **{k: p["limits"].get(k) for k in (
            "forms", "responses_per_form", "custom_domains", "ai_credits", "languages")},
         "databases": list(p["limits"].get("databases") or []), "sso": bool(p["limits"].get("sso")),
         "custom_email": bool(p["limits"].get("custom_email")),
         "data_residency": bool(p["limits"].get("data_residency")), **_stamp()} for p in PLANS])
    counts["plan_features"] = _insert(conn, "plan_features", ("plan_id", "feature"), [
        {"plan_id": p["id"], "feature": f, **_stamp()} for p in PLANS for f in p.get("features") or []])

    lists = sample_lists()
    counts["system_option_lists"] = _insert(conn, "system_option_lists", ("key",), [
        {"key": item["system_key"], "name": item["name"], "description": item.get("description"),
         "levels": json.dumps(item.get("levels")) if item.get("levels") else None,
         "columns": json.dumps(item.get("columns")) if item.get("columns") else None,
         "large": False, "sort": i, **_stamp()} for i, item in enumerate(lists)],
        {"levels": "jsonb", "columns": "jsonb"})
    counts["system_option_items"] = _insert(conn, "system_option_items", ("list_key", "value"), [
        {"list_key": item["system_key"], "value": o["value"], "label": o["label"], "level": o.get("level", 0),
         "parent_value": o.get("parent"), "translations": json.dumps(o.get("translations") or {}),
         "attrs": json.dumps(o.get("attrs") or {}), "sort_order": n, "active": True, **_stamp()}
        for item in lists for n, o in enumerate(item["options"])], {"translations": "jsonb", "attrs": "jsonb"})

    defaults = Path(__file__).resolve().parents[1] / "emails" / "defaults"
    emails: list[dict[str, Any]] = []
    for path in sorted(defaults.glob("*.json")):
        templates = json.loads(path.read_text(encoding="utf-8")).get("templates") or {}
        emails.extend({"key": key, "language": path.stem, "subject": t["subject"], "body": t["body"], **_stamp()}
                      for key, t in templates.items())
    counts["system_email_templates"] = _insert(conn, "system_email_templates", ("key", "language"), emails)

    catalogue = Path(__file__).resolve().parents[1] / "templates" / "data" / "system_templates.json"
    templates = json.loads(catalogue.read_text(encoding="utf-8"))["templates"]
    counts["system_templates"] = _insert(conn, "system_templates", ("key",), [
        {"key": t["key"], "category": t["category"], "icon": t.get("icon"), "tags": list(t.get("tags") or []),
         "minutes": int(t.get("minutes") or 0), "design": json.dumps(t.get("design") or {}),
         "schema": json.dumps(t["schema"]), "sort": i, **_stamp()} for i, t in enumerate(templates)],
        {"design": "jsonb", "schema": "jsonb"})
    counts["system_template_translations"] = _insert(conn, "system_template_translations", ("template_key", "language"), [
        {"template_key": t["key"], "language": "en", "name": t["name"], "description": t.get("description"), **_stamp()}
        for t in templates])

    counts["system_themes"] = _insert(conn, "system_themes", ("key",), [
        {"key": t["key"], "name_key": f"themes.presets.{t['key']}", "tokens": json.dumps(t["patch"]), "sort": i,
         **_stamp()} for i, t in enumerate(THEME_PRESETS)], {"tokens": "jsonb"})
    counts["system_page_designs"] = _insert(conn, "system_page_designs", ("key",), [
        {"key": t["key"], "name_key": f"pages.presets.{t['key']}", "tokens": json.dumps(t["patch"]), "sort": i,
         **_stamp()} for i, t in enumerate(PAGE_PRESETS)], {"tokens": "jsonb"})
    return counts
