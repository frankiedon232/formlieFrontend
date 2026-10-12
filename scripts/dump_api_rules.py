"""Records the frontend's API service rules (B10) into tests/vectors/api_rules.json: token prefixes, previews, status,
scopes, header and Formalie-Key checks, canonical JSON (tokens.ts); allowed websites (origins.ts); access rule values,
IP ranges, matching and decisions (access.ts); choices in and out (choices.ts); endpoint fields, names, examples and
version changes (endpoints.ts), with the label rules they use (forms/build.ts keyFromLabel, forms/label-icons.ts).

    fmly\\Scripts\\python.exe scripts\\dump_api_rules.py [path\\to\\formalieFrontend]

tests/parity/test_api_rules.py holds the port (app/modules/api_service/) to these answers. snippets.ts is not ported:
it only writes code samples for the portal's Docs page, and the server never uses it.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dump_frontend_rules import ROOT, run_in_node  # noqa: E402

OUT = ROOT / "tests" / "vectors" / "api_rules.json"

ENTRY = r"""
import * as T from '__SHARED__/utils/apiService/tokens.ts'
import * as O from '__SHARED__/utils/apiService/origins.ts'
import * as A from '__SHARED__/utils/apiService/access.ts'
import * as C from '__SHARED__/utils/apiService/choices.ts'
import * as E from '__SHARED__/utils/apiService/endpoints.ts'
import { keyFromLabel } from '__SHARED__/utils/forms/build.ts'
import { iconFromLabel } from '__SHARED__/utils/forms/label-icons.ts'

const safe = fn => { try { return { value: fn() } } catch (e) { return { error: true } } }
const big = v => JSON.parse(JSON.stringify(v, (k, x) => (typeof x === 'bigint' ? x.toString() : x)))

// ── tokens ──
const kinds = ['static', 'client', 'client_id', 'signing', 'webhook', 'access']
const prefixes = kinds.flatMap(kind => ['live', 'test'].map(mode => ({ kind, mode, prefix: T.tokenPrefix(kind, mode) })))
const secrets = ['formalie_live_abcDEF123456', 'formalie_test_x', 'formalie_secret_live_ABCDEFGHJK', 'formalie_client_test_1234',
  'formalie_hook_live_Zz99', 'nope_live_abcd', 'abc', '', 'formalie_LIVE_abcdefg', 'formalie_access_test_qwerty']
const previews = secrets.map(secret => ({ secret, preview: T.secretPreview(secret) }))
const masks = ['', 'a', 'abcd', 'abcde', 'secret-value-1234'].map(value => ({ value, masked: T.maskValue(value) }))
const NOW = '2026-10-12T12:00:00.000Z'
const nowMs = Date.parse(NOW)
const expiries = [null, '2026-10-12T11:59:59.000Z', NOW, '2026-10-12T12:00:00.001Z', '2026-10-26T12:00:00.000Z', '2026-10-26T12:00:00.001Z', '2027-01-01T00:00:00.000Z']
const statuses = [null, '2026-10-01T00:00:00.000Z'].flatMap(revoked_at => expiries.map(expires_at => ({ revoked_at, expires_at, now: NOW, status: T.tokenStatusOf({ revoked_at, expires_at }, nowMs) })))
const scopeSets = [{ services: [], endpoints: [], methods: [] }, { services: ['s1'], endpoints: [], methods: [] }, { services: [], endpoints: ['e1'], methods: ['GET'] },
  { services: ['s2'], endpoints: ['e1'], methods: [] }, { services: ['s1', 's2'], endpoints: ['e2'], methods: ['POST', 'PUT'] }]
const targets = [{ endpoint_id: 'e1', service_id: 's1' }, { endpoint_id: 'e2', service_id: 's2' }, { endpoint_id: 'e3', service_id: 's1' }]
const scopes = scopeSets.flatMap(s => targets.flatMap(t => ['GET', 'POST', 'PUT', 'DELETE'].map(method => ({ scopes: s, target: { ...t, method }, allows: T.scopeAllows(s, { ...t, method }), reach: T.tokenReach(s, { id: t.endpoint_id, service_id: t.service_id }) }))))
const headerNames = ['', 'X', 'X-Api', 'x-tenant', 'Authorization', 'content-type', 'Formalie-Thing', 'X-Formalie-Sig', '1abc', 'A_b', 'Ab' + 'c'.repeat(62), 'Ab' + 'c'.repeat(63), 'Origin', 'X-Custom-Header']
  .map(name => ({ name, problem: T.checkHeaderName(name) }))
const headerValues = ['', ' x', 'x ', 'value', 'a\tb', 'héllo', 'x'.repeat(200), 'x'.repeat(201), '~!@#$%^&*()']
  .map(value => ({ value, problem: T.checkHeaderValue(value) }))
const callKeys = ['', 'short', '3f2504e0-4f89-11d3-9a0c-0305e82c3301', '1111111111111111', 'abababababababab', '1234567890123456', 'abcdefghijklmnop',
  'zyxwvutsrqponmlk', 'order-2026-10-12-0001', 'has space in it ok', 'x'.repeat(101), 'a.b_c:d-e.f_g:h-i', 'Xb7QmV2kP0aZr9Lw', 'aaaabbbbccccdddd', 'aabbccddeeffgghh', 'ABCDEFGHIJKLMNOPQ', 'é'.repeat(20)]
  .map(key => ({ key, problem: T.checkCallKey(key) }))
const canon = [null, true, false, 0, 1, -1, 1.5, 1e21, 1e-7, 0.000001, 123456789.125, 'text', 'é"\\\n\t', [], {}, [1, 'a', null], { b: 1, a: [2, { d: 4, c: 3 }] }, { 'Z': 1, 'a': 2, '_': 3, '10': 4, '9': 5 }]
  .map(value => ({ value, json: T.canonicalJson(value) }))

// ── origins ──
const originInputs = ['https://shop.example.com', 'shop.example.com', 'HTTPS://Shop.Example.com/', 'https://shop.example.com///', 'http://shop.example.com', 'http://localhost:3000',
  'localhost:3000', 'http://127.0.0.1:8080', 'http://app.localhost', 'https://example.com:443', 'https://example.com:8443', 'https://example.com:0443', 'https://example.com:99999',
  'https://example.com/path', 'https://example.com?x=1', 'https://example.com#top', 'https://example.com?', 'https://example.com/?', 'https://example.com/.', 'https://user@example.com',
  'https://user:pw@example.com', 'ftp://example.com', 'https://', '', '   ', 'https://exa mple.com', 'example', 'https://example', 'https://exa_mple.com', 'https://-x.example.com',
  'https://bücher.example', 'https://[::1]', 'https://10.0.0.1', 'https://example.com:', 'https:///example.com', 'https:example.com', 'https://example.com\\path', '  https://example.com  ',
  'https://a.b.c.d.example.co.uk', 'wss://example.com', 'https://example.com.']
const origins = originInputs.map(value => ({ value, origin: safe(() => O.normaliseOrigin(value)).value ?? null }))
const allowedLists = [[], ['https://shop.example.com'], ['https://shop.example.com', 'http://localhost:3000']]
const originAllowed = [null, '', 'https://shop.example.com', 'shop.example.com/', 'http://localhost:3000', 'https://other.example.com', 'nonsense value']
  .flatMap(origin => allowedLists.map(allowed => ({ origin, allowed, ok: O.originAllowed(origin, allowed) })))

// ── access ──
const ruleValues = {
  ip: ['192.0.2.1', ' 192.0.2.1 ', '192.0.2.0/24', '192.0.2.0/33', '192.0.2.0/', '256.1.1.1', '1.2.3', '2001:db8::1', '2001:db8::/32', '::1', '::', '::ffff:192.0.2.1', '2001:db8::1::2',
    '1:2:3:4:5:6:7:8', '1:2:3:4:5:6:7', 'gggg::1', '2001:db8::/129', '10.0.0.0/8/9', '', '  ', '01.02.03.004', '1.2.3.4/0', 'fe80::1%eth0', '2001:DB8::ABCD'],
  domain: ['example.com', '*.example.com', 'EXAMPLE.com', 'localhost', '*.com', 'ex_ample.com', 'a.b', '-a.com', 'a-.com', 'xn--bcher-kva.example', ' example.com ', '*.*.example.com', 'x'.repeat(64) + '.com'],
  country: ['GB', 'gb', 'XX', 'UK', 'us', ' fr ', 'G'],
  region: ['EU', 'eu', 'AF', 'XX', 'NA', 'Europe'],
  network: ['vpn', 'VPN', 'tor', 'proxy', 'hosting', 'cloud', ''],
}
const valueChecks = Object.entries(ruleValues).flatMap(([kind, list]) => list.map(value => ({ kind, value, problem: A.checkRuleValue(kind, value), normal: A.normaliseRuleValue(kind, value) })))
const regions = ['GB', 'gb', 'US', 'BR', 'JP', 'AU', 'ZA', 'XX', null, ''].map(country => ({ country, region: A.regionOf(country) }))
const cidrs = ruleValues.ip.map(text => ({ text, cidr: big(A.parseCidr(text)) }))
const ipPairs = [['192.0.2.5', '192.0.2.0/24'], ['192.0.3.5', '192.0.2.0/24'], ['192.0.2.5', '192.0.2.5'], ['192.0.2.5', '0.0.0.0/0'], ['2001:db8::5', '2001:db8::/32'],
  ['2001:db9::5', '2001:db8::/32'], ['::ffff:192.0.2.5', '192.0.2.0/24'], ['192.0.2.5', '::/0'], ['bad', '192.0.2.0/24'], ['192.0.2.5', 'bad'], ['10.1.2.3', '10.0.0.0/8'], ['198.51.100.7', '198.51.100.0/28'], ['198.51.100.17', '198.51.100.0/28']]
  .map(([ip, cidr]) => ({ ip, cidr, inside: A.ipInCidr(ip, cidr) }))
const callers = [{ ip: '192.0.2.66', domain: null, country: 'GB', networks: [] }, { ip: '203.0.113.9', domain: 'shop.example.com', country: 'US', networks: ['vpn'] },
  { ip: '203.0.113.9', domain: 'example.com', country: 'BR', networks: [] }, { ip: '198.51.100.3', domain: 'x.spam-example.net', country: null, networks: ['tor', 'hosting'] },
  { ip: '2001:db8::1', domain: 'EXAMPLE.COM', country: 'jp' }]
const ruleSets = [
  [],
  [{ id: 'r1', action: 'block', kind: 'ip', values: ['192.0.2.66', '198.51.100.0/28'], enabled: true }],
  [{ id: 'r1', action: 'block', kind: 'ip', values: ['192.0.2.66'], enabled: false }, { id: 'r2', action: 'allow', kind: 'domain', values: ['example.com', '*.example.com'], enabled: true }],
  [{ id: 'r3', action: 'allow', kind: 'country', values: ['GB', 'US'], enabled: true }, { id: 'r4', action: 'block', kind: 'network', values: ['vpn', 'tor'], enabled: true }],
  [{ id: 'r5', action: 'allow', kind: 'region', values: ['SA', 'AS'], enabled: true }, { id: 'r6', action: 'block', kind: 'domain', values: ['*.spam-example.net'], enabled: true }],
  [{ id: 'r7', action: 'allow', kind: 'ip', values: ['2001:db8::/32'], enabled: true }, { id: 'r8', action: 'allow', kind: 'network', values: ['hosting'], enabled: true }],
]
const decisions = ruleSets.flatMap(rules => callers.map(caller => ({ rules, caller, decision: A.decideAccess(rules, caller) })))
const matches = ['ip', 'domain', 'country', 'region', 'network'].flatMap(kind => ['192.0.2.66', 'example.com', '*.example.com', 'GB', 'EU', 'NA', 'vpn', 'BR', 'SA']
  .flatMap(value => callers.map(caller => ({ kind, value, caller, match: A.matchesValue(kind, value, caller) }))))
const scopedRules = [{ id: 'a', scope: { type: 'all', id: null } }, { id: 'b', scope: { type: 'service', id: 's1' } }, { id: 'c', scope: { type: 'endpoint', id: 'e1' } },
  { id: 'd', scope: { type: 'service', id: 's2' } }, { id: 'e', scope: { type: 'endpoint', id: 'e2' } }]
const rulesFor = targets.map(t => ({ endpoint: { id: t.endpoint_id, service_id: t.service_id }, ids: A.rulesFor(scopedRules, { id: t.endpoint_id, service_id: t.service_id }).map(r => r.id) }))

// ── choices ──
const country = { id: 'f_c', key: 'country', options: [{ value: 'br', label: 'Brazil' }, { value: 'pt', label: 'Portugal' }] }
const city = { id: 'f_t', key: 'city', option_parent: 'f_c', options: [{ value: 'sp', label: 'São Paulo', parent: 'br' }, { value: 'campinas', label: 'Campinas', parent: 'br' }, { value: 'lis', label: 'Lisbon', parent: 'pt' }, { value: 'sp_pt', label: 'São Paulo', parent: 'pt' }] }
const skills = { id: 'f_s', key: 'skills', options: [{ value: 'vue', label: 'Vue' }, { value: 'ts', label: 'TypeScript' }] }
const plain = { id: 'f_p', key: 'note' }
const choiceFields = [country, city, skills, plain]
const outCases = [[country, 'br'], [country, 'xx'], [country, null], [country, ['br', 'pt', 'zz']], [skills, ['vue', 3]], [plain, 'free'], [skills, 7], [city, 'sp_pt']]
  .map(([field, value]) => ({ field, value, out: C.choiceOut(field, value) }))
const inCases = [{ country: 'Brazil', city: 'São Paulo' }, { country: 'pt', city: ' são paulo ' }, { country: 'Portugal', city: 'SÃO PAULO' }, { skills: ['typescript', 'vue', 'Go'] },
  { country: null, city: 'Lisbon' }, { note: 'x', skills: 'Vue' }, { city: 'Campinas' }, { country: ['Brazil', 'Portugal'], city: 'São Paulo' }, { country: 5, city: 'Lisbon' }]
  .map(answers => ({ answers, out: C.choicesIn(choiceFields, answers) }))
const filterCases = [[country, 'Brazil'], [country, 'br'], [country, 'nowhere'], [plain, 'x'], [city, 'são paulo']].map(([field, wanted]) => ({ field, wanted, out: C.choiceFilter(field, wanted) }))

// ── endpoints ──
const fld = (key, type, extra = {}) => ({ id: `f_${key}`, key, type, label: key.replace(/_/g, ' '), ...extra })
const opts = (...pairs) => pairs.map(([value, label, parent]) => (parent ? { value, label, parent } : { value, label }))
const schemaA = { schema_version: 1, pages: [
  { id: 'p1', rows: [{ id: 'r1', fields: [fld('full_name', 'short_text', { required: true }), fld('email', 'email'), fld('intro', 'paragraph')] }] },
  { id: 'p2', rows: [{ id: 'r2', fields: [fld('cv', 'file_upload'), fld('total', 'calculated'), fld('reference', 'short_text', { readonly: true }), fld('topic', 'dropdown', { options: opts(['a', 'Alpha'], ['b', 'Beta']) }), fld('locked', 'number', { disabled: true, required: true })] }] },
] }
const schemaB = { schema_version: 1, pages: [{ id: 'p', rows: [
  { id: 'r1', fields: [fld('first_name', 'short_text', { label: 'First name', required: true }), fld('first_name_k3x9', 'short_text', { label: 'First name' }), fld('id', 'short_text', { label: 'ID' }), fld('status', 'short_text', { label: 'Status' })] },
  { id: 'r2', fields: [fld('city', 'dropdown', { label: 'City', option_parent: 'f_country', options: opts(['sp', 'São Paulo', 'br'], ['campinas', 'Campinas', 'br'], ['lis', 'Lisbon', 'pt']) }), fld('country', 'dropdown', { label: 'Country', options: opts(['br', 'Brazil'], ['pt', 'Portugal'], ['fr', 'France']) })] },
  { id: 'r3', fields: [fld('big', 'dropdown', { label: 'Big list', options: Array.from({ length: 30 }, (_, i) => ({ value: `v${i}`, label: `Value ${i}` })), options_large: { total: 5000 } }), fld('empty_large', 'dropdown', { label: 'Huge', options_large: { total: 90000 } })] },
  { id: 'r4', fields: [fld('sig', 'signature', { label: 'Signature', required: true }), fld('pay', 'payment', { label: 'Pay' }), fld('when', 'date', { label: 'Date of birth' }), fld('qty', 'number', { label: 'How many' }), fld('n2', 'number', { label: 'Score' })] },
  { id: 'r5', fields: [fld('nolabel', 'short_text', { label: '' }), fld('1st', 'short_text', { label: '1st choice' }), fld('café', 'short_text', { label: 'Café Crème' }), fld('hidden_x', 'hidden', { label: 'Source' })] },
] }] }
const savedSets = [undefined, [], [
  { key: 'full_name', accept: false, required: false, returned: false, filter: false },
  { key: 'email', name: 'mail', accept: true, required: true, returned: true, filter: true },
  { key: 'cv', accept: true, required: true, returned: false, filter: true },
  { key: 'total', accept: true, required: true, returned: true, filter: false },
  { key: 'topic', name: 'Topic', accept: false, required: true, returned: true, filter: true },
], [
  { key: 'first_name', name: 'given', accept: true, required: true, returned: true, filter: true },
  { key: 'first_name_k3x9', name: 'given', accept: true, required: false, returned: true, filter: false },
  { key: 'id', name: 'record_id', accept: true, required: false, returned: false, filter: false },
  { key: 'city', name: 'town', accept: true, required: true, returned: true, filter: true },
  { key: 'when', accept: false, required: true, returned: true, filter: true },
]]
const fieldCases = [schemaA, schemaB].flatMap(schema => savedSets.map(saved => {
  const fields = E.endpointFieldsOf(schema, saved)
  return { schema, saved: saved ?? null, fields, reasons: fields.map(E.notAcceptedReason), body: E.exampleRequestBody(fields), record: E.exampleRecord(fields), levels: E.withLevelSamples(fields) }
}))
const types = ['short_text', 'long_text', 'rich_text', 'email', 'phone', 'url', 'domain', 'number', 'slider', 'currency', 'percentage', 'full_name', 'date', 'time', 'datetime', 'date_range', 'duration',
  'multi_select', 'checkbox', 'ranking', 'dropdown', 'radio', 'toggle', 'consent', 'rating', 'scale', 'matrix', 'address', 'country', 'language', 'timezone', 'iban', 'bic', 'currency_code',
  'ip_address', 'mac_address', 'color', 'file_upload', 'image_upload', 'signature', 'hidden', 'calculated', 'whatever']
const labels = ['', 'First name', 'Last name', 'Surname', 'Prénom', 'Nombre completo', 'Email address', 'Phone', 'Company name', 'Organisation', 'Job title', 'Street address', 'City', 'Region',
  'Postcode', 'Country', 'Website', 'Date of birth', 'Budget', 'Quantity', 'Age', 'Comments', 'Subject', 'Username', 'Invoice number', 'Passport', 'Your name', 'Product name', 'When?', 'Where',
  'Something else', 'Nationality', 'pin_code', 'E-mail', 'Telefone', 'Straße', 'Geburtsdatum', 'Количество', 'how many guests', 'Total price (EUR)']
const samples = types.flatMap(type => labels.map(label => ({ field: { key: label.toLowerCase().replace(/[^a-z0-9]+/g, '_') || 'field', label, type }, value: E.sampleValue({ key: label.toLowerCase().replace(/[^a-z0-9]+/g, '_') || 'field', label, type }) })))
  .concat([{ field: { key: 'pick', label: 'Pick', type: 'dropdown', options: opts(['x', 'X'], ['y', 'Y']) } }, { field: { key: 'many', label: 'Many', type: 'checkbox', options: opts(['x', 'X'], ['y', 'Y'], ['z', 'Z']) } },
    { field: { key: 'rank', label: 'Rank', type: 'ranking', options: opts(['x', 'X'], ['y', 'Y'], ['z', 'Z']) } }].map(item => ({ ...item, value: E.sampleValue(item.field) })))
const forLabel = labels.map(label => ({ label, value: E.sampleForLabel({ key: 'k', label }) })).concat([{ key: 'first_name', label: '' }, { key: 'zip', label: '' }].map(f => ({ ...f, value: E.sampleForLabel(f) })))
const icons = labels.concat(['Product', 'Delivery address', 'Appointment date', 'Allergies', 'Emergency contact', 'Language', 'Gender', 'Rating', 'Priority', 'Hobby', 'Notes', 'Search', 'Time', 'Date',
  'Name', 'Nom', 'Kind of thing', 'TEL', 'DOB', 'company size', 'Upload your CV', 'Áccént Strasse']).map(label => ({ label, key: null, icon: iconFromLabel(label) }))
  .concat([['', 'email'], [null, 'phone_number'], ['  ', 'company'], ['Zzz', 'city']].map(([label, key]) => ({ label, key, icon: iconFromLabel(label, key) })))
const endpointNames = ['register-account', '', 'ab', 'abc', 'Register', '-start', 'end-', 'double--hyphen', 'token', 'files', 'webhooks', 'a'.repeat(64), 'a'.repeat(65), 'with_underscore', '123', 'a1-b2-c3', 'docs-v2']
  .map(name => ({ name, problem: E.checkEndpointName(name) }))
const nameFrom = ['Register account', '  Café & Résumé 2026! ', 'Quote - Estimate Request', '', '---', 'Ünïcödé Fòrm', 'x'.repeat(70) + ' end', 'a'.repeat(63) + ' b', 'Formulaire d’inscription', '日本語のフォーム']
  .map(text => ({ text, name: E.endpointNameFrom(text) }))
const apiNames = ['first_name', '', '  ', 'First', '1st', '_x', 'id', 'status', 'data', 'a'.repeat(64), 'a'.repeat(65), 'a-b', 'ok_2'].map(name => ({ name, problem: E.checkApiName(name) }))
const keys = ['Full name', 'Email', 'email', '1st choice', '', '   ', 'Café Crème', '日本', 'A'.repeat(60), '__x__', 'Prénom / Nom'].map(label => ({ label, taken: ['email', 'email_2', 'full_name'], key: keyFromLabel(label, ['email', 'email_2', 'full_name']) }))
const live = [{ key: 'a', label: 'A', required: false, type: 'short_text' }, { key: 'b', label: 'B', required: true, type: 'email' }, { key: 'c', label: 'C', required: false, type: 'calculated' }, { key: 'd', label: 'D', required: false, type: 'number' }, { key: 'e', label: 'E', required: false, type: 'section' }]
const drafts = [[], live, [{ key: 'a', label: 'A2', required: true, type: 'short_text' }, { key: 'b', type: 'email', required: true }, { key: 'x', type: 'date' }, { key: 'd', label: 'D', required: true, type: 'number', readonly: true }, { key: '', type: 'short_text' }, { key: 'y', type: 'paragraph' }]]
const changes = drafts.map(draft => ({ live, draft, changes: E.apiChanges(live, draft) }))

process.stdout.write(JSON.stringify({ about: 'Recorded from the frontend by scripts/dump_api_rules.py. Do not edit.',
  tokens: { prefixes, previews, masks, statuses, scopes, headerNames, headerValues, callKeys, canon },
  origins: { origins, originAllowed },
  access: { valueChecks, regions, cidrs, ipPairs, decisions, matches, rulesFor },
  choices: { outCases, inCases, filterCases },
  endpoints: { fieldCases, samples, forLabel, icons, endpointNames, nameFrom, apiNames, keys, changes } }))
"""


def main() -> None:
    result = run_in_node(ENTRY, {})
    OUT.write_text(json.dumps(result, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    counts = {area: sum(len(v) for v in cases.values()) for area, cases in result.items() if isinstance(cases, dict)}
    print(f"Wrote {OUT.relative_to(ROOT)}: " + ", ".join(f"{n} {area}" for area, n in counts.items()))


if __name__ == "__main__":
    main()
