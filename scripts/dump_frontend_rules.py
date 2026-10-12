"""Records what the frontend's own shared/ code answers, into tests/vectors/frontend_rules.json.

    fmly\\Scripts\\python.exe scripts\\dump_frontend_rules.py [path\\to\\formalieFrontend]

The frontend is only read: esbuild (from its node_modules) bundles the shared modules into a temporary folder and
Node runs them. Recorded: the permission catalogue, built-in roles and needs, `permissionFor` for every endpoint
in docs/ENDPOINTS.md, `withNeeds` / `setGrant` cases, the audit event catalogue, the plans, the password policy
with test passwords, reserved subdomains. Then scripts/gen_frontend_catalogues.py turns the data parts into Python
modules, and the parity tests hold the hand-ported logic to the recorded answers. Run again whenever the
frontend's shared/ changes.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "tests" / "vectors" / "frontend_rules.json"
FRONTEND = Path(sys.argv[1] if len(sys.argv) > 1 else os.environ.get("FORMALIE_FRONTEND_DIR",
                                                                      r"C:\UNETPROJECTS\formalieFrontend"))

ENTRY = r"""
import { readFileSync } from 'node:fs'
import * as P from '__SHARED__/utils/auth/permissions.ts'
import * as E from '__SHARED__/utils/audit/events.ts'
import * as B from '__SHARED__/utils/billing/plans.ts'
import * as W from '__SHARED__/utils/auth/password.ts'
import * as H from '__SHARED__/utils/tenant/host.ts'
import * as L from '__SHARED__/utils/i18n/locales.ts'
import { SIGNIN_PROVIDERS } from '__SHARED__/utils/settings/schemas.ts'

const routes = JSON.parse(readFileSync(process.argv[2], 'utf8'))
const singles = []
for (const p of P.ALL_PERMISSIONS) for (const s of (P.scopesOf(p) ?? ['all'])) singles.push({ [p]: s })
const withNeedsCases = [...singles, P.DEFAULT_ROLE_GRANTS.member, P.DEFAULT_ROLE_GRANTS.admin,
  { 'forms.purge': 'own', 'data.rows': 'all' }, { 'forms.share': 'shared', 'forms.view': 'own' },
  { 'not.a.permission': 'all', 'forms.view': 'nonsense' }, { 'folders.edit': 'own_shared', 'templates.edit': 'shared' }]
const setGrantCases = []
for (const base of [P.DEFAULT_ROLE_GRANTS.member, P.DEFAULT_ROLE_GRANTS.admin, {}])
  for (const p of ['forms.view', 'forms.edit', 'forms.purge', 'responses.view', 'data.view', 'data.query_write', 'people.view', 'folders.edit', 'api.view', 'ai.use'])
    for (const s of [null, ...(P.scopesOf(p) ?? ['all'])]) setGrantCases.push({ base, permission: p, scope: s, result: P.setGrant(base, p, s) })
const passwords = ['', 'short', 'alllowercase1', 'NoDigitsHere', 'Correct-Horse-9', 'Formalie!2026', 'abcDEF123456789', 'Aa1!', 'Ünïcödé1Aa']
const policies = [W.DEFAULT_PASSWORD_POLICY, { min_length: 8, lower: false, upper: false, number: false, symbol: true }, { min_length: 12, lower: true, upper: true, number: true, symbol: true }]
const passwordCases = []
for (const policy of policies) for (const pw of passwords)
  passwordCases.push({ password: pw, policy, checks: W.checkPassword(pw, policy), meets: W.meetsPasswordPolicy(pw, policy), score: W.passwordScore(pw, policy) })

const out = {
  permission_areas: P.PERMISSION_AREAS,
  all_permissions: P.ALL_PERMISSIONS,
  scopes: P.SCOPES,
  built_in_roles: P.BUILT_IN_ROLES,
  built_in_role_text: P.BUILT_IN_ROLE_TEXT,
  default_role_grants: P.DEFAULT_ROLE_GRANTS,
  permission_needs: P.PERMISSION_NEEDS,
  resource_views: P.RESOURCE_VIEWS,
  resource_changes: P.RESOURCE_CHANGES,
  split_permissions: P.SPLIT_PERMISSIONS,
  permission_for: routes.map(([m, p]) => [m, p, P.permissionFor(m, p)]),
  with_needs: withNeedsCases.map(g => [g, P.withNeeds(g)]),
  set_grant: setGrantCases,
  reach: [P.DEFAULT_ROLE_GRANTS.member, P.DEFAULT_ROLE_GRANTS.admin].map(g => [g, P.reachOf(g), P.areasOf(g)]),
  audit_areas: E.AUDIT_AREAS,
  audit_events: E.AUDIT_EVENTS,
  plans: B.PLANS,
  period_months: B.PERIOD_MONTHS,
  period_discount: B.PERIOD_DISCOUNT,
  default_password_policy: W.DEFAULT_PASSWORD_POLICY,
  password_length_range: W.PASSWORD_LENGTH_RANGE,
  password_cases: passwordCases,
  reserved_subdomains: H.RESERVED_SUBDOMAINS,
  app_locales: L.APP_LOCALES,
  signin_providers: SIGNIN_PROVIDERS,
}
process.stdout.write(JSON.stringify(out))
"""


def endpoint_routes() -> list[list[str]]:
    """Every method + path of docs/ENDPOINTS.md (without /api/v1), params filled with sample values."""
    routes: list[list[str]] = []
    for line in (ROOT / "docs" / "ENDPOINTS.md").read_text(encoding="utf-8").splitlines():
        # Marked ✅ / ⬜ like the frontend's PROGRESS (2026-10-12); the old [x] / [ ] boxes still read
        m = re.match(r"^- (?:\[[ x]\]|✅|⬜) `(GET|POST|PUT|PATCH|DELETE) /api/v1(/[^`]*)`", line)
        if m:
            path = re.sub(r"\{[^}]+\}", "Xb7QmV2kP0aZr9LwE4tYh1sN3cU", m.group(2))
            routes.append([m.group(1), path])
    # A few more shapes the rules distinguish
    routes += [["GET", "/folders/abc"], ["PATCH", "/folders/abc"], ["DELETE", "/folders/abc"], ["GET", "/templates"],
               ["POST", "/templates"], ["GET", "/forms?status=draft"], ["GET", "/unknown/thing"]]
    return routes


def run_in_node(entry_js: str, argument: object = None) -> dict:
    """Bundles `entry_js` (`__SHARED__` = the frontend's shared/) with the frontend's esbuild, runs it with Node and
    returns what it printed as JSON. `argument` is handed over as a JSON file path (process.argv[2])."""
    esbuild = FRONTEND / "node_modules" / ".bin" / ("esbuild.cmd" if os.name == "nt" else "esbuild")
    shared = (FRONTEND / "shared").as_posix()
    with tempfile.TemporaryDirectory(prefix="formalie-rules-") as tmp:
        entry = Path(tmp) / "entry.ts"
        entry.write_text(entry_js.replace("__SHARED__", shared), encoding="utf-8")
        bundle = Path(tmp) / "rules.mjs"
        subprocess.run([str(esbuild), str(entry), "--bundle", "--format=esm", "--platform=node",
                        f"--alias:#shared={shared}", f"--outfile={bundle}", "--log-level=warning"],
                       check=True, cwd=FRONTEND)
        arg_file = Path(tmp) / "argument.json"
        arg_file.write_text(json.dumps(argument), encoding="utf-8")
        run = subprocess.run(["node", str(bundle), str(arg_file)], capture_output=True, text=True, encoding="utf-8")
    if run.returncode != 0:
        raise SystemExit(run.stderr)
    return json.loads(run.stdout)


def main() -> None:
    data = run_in_node(ENTRY, endpoint_routes())
    data["about"] = "Recorded from the frontend's shared/ code by scripts/dump_frontend_rules.py. Do not edit."
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {OUT.relative_to(ROOT)}: {len(data['permission_for'])} routes, {len(data['with_needs'])} withNeeds, "
          f"{len(data['set_grant'])} setGrant, {len(data['audit_events'])} audit events, {len(data['plans'])} plans")


if __name__ == "__main__":
    main()
