"""Formalie's template catalogue for the backend (B6), from the frontend's shared/templates:

- app/modules/templates/data/system_templates.json: every system template (key, category, icon, minutes, name,
  description, tags, its own design patch) with its built English form (buildSchema), and the onboarding starters;
- tests/vectors/templates_rules.json: a fingerprint (SHA-256 of sorted JSON) of every template in every language
  and two brandings as the mock serves it (localiseSchema(templateSchema(def, branding), dictionary, language)),
  of each language's translation dictionary, and translateContent cases. tests/parity/test_templates_rules.py
  holds the port to them.

    fmly\\Scripts\\python.exe scripts\\dump_templates_rules.py [path\\to\\formalieFrontend]

Run scripts/sync_frontend_data.py first (it copies the message files the port reads).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dump_frontend_rules import FRONTEND, ROOT, run_in_node  # noqa: E402

DATA = ROOT / "app" / "modules" / "templates" / "data" / "system_templates.json"
OUT = ROOT / "tests" / "vectors" / "templates_rules.json"

ENTRY = r"""
import { readFileSync } from 'node:fs'
import { createHash } from 'node:crypto'
import { SYSTEM_TEMPLATES, templateSchema, localiseSchema, translateContent } from '__SHARED__/templates/index.ts'
import { buildSchema } from '__SHARED__/templates/kit.ts'
import { starterSchema } from '__SHARED__/utils/forms/build.ts'
import { STARTER_TEMPLATE_KEYS } from '__SHARED__/utils/templates/starters.ts'
import { APP_LOCALES } from '__SHARED__/utils/i18n/locales.ts'

const root = JSON.parse(readFileSync(process.argv[2], 'utf8')).frontend
const read = path => { try { return JSON.parse(readFileSync(`${root}/${path}`, 'utf8')) } catch { return null } }
const sorted = value => Array.isArray(value) ? value.map(sorted) : value && typeof value === 'object'
  ? Object.fromEntries(Object.keys(value).sort().map(k => [k, sorted(value[k])])) : value
const hash = value => createHash('sha256').update(JSON.stringify(sorted(value))).digest('hex')

const codes = APP_LOCALES.map(l => l.code)
const content = Object.fromEntries(codes.map(c => [c, c === 'en' ? null : read(`shared/templates/messages/${c}.json`)]))

// The mock's translationDict (server/mock/data/templateStore.ts): vocabulary, builder defaults, template text
const builderDict = code => {
  const en = read('i18n/locales/en.json')?.builder, local = read(`i18n/locales/${code}.json`)?.builder
  const dict = {}
  if (!en || !local) return dict
  for (const [type, text] of Object.entries(en.field ?? {})) if (typeof text === 'string' && typeof local.field?.[type] === 'string') dict[text] = local.field[type]
  for (const [source, target] of [[en.defaults?.option, local.defaults?.option], [en.defaults?.row, local.defaults?.row], [en.page?.default, local.page?.default]])
    if (source && target) for (let n = 1; n <= 50; n++) dict[source.replace('{n}', String(n))] = target.replace('{n}', String(n))
  return dict
}
const translationDict = code => {
  if (code === 'en') return null
  const merged = { ...(read(`shared/templates/vocabulary/${code}.json`) ?? {}), ...builderDict(code), ...(content[code] ?? {}) }
  return Object.keys(merged).length ? merged : null
}

const brandings = [{ logo_url: null, primary: null }, { logo_url: '/api/v1/files/AbCdEfGhIjKlMnOpQrStUvWxYz0', primary: '#0055FF' }]
const fingerprints = []
for (const def of SYSTEM_TEMPLATES)
  for (const code of codes)
    brandings.forEach((b, i) => fingerprints.push({ key: def.key, language: code, branding: i, hash: hash(localiseSchema(templateSchema(def, b), content[code], code)) }))

const base = templateSchema(SYSTEM_TEMPLATES[0], brandings[0])
const own = JSON.parse(JSON.stringify(base))
own.pages[0].title = 'My own heading'
own.pages[0].rows[0].fields[0].label = '  how LIKELY are you   to recommend us to a friend or colleague?  '
const translateCases = [['en', 'fr', base], ['fr', 'de', localiseSchema(base, content.fr, 'fr')], ['en', 'ja', own], ['de', 'en', localiseSchema(own, content.de, 'de')]]
  .map(([from, to, schema]) => { const r = translateContent(schema, translationDict(from), translationDict(to)); return { from, to, schema, hash: hash(r.schema), translated: r.translated, kept: r.kept } })

process.stdout.write(JSON.stringify({
  data: {
    templates: SYSTEM_TEMPLATES.map(def => ({ key: def.key, category: def.category, icon: def.icon, minutes: def.minutes, name: def.name,
      description: def.description, tags: def.tags ?? [], design: def.design ?? {}, schema: buildSchema(def) })),
    starters: Object.fromEntries(STARTER_TEMPLATE_KEYS.map(key => [key, SYSTEM_TEMPLATES.some(def => def.key === key) ? null : starterSchema(key)])),
  },
  vectors: { brandings, fingerprints, dictionaries: Object.fromEntries(codes.map(c => [c, translationDict(c) ? hash(translationDict(c)) : null])), translate: translateCases },
}))
"""


def main() -> None:
    result = run_in_node(ENTRY, {"frontend": FRONTEND.as_posix()})
    DATA.parent.mkdir(parents=True, exist_ok=True)
    DATA.write_text(json.dumps({"about": "Generated by scripts/dump_templates_rules.py from the frontend's "
                                         "shared/templates. Do not edit.", **result["data"]},
                               ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    vectors = {"about": "Recorded from the frontend's shared/templates by scripts/dump_templates_rules.py. Do not edit.",
               **result["vectors"]}
    OUT.write_text(json.dumps(vectors, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {DATA.relative_to(ROOT)} ({len(result['data']['templates'])} templates) and "
          f"{OUT.relative_to(ROOT)} ({len(vectors['fingerprints'])} fingerprints)")


if __name__ == "__main__":
    main()
