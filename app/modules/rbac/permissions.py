"""Roles & access logic (F22), ported line by line from the frontend's shared/utils/auth/permissions.ts.

A grant has a scope: own (what the person made) · shared (forms others shared with them) · own_shared · all.
Actions without a scope are on / off (stored as `all`). A scope is a set of parts: own 1, shared 2, the rest 4.
Parity: tests/parity/test_permissions.py holds every function here to the frontend's recorded answers
(tests/vectors/frontend_rules.json), including `permission_for` for every endpoint of docs/ENDPOINTS.md.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Mapping

from app.modules.rbac.catalogue import (
    ALL_PERMISSIONS,
    PERMISSION_AREAS,
    PERMISSION_NEEDS,
)

Grants = dict[str, str]

PARTS = {"own": 1, "shared": 2, "own_shared": 3, "all": 7}
OWNER_ROLE = "owner"
ALL_GRANTS: Grants = {p: "all" for p in ALL_PERMISSIONS}

_DEFS: dict[str, tuple[str, ...] | None] = {
    f"{area['key']}.{action['key']}": (tuple(action["scopes"]) if action.get("scopes") else None)
    for area in PERMISSION_AREAS for group in area["groups"] for action in group["actions"]
}


def scope_parts(scope: str) -> int:
    return PARTS[scope]


def scopes_of(permission: str) -> tuple[str, ...] | None:
    """The scopes an action offers (None = on / off)."""
    return _DEFS.get(permission)


def is_permission(value: str) -> bool:
    return value in _DEFS


def _bits(mask: int) -> int:
    return (mask & 1) + ((mask >> 1) & 1) + ((mask >> 2) & 1)


def _cover(permission: str, mask: int) -> str:
    """The narrowest scope the action offers that covers all these parts."""
    offered = scopes_of(permission)
    if not offered:
        return "all"
    fits = sorted((s for s in offered if (PARTS[s] & mask) == mask), key=lambda s: _bits(PARTS[s]))
    return fits[0] if fits else "all"


def _within(permission: str, mask: int) -> str | None:
    """The widest scope the action offers inside these parts, or None."""
    offered = scopes_of(permission)
    if not offered:
        return "all" if mask == 7 else None
    fits = sorted((s for s in offered if (PARTS[s] & ~mask) == 0), key=lambda s: -_bits(PARTS[s]))
    return fits[0] if fits else None


def _fit(permission: str, scope: str) -> str:
    """A scope as the action offers it: the widest inside it, else the narrowest it has (never wider)."""
    offered = scopes_of(permission)
    if not offered:
        return "all"
    inside = _within(permission, PARTS[scope])
    return inside if inside is not None else sorted(offered, key=lambda s: _bits(PARTS[s]))[0]


def with_needs(grants: Mapping[str, str | None]) -> Grants:
    """Grants cleaned up (unknown actions dropped, scopes fitted), with what they need added as far as they reach."""
    out: Grants = {}
    for key, value in grants.items():
        if is_permission(key) and value and value in PARTS:
            out[key] = _fit(key, value)
    changed = True
    while changed:
        changed = False
        for item, scope in list(out.items()):
            for need in PERMISSION_NEEDS.get(item, []):
                has = out.get(need)
                wanted = _cover(need, (PARTS[has] if has else 0) | PARTS[scope])
                if wanted != has:
                    out[need] = wanted
                    changed = True
    return {item: out[item] for item in ALL_PERMISSIONS if out.get(item)}


def dependents_of(permission: str) -> list[str]:
    """Every action that needs this one, directly or through another."""
    found: list[str] = []
    seen: set[str] = set()
    changed = True
    while changed:
        changed = False
        for item, needs in PERMISSION_NEEDS.items():
            if item not in seen and any(n == permission or n in seen for n in needs):
                seen.add(item)
                found.append(item)
                changed = True
    return found


def set_grant(grants: Mapping[str, str], permission: str, scope: str | None) -> Grants:
    """One action changed in a role: what needs it follows (removed or held back); what it needs is added."""
    dependents = dependents_of(permission)
    nxt: dict[str, str | None] = dict(grants)
    if scope:
        nxt[permission] = _fit(permission, scope)
    reach = PARTS[nxt[permission]] if scope else 0  # type: ignore[index]
    for item in [permission, *dependents]:
        has = nxt.get(item)
        if not has or (item == permission and scope):
            continue
        kept = _within(item, PARTS[has] & reach)
        nxt[item] = kept if kept else None
    return with_needs({k: v for k, v in nxt.items() if v})


def reach_of(grants: Mapping[str, str]) -> float:
    """How much of the platform a role opens (0 to 1)."""
    total = sum(_bits(PARTS[s]) / 3 for s in with_needs(grants).values())
    return total / len(ALL_PERMISSIONS)


def areas_of(grants: Mapping[str, str]) -> int:
    return sum(1 for area in PERMISSION_AREAS if any(
        grants.get(f"{area['key']}.{action['key']}") for group in area["groups"] for action in group["actions"]))


# ── The permission an address needs ───────────────────────────────────────────

Rule = tuple[re.Pattern[str], "str | None | Callable[[bool], str | None]"]


def _resource_rules(base: str, area: str, method: str) -> list[Rule]:
    read = method == "GET"

    def p(action: str) -> str:
        return f"{area}.{action}"

    return [
        (re.compile(rf"^/{base}/[^/]+/duplicate$"), None if read else p("duplicate")),
        (re.compile(rf"^/{base}$"), None if read else p("create")),
        (re.compile(rf"^/{base}/[^/]+$"), None if read else (p("delete") if method == "DELETE" else p("edit"))),
        (re.compile(rf"^/{base}(/|$)"), None if read else p("edit")),
    ]


def _r(read_value: str | None, write_value: str | None) -> Callable[[bool], str | None]:
    return lambda read: read_value if read else write_value


def permission_for(method: str, path: str) -> str | None:
    """The permission an API call needs (method + path without /api/v1), or None for calls every signed-in
    person may make. First match wins (permissionFor)."""
    m = method.upper()
    read = m == "GET"
    p = path.split("?")[0]
    rules: list[Rule] = [
        (re.compile(r"^/(me|navigation|notifications|directory|auth|public|crypto|tenants|health|uploads|storage|files|"
                    r"downloads|response-files|response-exports|datasource-exports|help)(/|$)"), None),
        (re.compile(r"^/roles(/|$)"), _r("people.view", "roles.manage")),
        (re.compile(r"^/people/[^/]+/(approve|reject)$"), "people.approve"),
        (re.compile(r"^/people(/|$)"), _r("people.view", "people.manage")),
        (re.compile(r"^/org(/|$)"), _r(None, "people.manage")),
        (re.compile(r"^/forms/[^/]+/responses/export$"), "responses.export"),
        (re.compile(r"^/forms/[^/]+/responses(/|$)"), "responses.view"),
        (re.compile(r"^/responses/exports(/|$)"), "responses.export"),
        (re.compile(r"^/responses/[^/]+/files$"), "responses.view"),
        (re.compile(r"^/responses/[^/]+$"),
         lambda _: "responses.delete" if m == "DELETE" else ("responses.view" if read else "responses.review")),
        (re.compile(r"^/responses(/|$)"), _r("responses.view", "responses.review")),
        (re.compile(r"^/forms/pass$"), None),
        (re.compile(r"^/forms/import$"), "forms.import"),
        (re.compile(r"^/forms/[^/]+/duplicate$"), "forms.duplicate"),
        (re.compile(r"^/forms/[^/]+/publish$"), "forms.publish"),
        (re.compile(r"^/forms/trash$"), "forms.purge"),
        (re.compile(r"^/forms$"), _r("forms.view", "forms.create")),
        (re.compile(r"^/forms(/|$)"), "forms.view"),
        (re.compile(r"^/folders/[^/]+/access$"), "folders.access"),
        (re.compile(r"^/folders$"), _r(None, "folders.create")),
        (re.compile(r"^/folders/[^/]+$"),
         lambda _: None if read else ("folders.delete" if m == "DELETE" else "folders.edit")),
        (re.compile(r"^/folders(/|$)"), None),
        (re.compile(r"^/templates/translate-content$"), None),
        (re.compile(r"^/templates$"), _r(None, "forms.save_template")),
        (re.compile(r"^/templates/[^/]+/sync$"), "templates.edit"),
        *_resource_rules("templates", "templates", m),
        *_resource_rules("option-lists", "lists", m),
        *_resource_rules("themes", "themes", m),
        *_resource_rules("page-designs", "pages", m),
        *_resource_rules("field-library", "fields", m),
        (re.compile(r"^/analytics(/|$)"), "analytics.view"),
        (re.compile(r"^/datasources/[^/]+/explorer/rows$"), _r("data.browse", "data.rows")),
        (re.compile(r"^/datasources/[^/]+/explorer/(tables|changes)$"), _r("data.browse", "data.structure")),
        (re.compile(r"^/datasources/[^/]+/explorer/exports$"), "data.export"),
        (re.compile(r"^/datasources/[^/]+/explorer(/|$)"), "data.browse"),
        (re.compile(r"^/explorer-exports(/|$)"), "data.export"),
        (re.compile(r"^/datasources/[^/]+/query/export$"), "data.export"),
        (re.compile(r"^/datasources/[^/]+/(query|query-history)$"), "data.query"),
        (re.compile(r"^/datasources/test$"), "data.view"),
        (re.compile(r"^/datasources/[^/]+/test$"), "data.edit"),
        (re.compile(r"^/datasources/[^/]+/duplicate$"), "data.create"),
        (re.compile(r"^/datasources$"), _r("data.view", "data.create")),
        (re.compile(r"^/datasources/[^/]+$"),
         lambda _: "data.view" if read else ("data.delete" if m == "DELETE" else "data.edit")),
        (re.compile(r"^/datasources(/|$)"), "data.view"),
        (re.compile(r"^/saved-queries(/|$)"), _r("data.view", "data.saved")),
        (re.compile(r"^/destinations(/|$)"), _r("data.view", "data.storage")),
        (re.compile(r"^/api-service/key/rotate$"), "api.key"),
        (re.compile(r"^/api-service/limits$"), _r("api.view", "api.access")),
        (re.compile(r"^/api-access-rules/test$"), "api.view"),
        (re.compile(r"^/api-access-rules(/|$)"), _r("api.view", "api.access")),
        (re.compile(r"^/api-logs/settings$"), _r("api.view", "api.logs")),
        (re.compile(r"^/api-services/[^/]+/duplicate$"), "api.service_create"),
        (re.compile(r"^/api-services$"), _r("api.view", "api.service_create")),
        (re.compile(r"^/api-services/[^/]+$"),
         lambda _: "api.view" if read else ("api.service_delete" if m == "DELETE" else "api.service_edit")),
        (re.compile(r"^/api-endpoints/[^/]+/try$"), "api.try"),
        (re.compile(r"^/api-endpoints(/|$)"), _r("api.view", "api.endpoints")),
        (re.compile(r"^/api-tokens(/|$)"), _r("api.view", "api.tokens")),
        (re.compile(r"^/(webhooks|webhook-deliveries)(/|$)"), _r("api.view", "api.webhooks")),
        (re.compile(r"^/api-[a-z-]+(/|$)"), _r("api.view", "api.service_edit")),
        (re.compile(r"^/ai/settings$"), _r("ai.use", "ai.settings")),
        (re.compile(r"^/ai/requests/[^/]+/(apply|discard)$"), "ai.use"),
        (re.compile(r"^/ai/forms/[^/]+/assist$"), "ai.assist"),
        (re.compile(r"^/ai/forms/[^/]+/(translate|rewrite)$"), "ai.translate"),
        (re.compile(r"^/ai/(analysis|digest|ask)$"), "ai.analyse"),
        (re.compile(r"^/ai/responses/[^/]+/summary$"), "ai.analyse"),
        (re.compile(r"^/ai/(forms|templates|themes)/draft$"), "ai.create"),
        (re.compile(r"^/ai/requests(/|$)"), "ai.history"),
        (re.compile(r"^/ai(/|$)"), "ai.use"),
        (re.compile(r"^/audit-logs/export"), "audit.export"),
        (re.compile(r"^/audit-logs(/|$)"), "audit.view"),
        (re.compile(r"^/settings/(security|emails)(/|$)"), _r("settings.view", "settings.manage")),
        (re.compile(r"^/(settings|privacy|onboarding)(/|$)"), _r(None, "settings.manage")),
        (re.compile(r"^/billing/plans$"), _r(None, "settings.manage")),
        (re.compile(r"^/billing(/|$)"), _r("settings.view", "settings.manage")),
    ]
    for pattern, rule in rules:
        if pattern.search(p):
            return rule(read) if callable(rule) else rule
    return None
