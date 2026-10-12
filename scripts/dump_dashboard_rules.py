"""Records the frontend's dashboard and analytics rules (B12) into tests/vectors/dashboard_rules.json:

- shared/utils/dashboard/buckets.ts (`bucketStart`, `bucketsOf`, `groupFor`) and scope.ts (`scopeFrom`),
- `periodFrom` from server/mock/routes/dashboard.ts,
- `periodOf`, `seeded`, `daysOf`, `totalsOf` and `funnelOf` from server/mock/routes/analytics.ts.

The mock route files need the server to import, so their functions are cut out of the files as they are (between
fixed markers) and run on their own, with the clock held at chosen moments.

    fmly\\Scripts\\python.exe scripts\\dump_dashboard_rules.py [path\\to\\formalieFrontend]

tests/parity/test_dashboard_rules.py holds the ports (app/modules/dashboard/rules.py, app/modules/analytics/rules.py)
to these answers.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dump_frontend_rules import FRONTEND, ROOT, run_in_node  # noqa: E402

OUT = ROOT / "tests" / "vectors" / "dashboard_rules.json"


def cut(path: Path, start: str, end: str) -> str:
    """The text of a mock file from `start` up to (not including) `end`, without `export`."""
    text = path.read_text(encoding="utf-8")
    a = text.index(start)
    b = text.index(end, a)
    return text[a:b].replace("export function", "function")


def entry() -> str:
    routes = FRONTEND / "server" / "mock" / "routes"
    dashboard = cut(routes / "dashboard.ts", "const DAY = 86_400_000", "export const workspaceDashboard")
    analytics = cut(routes / "analytics.ts", "const DAY = 86_400_000", "const visibleForms")
    funnel = cut(routes / "analytics.ts", "/** Where people stop", "export const analyticsOverview")
    return r"""
import { DASHBOARD_GROUPS } from '__SHARED__/types/dashboard.ts'
import { bucketStart, bucketsOf, groupFor } from '__SHARED__/utils/dashboard/buckets.ts'
import { scopeFrom } from '__SHARED__/utils/dashboard/scope.ts'

let NOW = Date.UTC(2026, 9, 12, 15, 30)
const RealDate = Date
class HeldDate extends RealDate {
  constructor(...args) { if (args.length) super(...args); else super(NOW) }
  static now() { return NOW }
}
globalThis.Date = HeldDate

const D = (() => { __DASHBOARD__; return { periodFrom } })()
const responseSchema = form => form.published_schema ?? form.schema ?? null
const A = (() => { __ANALYTICS__; __FUNNEL__; return { periodOf, before, seeded, daysOf, totalsOf, funnelOf } })()

const DAY = 86_400_000
const iso = time => new RealDate(time).toISOString().slice(0, 10)
const nows = [Date.UTC(2026, 9, 12, 15, 30), Date.UTC(2026, 0, 1, 0, 0), Date.UTC(2024, 1, 29, 23, 59), Date.UTC(2027, 11, 31, 12)]

// Buckets
const times = [0, 1, -1, Date.UTC(2026, 9, 12), Date.UTC(2026, 9, 12, 23, 59, 59, 999), Date.UTC(2026, 9, 11), Date.UTC(2026, 9, 18),
  Date.UTC(2026, 9, 19), Date.UTC(2024, 1, 29, 6), Date.UTC(2025, 11, 31), Date.UTC(2026, 0, 1), Date.UTC(2021, 0, 3), Date.UTC(2021, 0, 4),
  Date.UTC(1999, 11, 31, 22), Date.UTC(2000, 2, 1), Date.UTC(1969, 11, 28), Date.UTC(2100, 1, 28), Date.UTC(1600, 1, 29), Date.UTC(9999, 11, 31)]
const starts = times.flatMap(time => DASHBOARD_GROUPS.map(group => ({ time, group, start: iso(bucketStart(time, group)) })))
const spans = [[Date.UTC(2026, 9, 1), Date.UTC(2026, 9, 30)], [Date.UTC(2026, 8, 13), Date.UTC(2026, 9, 12)], [Date.UTC(2026, 0, 1), Date.UTC(2026, 11, 31)],
  [Date.UTC(2025, 9, 13), Date.UTC(2026, 9, 12)], [Date.UTC(2020, 1, 29), Date.UTC(2026, 9, 12)], [Date.UTC(2026, 9, 12), Date.UTC(2026, 9, 12)],
  [Date.UTC(2026, 9, 13), Date.UTC(2026, 9, 12)], [Date.UTC(1990, 0, 1), Date.UTC(2026, 9, 12)], [Date.UTC(1900, 0, 1), Date.UTC(2026, 9, 12)],
  [Date.UTC(2026, 0, 31), Date.UTC(2026, 3, 30)], [Date.UTC(2024, 11, 30), Date.UTC(2025, 0, 5)]]
const buckets = spans.flatMap(([from, to]) => DASHBOARD_GROUPS.map(group => ({ from, to, group, buckets: bucketsOf(from, to, group) })))
const groups = [0, 1, 7, 30, 62, 63, 90, 365, 400, 401, 1000, 1500, 1501, 5000].map(days => ({ days, group: groupFor(days) }))

// The period (periodFrom)
const days = [undefined, '', '2026-10-12', '2026-10-01', '2026-09-13', '2026-01-01', '2025-10-13', '2026-12-31', '2026-02-30', '2026-02-31',
  '2026-02-32', '2026-13-01', '2026-00-10', '2026-04-31', '2024-02-29', '2026-1-01', '20261001', 'yesterday', '2026-10-12T00:00:00Z', '1999-12-31',
  '2030-06-15', '0050-03-15', 12]
const groupsAsked = [undefined, '', 'day', 'week', 'month', 'year', 'Day', 'decade']
const periods = []
for (const now of nows) {
  NOW = now
  for (const from of days) for (const to of days) {
    if ((days.indexOf(from) * 5 + days.indexOf(to)) % 7 && from !== undefined && to !== undefined) continue
    for (const group of groupsAsked.slice(0, from === undefined || to === undefined ? 8 : 2)) {
      const query = { from, to, group }
      const p = D.periodFrom(query)
      periods.push({ now, query, from: iso(p.from), to: iso(p.to), days: p.days, group: p.group, prev_from: iso(p.prevFrom), end: p.end - p.to, buckets: p.buckets })
    }
  }
}

// The forms filter (scopeFrom)
const forms = [{ folder: null, owner: { id: 'u1' } }, { folder: { id: 'f1' }, owner: { id: 'u1' } }, { folder: { id: 'f2' }, owner: { id: 'u2' } }, { folder: { id: 'none' }, owner: { id: 'none' } }]
const scopes = [{}, { folder: '' }, { folder: 'f1' }, { folder: 'none' }, { owner: 'u1' }, { owner: 'u2', folder: 'f2' }, { folder: 'f1', owner: 'u2' },
  { folder: 12 }, { owner: ['u1'] }, { folder: 'F1' }].map(query => { const s = scopeFrom(query); return { query, filtered: s.filtered, matches: forms.map(f => s.matches(f)) } })

// Analytics: periodOf, seeded, daysOf, totalsOf, funnelOf
const analyticsPeriods = []
for (const now of nows) {
  NOW = now
  for (const from of days) for (const to of days) {
    if ((days.indexOf(from) * 7 + days.indexOf(to)) % 4) continue
    const p = A.periodOf({ from, to })
    const b = A.before(p)
    analyticsPeriods.push({ now, query: { from, to }, from: iso(p.from), to: iso(p.to), days: p.days, before: [iso(b.from), iso(b.to), b.days] })
  }
}
const seeds = ['', 'a', 'form-1:2026-10-12', '0190a1b2-c3d4-7e5f-8a9b-0c1d2e3f4a5b:funnel', 'Café ☕ 😀 文字'].map(text => { const r = A.seeded(text); return { text, numbers: Array.from({ length: 6 }, () => r()) } })

let lcg = 12345
const rnd = () => (lcg = (lcg * 1103515245 + 12345) % 2147483648) / 2147483648
NOW = Date.UTC(2026, 9, 12, 15, 30)
const period = A.periodOf({})
const longer = A.periodOf({ from: '2026-01-01', to: '2026-10-12' })
const prev = A.before(period)
const formCases = [
  { id: '0190a1b2-c3d4-7e5f-8a9b-0c1d2e3f4a5b', status: 'published', completion_rate: 72, count: 40 },
  { id: '0190a1b2-c3d4-7e5f-8a9b-0c1d2e3f4a5c', status: 'published', completion_rate: 0, count: 0 },
  { id: '0190a1b2-c3d4-7e5f-8a9b-0c1d2e3f4a5d', status: 'closed', completion_rate: 10, count: 12 },
  { id: '0190a1b2-c3d4-7e5f-8a9b-0c1d2e3f4a5e', status: 'draft', completion_rate: 99, count: 3 },
  { id: '0190a1b2-c3d4-7e5f-8a9b-0c1d2e3f4a5f', status: 'archived', completion_rate: 50, count: 0 },
  { id: 'form-7', status: 'published', completion_rate: 100, count: 200 },
]
const schemas = [
  null,
  { pages: [{ title: 'About you', rows: [{ fields: [{ key: 'name', label: 'Name', type: 'full_name', required: true }, { key: 'email', label: 'Email', type: 'email', required: true }] },
    { fields: [{ key: 'intro', label: 'Intro', type: 'paragraph' }] }] },
    { title: '', rows: [{ fields: [{ key: 'cv', label: 'CV', type: 'file' }, { key: 'note', label: 'Anything else?', type: 'long_text' }] }] },
    { title: 'Thanks', rows: [] }] },
  { pages: [{ rows: [{ fields: [{ key: 'q1', label: 'Q1', type: 'rating', required: false }] }] }] },
  { pages: [{ title: 'Only text', rows: [{ fields: [{ key: 's', label: 'S', type: 'section' }] }] }] },
  { pages: [{ title: 'Long', rows: [{ fields: ['short_text', 'number', 'date', 'phone', 'address', 'matrix', 'ranking', 'signature', 'dropdown', 'checkbox'].map((type, i) => ({ key: `k${i}`, label: `L${i}`, type, required: i % 3 === 0 })) }] }] },
]
const analytics = formCases.flatMap((form, n) => {
  const entries = Array.from({ length: form.count }, () => {
    const at = longer.from + Math.floor(rnd() * (longer.days + 40)) * DAY - 40 * DAY * (rnd() < 0.3 ? 1 : 0) + Math.floor(rnd() * DAY)
    return { at, duration_seconds: rnd() < 0.2 ? null : Math.floor(rnd() * 900), channel: ['link', 'embed', 'api'][Math.floor(rnd() * 3)] }
  })
  return [period, longer, prev].map((p, k) => {
    const { daily, within } = A.daysOf(form, entries, p)
    const totals = A.totalsOf(daily, within)
    const schema = schemas[(n + k) % schemas.length]
    const funnel = A.funnelOf({ id: form.id, published_schema: schema }, totals)
    return { form, entries, period: { from: iso(p.from), to: iso(p.to), days: p.days }, daily, totals, schema, funnel }
  })
})

process.stdout.write(JSON.stringify({ about: 'Recorded from the frontend by scripts/dump_dashboard_rules.py. Do not edit.',
  starts, buckets, groups, periods, scopes, analytics_periods: analyticsPeriods, seeds, analytics }))
""".replace("__DASHBOARD__", dashboard).replace("__ANALYTICS__", analytics).replace("__FUNNEL__", funnel)


def main() -> None:
    result = run_in_node(entry(), {})
    OUT.write_text(json.dumps(result, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    print(f"Wrote {OUT.relative_to(ROOT)}: {len(result['starts'])} bucket starts, {len(result['buckets'])} bucket lists, "
          f"{len(result['periods'])} periods, {len(result['scopes'])} filters, {len(result['analytics_periods'])} analytics "
          f"periods, {len(result['analytics'])} form analytics")


if __name__ == "__main__":
    main()
