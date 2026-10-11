"""Records the frontend's submission rules (B7) into tests/vectors/submission_rules.json, and Node's Intl answers
the port needs into app/modules/forms/data/intl.json:

- checkSubmission (shared/utils/forms/submission.ts) on every system template with generated answers, and on
  hand-made forms with logic, jumps, levels, auto-fill and calculations;
- calculateResult (formula.ts), ruleMatches (logic.ts), validateAnswer (validate.ts) on many cases;
- currencies and time zones as Node's Intl accepts them (validate.ts uses Intl);
- the proof of work (proof-of-work.ts).

    fmly\\Scripts\\python.exe scripts\\dump_submission_rules.py [path\\to\\formalieFrontend]

tests/parity/test_submission_rules.py holds the port (app/modules/forms/formula.py, logic.py, answers.py,
app/modules/public/submit.py, pow.py) to these answers.
"""

from __future__ import annotations

import json
import sys
import zoneinfo
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dump_frontend_rules import ROOT, run_in_node  # noqa: E402

OUT = ROOT / "tests" / "vectors" / "submission_rules.json"
INTL = ROOT / "app" / "modules" / "forms" / "data" / "intl.json"

ENTRY = r"""
import { readFileSync } from 'node:fs'
import { createHash } from 'node:crypto'
import { SYSTEM_TEMPLATES } from '__SHARED__/templates/index.ts'
import { buildSchema } from '__SHARED__/templates/kit.ts'
import { checkSubmission } from '__SHARED__/utils/forms/submission.ts'
import { calculateResult } from '__SHARED__/utils/forms/formula.ts'
import { ruleMatches, evaluateLogic } from '__SHARED__/utils/forms/logic.ts'
import { validateAnswer } from '__SHARED__/utils/forms/validate.ts'
import { hasLeadingZeroBits } from '__SHARED__/utils/forms/proof-of-work.ts'
import { allFields } from '__SHARED__/utils/forms/build.ts'

const input = JSON.parse(readFileSync(process.argv[2], 'utf8'))

// ── Deterministic answers ────────────────────────────────────────────────────
let seed = 20261011
const rand = () => { seed = (seed + 0x6D2B79F5) | 0; let t = Math.imul(seed ^ (seed >>> 15), 1 | seed); t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296 }
const pick = list => list[Math.floor(rand() * list.length)]
const values = field => (field.options ?? []).map(o => o.value)
function answerFor(field) {
  const v = values(field)
  switch (field.type) {
    case 'short_text': case 'long_text': case 'hidden': return pick(['Hello', '', '  spaced  ', 'x'.repeat(301), 42, 'Ünïcödé 😀', null])
    case 'rich_text': return pick(['<p>Hi</p>', '<p> </p>', '<b>&nbsp;</b>', '<p>' + 'y'.repeat(50) + '</p>'])
    case 'email': return pick(['ana@example.org', 'ANA@EXAMPLE.ORG ', 'bad@', 'a@b.c', ''])
    case 'phone': return pick(['+44 7700 900123', '(020) 7946-0018', '12', 'phone'])
    case 'url': return pick(['https://example.org/a', 'http://localhost', 'ftp://x.example', 'example.org', 'https://1234', 'https://ex ample.org'])
    case 'number': case 'currency': case 'percentage': case 'slider': case 'scale': case 'rating': return pick([5, '12', 'abc', -3, 1e6, '', 0, '0x10', ' 7 ', true])
    case 'dropdown': case 'radio': case 'country': return pick([...v, ...v, 'nope', '', null])
    case 'checkbox': case 'multi_select': case 'ranking': return pick([v.slice(0, 1), v.slice(0, 2), v, [], ['nope'], v.slice(1, 3)])
    case 'toggle': case 'consent': return pick([true, false, null, 'yes'])
    case 'date': return pick(['2026-01-05', '2025-12-31', '', 'x', '2026-13-40'])
    case 'datetime': return pick(['2026-01-05T10:00', ''])
    case 'time': return pick(['09:30', ''])
    case 'date_range': return pick([{ from: '2026-01-01', to: '2026-01-05' }, { from: '2026-02-01', to: '2026-01-05' }, { from: '2026-01-01' }, {}])
    case 'duration': return pick([{ hours: 1, minutes: 30 }, { hours: 0, minutes: 0 }, { minutes: 75 }, { hours: '2' }, {}])
    case 'full_name': return pick([{ first: 'Ana', last: 'Silva' }, { first: 'Ana' }, {}, { first: ' ', last: ' ' }])
    case 'address': return pick([{ line1: '1 Main St', city: 'Leeds', postal_code: 'LS1 1AA', country: 'GB' }, { line1: '1 Main St' }, {}, { line1: '2 High St', city: 'Nairobi', country: 'KE', region: 'Nairobi' }])
    case 'file_upload': case 'image_upload': return pick([[{ id: 'f1', name: 'a.pdf', size: 10, type: 'application/pdf' }], [], [{ id: 'f1', name: 'a', size: 1, type: 'x' }, { id: 'f2', name: 'b', size: 1, type: 'x' }]])
    case 'signature': return pick(['data:image/png;base64,AAA', ''])
    case 'matrix': return pick([{ r1: 'a' }, {}])
    case 'language': return pick(['en', 'fr', 'xx', 'EN'])
    case 'timezone': return pick(['Europe/London', 'europe/london', 'Mars/Base', 'UTC', 'US/Eastern'])
    case 'currency_code': return pick(['EUR', 'eur', 'XYZ', 'KES'])
    case 'ip_address': return pick(['192.0.2.10', '2001:db8::1', '999.1.1.1', '::ffff:192.0.2.1'])
    case 'domain': return pick(['example.com', 'example.com.', '-bad.com', 'localhost'])
    case 'mac_address': return pick(['00:1A:2B:3C:4D:5E', '001A.2B3C.4D5E', '00:1A'])
    case 'iban': return pick(['GB82 WEST 1234 5698 7654 32', 'GB00WEST12345698765432'])
    case 'bic': return pick(['DEUTDEFF', 'deutdeff500', 'XX'])
    case 'color': return pick(['#00AAff', '#abc', 'red'])
    case 'calculated': return pick([999, 'client value'])
    default: return pick(['x', '', null])
  }
}
function answersFor(schema, mode) {
  const out = {}
  for (const field of allFields(schema)) {
    if (mode === 'empty') continue
    if (mode === 'some' && rand() < 0.5) continue
    out[field.key] = answerFor(field)
  }
  if (mode !== 'empty') out.unknown_key = 'dropped'
  return out
}

// ── Hand-made forms: jumps, levels, auto-fill, calculations, set values ─────────
const f = (id, key, type, extra = {}) => ({ id, key, type, label: key, ...extra })
const handmade = [{
  schema_version: 1, settings: {}, calculations: [], thank_you: {},
  pages: [
    { id: 'p1', title: 'One', rows: [{ id: 'r1', fields: [
      f('f_plan', 'plan', 'radio', { required: true, options: [{ value: 'basic', label: 'Basic', score: 10 }, { value: 'premium', label: 'Premium', score: 50 }] }),
      f('f_qty', 'qty', 'number', { required: true, validation: { min: 1, max: 10 } }),
      f('f_total', 'total', 'calculated', { props: { formula: '{plan} * {qty}' } }),
      f('f_level', 'level', 'calculated', { props: { formula: 'if({total} >= 100, "High", "Low")' } }),
      f('f_skip', 'skip', 'toggle'),
    ] }] },
    { id: 'p2', title: 'Two', rows: [{ id: 'r2', fields: [
      f('f_country', 'country_pick', 'dropdown', { required: true, options: [{ value: 'ke', label: 'Kenya' }, { value: 'br', label: 'Brazil' }] }),
      f('f_city', 'city', 'dropdown', { required: true, option_parent: 'f_country', options: [{ value: 'nbo', label: 'Nairobi', parent: 'ke' }, { value: 'sp', label: 'São Paulo', parent: 'br' }, { value: 'rio', label: 'Rio', parent: 'br' }] }),
      f('f_product', 'product', 'dropdown', { options: [{ value: 'desk', label: 'Desk', attrs: { price: 420, category: 'Furniture' } }, { value: 'lamp', label: 'Lamp', attrs: { price: '32,5', category: 'Furniture' } }], props: { fills: [{ column: 'price', target: 'f_price', lock: true }, { column: 'category', target: 'f_cat' }] } }),
      f('f_price', 'price', 'currency'),
      f('f_cat', 'cat', 'short_text'),
      f('f_cost', 'cost', 'calculated', { props: { formula: '{product.price} * {qty}' } }),
      f('f_secret', 'secret', 'short_text', { required: true }),
    ] }] },
    { id: 'p3', title: 'Three', rows: [{ id: 'r3', fields: [f('f_note', 'note', 'long_text', { required: true, validation: { min_length: 5, pattern: '^[A-Z]' } })] }] },
  ],
  logic: [
    { id: 'l1', when: { all: [{ field: 'f_skip', op: 'true' }] }, then: [{ action: 'jump', target: 'p3' }] },
    { id: 'l2', when: { all: [{ field: 'f_plan', op: 'eq', value: 'premium' }] }, then: [{ action: 'hide', target: 'f_secret' }, { action: 'set_value', target: 'f_cat', value: 'VIP' }] },
    { id: 'l3', when: { any: [{ field: 'f_qty', op: 'gt', value: 5 }, { field: 'f_product', detail: 'price', op: 'gte', value: 400 }] }, then: [{ action: 'unrequire', target: 'f_note' }] },
    { id: 'l4', when: { all: [{ field: 'f_plan', op: 'empty' }] }, then: [{ action: 'skip_to_end' }] },
  ],
}]
const handAnswers = [
  {}, { plan: 'basic', qty: 3, skip: true, note: 'Hello there' }, { plan: 'premium', qty: '4', country_pick: 'br', city: 'nbo', product: 'lamp', note: 'lower' },
  { plan: 'basic', qty: 11, country_pick: 'ke', city: 'nbo', product: 'desk', price: 1, cat: 'Mine', secret: 's', note: 'Abcdef' },
  { plan: 'premium', qty: 2, country_pick: 'br', city: ['sp', 'x'], product: 'desk', cat: 'Furniture', note: 'Abc' },
  { plan: 'basic', qty: 6, country_pick: 'br', city: 'rio', product: 'lamp', cat: '', secret: '', note: '' },
]

// ── Submissions ──────────────────────────────────────────────────────────────
const submissions = []
for (const def of SYSTEM_TEMPLATES) {
  const schema = buildSchema(def)
  for (const mode of ['empty', 'all', 'some', 'some', 'all']) {
    const answers = answersFor(schema, mode)
    submissions.push({ template: def.key, answers, result: checkSubmission(schema, answers) })
  }
}
const custom = handmade.flatMap(schema => handAnswers.map(answers => ({ schema, answers, result: checkSubmission(schema, answers), logic: (s => ({ hidden: [...s.hidden].sort(), hiddenPages: [...s.hiddenPages].sort(), required: [...s.required].sort(), optional: [...s.optional].sort(), disabled: [...s.disabled].sort(), enabled: [...s.enabled].sort(), values: Object.fromEntries(s.values), jumps: Object.fromEntries(s.jumps) }))(evaluateLogic(schema, answers)) })))

// ── Formulas ─────────────────────────────────────────────────────────────────
const fields = new Map([
  ['size', { id: 's', key: 'size', type: 'radio', options: [{ value: 's', label: 'Small', score: 1 }, { value: 'l', label: 'Large', score: 3 }] }],
  ['extras', { id: 'e', key: 'extras', type: 'checkbox', options: [{ value: 'a', label: 'A', score: 2 }, { value: 'b', label: 'B', score: 5 }] }],
  ['tags', { id: 't', key: 'tags', type: 'checkbox', options: [{ value: 'x', label: 'X' }, { value: 'y', label: 'Y' }] }],
  ['plan', { id: 'p', key: 'plan', type: 'dropdown', options: [{ value: 'premium', label: 'Premium' }, { value: '10', label: 'Ten' }] }],
  ['product', { id: 'pr', key: 'product', type: 'multi_select', options: [{ value: 'desk', label: 'Desk', attrs: { price: 420, region: 'North' } }, { value: 'lamp', label: 'Lamp', attrs: { price: '32,5', region: 'South' } }, { value: 'pen', label: 'Pen', attrs: { region: '' } }] }],
])
const formulas = ['{a} + {b}', '{a} * {b} / 3', '{a} - -{b}', '({a} + 1) * (2 - {b})', 'if({plan} = "premium", 50, 10)', 'if({plan} = "Premium", "Yes", "No")',
  '{size} + {extras}', 'count({tags})', '{tags} = "x"', 'round(max({a}, {b}) * 1.2, 2)', 'round(2.5)', 'round(-2.5)', 'round(1.005, 2)', 'round({a}, 20)', 'avg({a}, {b}, {c})',
  'sum({a}, {c})', 'min({c})', 'count({a}, {b}, {c})', 'days({d1}, {d2})', 'days({d1}, {c})', 'abs(-{a})', 'floor(-{a} / 3)', 'ceil({a} / 3)',
  '{a} >= {b}', '{a} <> {b}', 'and({a}, {b})', 'or({c}, 0)', 'not({a})', 'not()', 'if(1, 2)', '1 / 0', '0 / 0', '"text"', '""', '"12" + 1', '{t} = "Hello"',
  '{product.price} * 2', '{product.region} = "north"', '{product.missing}', '{a} +', '', '((1)', 'foo(1)', '{A} + 1', '1 + 2 * 3 - 4 / 8', '0.1 + 0.2', '1e3', '{a}{b}',
  'if({flag}, "on", "off")', '{flag} + 1', '{n} * 1', '{s} = "abc"', '{big} * {big}', 'round(10 / 3, 6)', 'max()', '{a} = 3', '{a} == "3"', '{plan} = 10', '{u} + 1', '-{a}',
  'if({a} > 2, {plan}, "none")', 'round({a} / 7, 3.7)', 'avg()', 'days("2024-02-28", "2024-03-01")', 'days("2024-02-28T23:00", "2024-03-01x")', '{a} * 1 < 4 > 0']
const answerSets = [
  { a: 3, b: 4, c: '', plan: 'premium', size: 'l', extras: ['a', 'b'], tags: ['x'], d1: '2024-01-01', d2: '2024-03-01', product: ['desk', 'lamp'], flag: true, n: ' 8 ', s: 'ABC', big: 1e200, t: 'hello', u: 'abc' },
  { a: '2.5', b: '-1', plan: '10', size: 's', extras: [], tags: [], d1: '2024-12-31', d2: '2024-01-01', product: ['pen'], flag: false, n: '0x1F', s: 'x', big: 3 },
  { a: 'abc', b: null, c: 7, plan: 'other', tags: ['x', 'y', 'z'], product: 'desk', d1: 'nope', d2: '2024-01-01' },
  {},
]
const formulaCases = formulas.flatMap(formula => answerSets.map((answers, set) => ({ formula, set, result: calculateResult(formula, answers, fields) })))

// ── Conditions ───────────────────────────────────────────────────────────────
const ops = ['eq', 'neq', 'contains', 'not_contains', 'starts_with', 'ends_with', 'empty', 'not_empty', 'gt', 'gte', 'lt', 'lte', 'between', 'not_between', 'in', 'not_in', 'contains_all', 'count_gte', 'count_lte', 'true', 'false', 'before', 'after']
const condValues = [[undefined, undefined], ['abc', undefined], [5, undefined], ['5', '10'], [['a', 'b'], undefined], ['2026-01-01', '2026-12-31'], [2, undefined], ['', ''], [null, 8], [0, undefined]]
const condAnswers = ['abc', 'ABCdef', '', null, undefined, 5, '7', 12, true, false, ['a', 'b'], [], ['a'], '2026-06-01', '2025-01-01', { line1: 'x' }, { line1: '' }, 0, 'b']
const conditionCases = []
for (const op of ops) for (const [value, value2] of condValues) for (const answer of condAnswers) {
  const rule = { id: 'r', when: { all: [{ field: 'f', op, ...(value !== undefined ? { value } : {}), ...(value2 !== undefined ? { value2 } : {}) }] }, then: [] }
  const answers = answer === undefined ? {} : { k: answer }
  conditionCases.push({ rule, answers, result: ruleMatches(rule, answers, id => (id === 'f' ? 'k' : undefined)) })
}
const detailField = { id: 'f', key: 'k', type: 'multi_select', options: [{ value: 'desk', label: 'Desk', attrs: { price: 420, region: 'North' } }, { value: 'lamp', label: 'Lamp', attrs: { price: '32,5', region: 'South' } }] }
for (const op of ['eq', 'gt', 'between', 'contains', 'empty', 'in']) for (const answer of ['desk', ['desk', 'lamp'], 'lamp', [], 'none']) for (const detail of ['price', 'region', 'nope']) {
  const rule = { id: 'r', when: { any: [{ field: 'f', detail, op, value: op === 'between' ? 100 : op === 'contains' ? 'nor' : op === 'in' ? ['North'] : 420, value2: 500 }] }, then: [] }
  conditionCases.push({ rule, answers: { k: answer }, detailField: true, result: ruleMatches(rule, { k: answer }, () => 'k', () => detailField) })
}

// ── Single answers ───────────────────────────────────────────────────────────
const vf = (type, extra = {}) => ({ id: 'v', key: 'v', type, label: 'v', ...extra })
const validateFields = [
  vf('short_text', { validation: { min_length: 3, max_length: 5, pattern: '^[a-z]+$' } }), vf('short_text', { validation: { pattern: '(?<word>a)\\k<word>' } }), vf('short_text', { validation: { pattern: '[' } }),
  vf('long_text', { validation: { max_length: '4' } }), vf('email'), vf('url'), vf('phone'), vf('number', { validation: { min: 1, max: '10.5' } }), vf('rating'), vf('percentage', { validation: { min: 0, max: 100 } }),
  vf('rich_text', { validation: { max_length: 5 } }), vf('checkbox', { validation: { min_selected: 2, max_selected: 3 } }), vf('multi_select'), vf('file_upload', { props: { max_files: 2 } }), vf('image_upload'),
  vf('address'), vf('address', { props: { require_region: true, require_postal_code: false } }), vf('full_name'), vf('consent'), vf('duration'), vf('date_range'),
  vf('ip_address'), vf('ip_address', { props: { ip_version: 'v6' } }), vf('ip_address', { props: { ip_version: 'v4' } }), vf('domain'), vf('mac_address'), vf('iban'), vf('bic'), vf('color'),
  vf('language'), vf('timezone'), vf('currency_code'), vf('date'), vf('toggle'), vf('dropdown', { options: [{ value: 'a', label: 'A' }] }),
]
const validateValues = ['', ' ', 'ab', 'abc', 'abcdef', 'ABC', 'aa', 'Hello', 5, 0, -1, '12', '10.6', 'x', '1e1', true, false, null, undefined, [], ['a'], ['a', 'b', 'c', 'd'],
  { line1: 'x' }, { line1: '1 Main', city: 'Leeds', country: 'GB', postal_code: 'LS1' }, { line1: '1 Main', city: 'Leeds', country: 'GB' }, { first: 'A', last: 'B' }, { first: 'A' },
  { hours: 1, minutes: 0 }, { hours: 0, minutes: 60 }, { hours: -1 }, { minutes: '5' }, { hours: 'x' }, { from: '2026-01-02', to: '2026-01-01' }, { from: '2026-01-01', to: '2026-01-02' }, { to: '2026-01-01' },
  'ana@example.org', 'ana@example', 'a@b.co', 'ana@@example.org', 'https://example.org', 'http://example', 'https://例え.テスト', 'https://example。org', 'https://1234', 'https://0x7f.1', 'http://[::1]',
  'https://user:pw@example.org:8080/x', 'https://example.org:99999', 'javascript:alert(1)', 'https://exa mple.org', 'HTTPS://EXAMPLE.ORG', 'https:example.org', 'https:\\\\example.org', 'https://ex%41mple.org',
  'https://.', 'https://a..b', '+44 7700 900123', '(020) 7946-0018', '123', '192.0.2.1', '192.168.001.1', '::1', '2001:db8::1', '2001:db8:0:0:0:0:0:1', '::ffff:192.0.2.1', '1:2:3:4:5:6:7:8:9',
  'example.com', 'example.com.', 'ex_ample.com', 'a-.com', '00:1a:2b:3c:4d:5e', '001A.2B3C.4D5E', 'GB82 WEST 1234 5698 7654 32', 'GB82WEST12345698765433', 'DEUTDEFF500', 'deut de ff',
  '#00AAFF', '#00AAF', 'en', 'xx', 'Europe/London', 'europe/LONDON', 'US/Eastern', 'Asia/Calcutta', 'Mars/Phobos', 'UTC', 'utc', 'GMT', 'Etc/GMT+5', '+05:00', '+0530', 'EST', 'EUR', 'eur', 'XXX', 'XTS',
  '<p>Hi</p>', '<p>&nbsp;</p>', '<p>Hello world</p>', '&amp;&#160;', [{ id: 'f', name: 'a', size: 1, type: 't' }], [{}, {}, {}], 'Ünïcödé', '😀😀😀😀😀😀', ' 7 ', '0x10']
const validateCases = validateFields.flatMap(field => validateValues.flatMap(value => [true, false].map(required => ({ field, value: value === undefined ? '__undefined__' : value, required, result: validateAnswer(field, value, required) }))))

// ── Intl (what validate.ts accepts through Node's Intl) ─────────────────────────
const accepted = zone => { try { new Intl.DateTimeFormat('en', { timeZone: zone }); return true } catch { return false } }
const zones = [...new Set([...input.zones, ...Intl.supportedValuesOf('timeZone')])].filter(accepted)
const offsets = ['+05:00', '-0800', '+05', '+24:00', '+05:60', '-00:00', '+5:00', '+05:30:00'].map(value => ({ value, ok: accepted(value) }))

// ── Proof of work ────────────────────────────────────────────────────────────
const pow = []
for (const salt of ['abc', 'f0rm:salt', 'x'.repeat(40)]) for (let nonce = 0; nonce < 40; nonce++) {
  const hash = new Uint8Array(createHash('sha256').update(`${salt}:${nonce}`).digest())
  pow.push({ salt, nonce, bits: [0, 1, 4, 8, 9, 12].map(bits => hasLeadingZeroBits(hash, bits)) })
}

process.stdout.write(JSON.stringify({
  intl: { currencies: Intl.supportedValuesOf('currency'), zones_lower: [...new Set(zones.map(z => z.toLowerCase()))].sort() },
  vectors: { about: 'Recorded from the frontend by scripts/dump_submission_rules.py. Do not edit.', submissions, custom, formulas: formulaCases, answer_sets: answerSets,
    conditions: conditionCases.map(c => ({ ...c, answers: c.answers })), validate: validateCases, offsets, pow },
}))
"""


def main() -> None:
    result = run_in_node(ENTRY, {"zones": sorted(zoneinfo.available_timezones())})
    INTL.parent.mkdir(parents=True, exist_ok=True)
    INTL.write_text(json.dumps({"about": "Node's Intl answers, recorded by scripts/dump_submission_rules.py. Do not edit.",
                                **result["intl"]}, ensure_ascii=False) + "\n", encoding="utf-8")
    OUT.write_text(json.dumps(result["vectors"], ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    v = result["vectors"]
    print(f"Wrote {INTL.relative_to(ROOT)} and {OUT.relative_to(ROOT)}: {len(v['submissions'])} submissions, "
          f"{len(v['custom'])} hand-made, {len(v['formulas'])} formulas, {len(v['conditions'])} conditions, "
          f"{len(v['validate'])} answers")


if __name__ == "__main__":
    main()
