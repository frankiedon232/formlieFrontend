"""Records the frontend's forms rules into tests/vectors/forms_rules.json (B5):

- the FormSchema v1 validation (shared/utils/forms/schema.ts) over a real template's form and many changes to it:
  accepted or not, the cleaned schema, and every problem's field and message;
- a blank form in each of the 20 languages (the mock's blankFormSchema: the page title and texts localised);
- the lists the forms use (form actions, folder colours, limits) and the mock's slugify answers.

    fmly\\Scripts\\python.exe scripts\\dump_forms_rules.py [path\\to\\formalieFrontend]

The frontend is only read. Then scripts/gen_frontend_catalogues.py writes app/modules/forms/catalogues.py, and
tests/parity/test_forms_rules.py holds the port to these answers.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dump_frontend_rules import FRONTEND, ROOT, run_in_node  # noqa: E402

OUT = ROOT / "tests" / "vectors" / "forms_rules.json"

ENTRY = r"""
import { readFileSync } from 'node:fs'
import { formSchemaV1, countFields } from '__SHARED__/utils/forms/schema.ts'
import { blankSchema } from '__SHARED__/utils/forms/build.ts'
import { SYSTEM_TEMPLATES, templateSchema, localiseSchema } from '__SHARED__/templates/index.ts'
import { FOLDER_COLOR_KEYS } from '__SHARED__/utils/forms/folders.ts'
import { FORM_ACTIONS, RESPONSE_ACTIONS, TRASH_RETENTION_DAYS, FORM_CHANNELS } from '__SHARED__/types/forms.ts'
import { MAX_LARGE_OPTIONS, MAX_LIST_LEVELS } from '__SHARED__/utils/forms/options.ts'
import { APP_LOCALES } from '__SHARED__/utils/i18n/locales.ts'

const root = process.argv[2] ? JSON.parse(readFileSync(process.argv[2], 'utf8')).frontend : ''
const clone = v => JSON.parse(JSON.stringify(v))
const run = input => {
  const r = formSchemaV1.safeParse(input)
  return r.success ? { input, ok: true, data: r.data } : { input, ok: false, issues: r.error.issues.map(i => ({ path: i.path.join('.'), message: i.message })) }
}
const at = (base, path, value) => {
  const out = clone(base)
  const keys = path.split('.')
  let node = out
  for (const k of keys.slice(0, -1)) node = node[k]
  if (value === '__DELETE__') delete node[keys.at(-1)]
  else node[keys.at(-1)] = value
  return out
}

// A real form: the first system template in English, without branding, with fixed ids
const base = templateSchema(SYSTEM_TEMPLATES[0], { logo_url: null, primary: null })
const field = base.pages[0].rows[0].fields[0]
const variants = [
  ['schema_version', 2], ['schema_version', '1'], ['pages', []], ['pages.0.id', 'bad id!'], ['pages.0.id', 'x'.repeat(65)],
  ['pages.0.title', 'x'.repeat(201)], ['pages.0.rows.0.fields.0.key', 'Bad-Key'], ['pages.0.rows.0.fields.0.key', 'ok_key'],
  ['pages.0.rows.0.fields.0.type', 'X'], ['pages.0.rows.0.fields.0.width', 13], ['pages.0.rows.0.fields.0.width', 0.5],
  ['pages.0.rows.0.fields.0.label', 'x'.repeat(501)], ['pages.0.rows.0.fields.0.extra_prop', 'dropped'],
  ['pages.0.rows.0.fields.0.audience', { mode: 'department', ids: ['d1'] }], ['pages.0.rows.0.fields.0.audience', { mode: 'team' }],
  ['pages.0.rows.0.fields.0.options', [{ value: 'a', label: 'A', score: 1, attrs: { price: 5, code: 'X' } }]],
  ['pages.0.rows.0.fields.0.options', [{ value: 'a', label: 'A', attrs: { flag: true } }]],
  ['pages.0.rows.0.fields.0.options', [{ value: 'a' }]],
  ['pages.0.rows.0.fields.0.option_level', 4], ['pages.0.rows.0.fields.0.option_level', 3],
  ['pages.0.rows.0.fields.0.validation', { min: 1, anything: [1, 2] }], ['pages.0.rows.0.fields.0.validation', 'nope'],
  ['pages.0.rows.0.fields.0.props', { a: { b: 1 } }], ['pages.0.rows.0.fields.0.default', { any: 'thing' }],
  ['pages.0.rows.0.fields', Array.from({ length: 13 }, (_, i) => ({ ...clone(field), id: `f${i}`, key: `k${i}` }))],
  ['settings.language', 'x'.repeat(11)], ['settings.languages', Array.from({ length: 20 }, () => 'fr')],
  ['settings.label_position', 'right'], ['settings.identity', { email: null, verify: true }], ['settings.identity', { email: 'email' }],
  ['settings.retention_days', 3651], ['settings.retention_days', null],
  ['settings.emails', { team: ['u1'], others: ['a@b.example'], others_personal: false, receipt_field: null }],
  ['settings.emails', { team: [], others: ['not-an-email'], others_personal: false, receipt_field: null }],
  ['settings.guide', { enabled: true, title: 'Help', html: '<p>hi</p>' }], ['settings.unknown', 1],
  ['logic', Array.from({ length: 501 }, () => ({}))], ['logic', [{ any: 'rule' }]], ['calculations', 'no'],
  ['theme', { primary: '#fff' }], ['theme', 'blue'], ['theme_id', null], ['page_design_id', 'x'.repeat(65)],
  ['translations', { fr: { 'pages.0.title': 'Bonjour' } }], ['translations', { ['x'.repeat(11)]: { a: 'b' } }],
  ['translations', { fr: { a: 5 } }], ['translated_from', { fr: { a: 'x'.repeat(17) } }],
  ['thank_you', { title: 'Merci', message: 'ok', redirect_url: 'https://acme.example/done' }],
  ['thank_you', { redirect_url: 'not a url' }], ['thank_you', { redirect_url: 'javascript:alert(1)' }], ['thank_you', { redirect_url: null }],
  ['unknown_top', 1], ['settings', '__DELETE__'],
]
const cases = [base, ...variants.map(([p, v]) => at(base, p, v)), 'nonsense', null, [], { schema_version: 1 }]

// Blank forms per language (the mock's blankFormSchema)
const blank = {}
for (const { code } of APP_LOCALES) {
  let page = 'Page 1'
  try { page = JSON.parse(readFileSync(`${root}/i18n/locales/${code}.json`, 'utf8')).builder?.page?.default?.replace('{n}', '1') ?? page } catch {}
  let dict = null
  if (code !== 'en') try { dict = JSON.parse(readFileSync(`${root}/shared/templates/messages/${code}.json`, 'utf8')) } catch {}
  const schema = localiseSchema(blankSchema(page), dict, code)
  schema.pages[0].id = '__PAGE_ID__'
  blank[code] = schema
}

const slugify = value => value.toLowerCase().normalize('NFKD').replace(/[̀-ͯ]/g, '').replace(/[^a-z0-9]+/g, '-').replace(/(^-|-$)/g, '').slice(0, 60) || 'form'
const slugs = ['Customer feedback', '  Café — Orders!  ', 'Ünïcödé Fòrm', '日本語のフォーム', '---', 'x'.repeat(80), 'A/B test 2026']

process.stdout.write(JSON.stringify({
  form_actions: FORM_ACTIONS, response_actions: RESPONSE_ACTIONS, trash_retention_days: TRASH_RETENTION_DAYS,
  form_channels: FORM_CHANNELS, folder_color_keys: FOLDER_COLOR_KEYS, max_large_options: MAX_LARGE_OPTIONS,
  max_list_levels: MAX_LIST_LEVELS,
  schema_cases: cases.map(run), count_fields: countFields(base),
  blank_schemas: blank,
  slugs: slugs.map(value => ({ value, slug: slugify(value) })),
}))
"""


def main() -> None:
    data = run_in_node(ENTRY, {"frontend": FRONTEND.as_posix()})
    data["about"] = "Recorded from the frontend's shared/ code by scripts/dump_forms_rules.py. Do not edit."
    OUT.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {OUT.relative_to(ROOT)}: {len(data['schema_cases'])} schema cases, "
          f"{len(data['blank_schemas'])} blank forms")


if __name__ == "__main__":
    main()
