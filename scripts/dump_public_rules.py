"""Records the frontend's public-page rules (B7) into tests/vectors/public_rules.json: identity (who already
responded), translations of forms, long-list lookups, file types, the resolved theme and the answers'
fingerprint (shared/utils/forms/identity.ts, translations.ts, options.ts, file-types.ts, theme.ts, and the
mock's fingerprintOf).

    fmly\\Scripts\\python.exe scripts\\dump_public_rules.py [path\\to\\formalieFrontend]

tests/parity/test_public_rules.py holds the port (app/modules/public/rules.py, design/theme.py) to these answers.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dump_frontend_rules import ROOT, run_in_node  # noqa: E402

OUT = ROOT / "tests" / "vectors" / "public_rules.json"

ENTRY = r"""
import { createHash } from 'node:crypto'
import { SYSTEM_TEMPLATES, templateSchema } from '__SHARED__/templates/index.ts'
import { buildSchema } from '__SHARED__/templates/kit.ts'
import * as I from '__SHARED__/utils/forms/identity.ts'
import { walkTexts, translateSchema, formLanguages, mainLanguage } from '__SHARED__/utils/forms/translations.ts'
import { lookupOptions, servedRemotely } from '__SHARED__/utils/forms/options.ts'
import * as F from '__SHARED__/utils/forms/file-types.ts'
import { resolveTheme, defaultTheme } from '__SHARED__/utils/forms/theme.ts'
import { allFields } from '__SHARED__/utils/forms/build.ts'

const clone = v => JSON.parse(JSON.stringify(v))
const schemas = SYSTEM_TEMPLATES.map(def => ({ key: def.key, schema: buildSchema(def) }))

// Identity
const identities = schemas.map(({ key, schema }) => ({ key, identity: I.identityOf(schema) }))
const storedIdentity = [{ email: 'email', verify: true }, { email: 'nope', verify: true }, { email: null, verify: true }]
const emails = ['Sa.rah+news@GoogleMail.com', ' ANA@Example.org ', 'no-at', '', null, 42, '@x.org', 'a@', 'a@b@c', 'jo.hn@gmail.com', 'ü@ü.de']
const names = ['Ana Silva', 'Silva, Ana', 'ANA SÍLVA', '', null, { first: 'Ana', last: 'Silva' }, ['x'], 'Ana-Maria  da Silva', 'Ñoño 3', 'Zoë']
const pairs = [['Ana Silva', 'Ana Sylva'], ['Ana Silva', 'Bob Smith'], ['', 'x'], ['Jon', 'John'], ['abc', 'bca']]
const distance = [['kitten', 'sitting'], ['ab', 'ba'], ['', 'abc'], ['sarah', 'sarha'], ['gmail.com', 'gmial.com']]
const identityForm = { settings: { identity: { email: 'email', verify: false } }, pages: [{ id: 'p', rows: [{ id: 'r', fields: [
  { id: 'a', key: 'email', type: 'email', label: 'Your email' }, { id: 'b', key: 'first_name', type: 'short_text', label: 'First name' },
  { id: 'c', key: 'last_name', type: 'short_text', label: 'Last name' }, { id: 'd', key: 'manager_name', type: 'short_text', label: 'Manager name' }] }] }] }
const earlier = [
  { id: 'r1', submitted_at: '2026-10-01T10:00:00.000Z', data: { email: 'sarah.jones@example.org', first_name: 'Sarah', last_name: 'Jones' } },
  { id: 'r2', submitted_at: '2026-10-02T10:00:00.000Z', data: { email: 'mike@example.org', first_name: 'Mike', last_name: 'Brown' } },
]
const matches = [
  { email: 'Sarah.Jones@example.org' }, { email: 'sarah.jone@example.org', first_name: 'Sarah', last_name: 'Jones' },
  { email: 'sarah.jone@example.org', first_name: 'Paul', last_name: 'Green' }, { email: 'mike@exampel.org' }, { email: 'mik@example.org', first_name: 'Mik' },
  { email: 'new@example.org' }, {}, { email: 'not email' },
].map(answers => ({ answers, result: (m => ({ level: m.level, reason: m.reason ?? null, record: m.record?.id ?? null }))(I.matchIdentity(identityForm, answers, earlier)) }))

// Translations: half the texts translated, the form offering fr and de
const translations = schemas.slice(0, 30).map(({ key, schema }, n) => {
  const s = clone(schema)
  const saved = {}
  let i = 0
  walkTexts(clone(s), (k, text) => { if (i++ % 2 === n % 2) saved[k] = n % 3 ? `  [fr] ${text}  ` : ' '; return text })
  s.settings = { ...s.settings, language: n % 5 === 0 ? 'xx' : 'en', languages: ['fr', 'de', 'en', 'fr', 'zz'], ...(n % 4 === 0 ? { title: undefined } : {}) }
  if (n % 4 === 0) { delete s.settings.title; saved['form.title'] = '  Titre  ' }
  s.translations = { fr: saved }
  return { key, schema: s, languages: formLanguages(s), main: mainLanguage(s), fr: translateSchema(s, 'fr'), de: translateSchema(s, 'de'), en: translateSchema(s, 'en') }
})

// Long lists
const cities = ['São Paulo', 'Santos', 'Sao Luis', 'Nairobi', 'Paris', 'Saint-Denis', 'Osaka', 'Sakai', 'Toronto', 'Montréal']
const options = cities.flatMap((label, i) => [{ value: `c${i}`, label, parent: i < 3 ? 'br' : 'other', ...(i % 2 ? { attrs: { pop: i } } : {}) }])
const many = Array.from({ length: 120 }, (_, i) => ({ value: `v${i}`, label: `Item ${i}` }))
const lookups = [
  { q: 'sao' }, { q: '  SA ' }, { q: '' }, { q: 'zzz' }, { values: ['c0', 'c9', 'nope'] }, { parents: ['br'] }, { parents: ['br'], q: 'san' }, { parents: [] }, { q: 'x'.repeat(150) },
].map(query => ({ query, result: lookupOptions(options, query) }))
const manyLookups = [{ q: 'item 1' }, { q: '' }].map(query => ({ query, result: lookupOptions(many, query) }))
const remote = [
  { type: 'dropdown', options: many }, { type: 'radio', options: many.slice(0, 21) }, { type: 'radio', options: many.slice(0, 20) }, { type: 'dropdown', options: many, option_parent: 'x' },
  { type: 'dropdown', options: [], options_large: { total: 5 } }, { type: 'short_text', options: many }, { type: 'checkbox', options: many },
].map(field => ({ field: { ...field, options: field.options.length }, many: field.options === many, result: servedRemotely(field) }))

// File types
const accepts = ['', 'image/*,.pdf', '.PDF, docx ,*.txt', 'application/pdf', 'video/*', 'image/png,image/svg+xml,.svg', 'nonsense!!,.toolongextension123456', 'audio/*,.mp3']
const files = [['a.pdf', 'application/pdf'], ['photo.HEIC', ''], ['photo.heic', 'application/octet-stream'], ['x.png', 'image/png'], ['x.svg', 'image/svg+xml'],
  ['clip.mov', 'video/quicktime'], ['clip.mov', ''], ['song.mp3', 'audio/mpeg'], ['notes.txt', 'text/plain'], ['doc.docx', 'application/vnd.openxmlformats'], ['noext', ''], ['run.exe', 'application/x-msdownload']]
const fileCases = accepts.flatMap(accept => files.map(([name, type]) => ({ accept, name, type, accepts: F.acceptsFile(accept, { name, type }) })))
const pictures = accepts.map(accept => ({ accept, picture: F.pictureAccept(accept), parsed: F.parseAccept(accept), non: F.nonPictureTypes(accept) }))
const looks = files.map(([name, type]) => ({ name, type, picture: F.looksLikePicture({ name, type }) }))

// Themes
const brandings = [{ logo_url: null, primary: null }, { logo_url: '/api/v1/files/AbCdEfGhIjKlMnOpQrStUvWxYz0', primary: '#0055FF' }]
const base = defaultTheme(brandings[0])
const stored = [null, {}, 'text', templateSchema(SYSTEM_TEMPLATES[3], brandings[1]).theme, { layout: 'split', split: { panel: 'color', bg: '#112233' }, header: { band: 'none' }, container: { width: 'xl' } },
  { layout: 'split', split: { panel: 'image' }, container: { width: 'md' } }, { colors: { primary: 'red' }, typography: { font: 'lora' } }, { page: { bg: 'nope' }, frame: { style: 'floating' } },
  { ...clone(base), layout: 'grid' }, { extra: 1, colors: { primary: '#ABCDEF' } }]
const themes = stored.flatMap(theme => brandings.map((b, i) => ({ stored: theme, branding: i, result: resolveTheme(theme, b) })))

// Fingerprint (server/mock/data/responseStore.ts fingerprintOf)
const fingerprintOf = answers => {
  const stable = Object.keys(answers).sort().map(key => [key, typeof answers[key] === 'string' ? answers[key].trim().toLowerCase() : answers[key]])
  return createHash('sha256').update(JSON.stringify(stable)).digest('hex')
}
const prints = [{}, { b: ' Hello ', a: 1.5, c: [1, 'X'], d: { y: 2, x: null } }, { z: 7, Z: 'é', 'ä': true, n: 1e21 }, { a: 0.1 + 0.2, b: -0, c: 'line\nbreak "q"' }]
  .map(answers => ({ answers, hash: fingerprintOf(answers) }))

process.stdout.write(JSON.stringify({
  about: 'Recorded from the frontend by scripts/dump_public_rules.py. Do not edit.',
  identities, stored_identity: storedIdentity.map(identity => ({ identity, result: I.identityOf({ ...identityForm, settings: { identity } }) })),
  emails: emails.map(value => ({ value, email: I.normaliseEmail(value), mask: I.maskEmail(value) })),
  names: names.map(value => ({ value, name: I.normaliseName(value) })),
  similarity: pairs.map(([a, b]) => ({ a, b, value: I.nameSimilarity(a, b) })),
  distance: distance.map(([a, b]) => ({ a, b, value: I.editDistance(a, b) })),
  matches, translations, lookups, many_lookups: manyLookups, remote, files: fileCases, pictures, looks, themes, brandings, prints,
}))
"""


def main() -> None:
    result = run_in_node(ENTRY, {})
    OUT.write_text(json.dumps(result, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    print(f"Wrote {OUT.relative_to(ROOT)}: {len(result['translations'])} translated forms, {len(result['files'])} file "
          f"checks, {len(result['themes'])} themes")


if __name__ == "__main__":
    main()
