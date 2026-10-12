"""Records the frontend's answers for Settings, the rest (B11) into tests/vectors/settings_more_rules.json:

- the catalogues: EMAIL_VARIABLES (shared/types/emails.ts), SSO_PROVIDERS and SSO_PROTOCOL (shared/types/sso.ts),
  DATA_REGIONS (shared/utils/platform/regions.ts), RETENTION_DAYS (shared/types/privacy.ts);
- the request schemas of the mock's routes (emails.ts, emailSending.ts, sso.ts, address.ts, dataPrivacy.ts), copied
  here word for word because the mock's route files can't be bundled on their own, run over many inputs: accepted
  or not, the cleaned value, and each problem's field and message.

    fmly\\Scripts\\python.exe scripts\\dump_settings_more_rules.py

The frontend is only read. tests/parity/test_settings_more_rules.py holds the backend to these answers.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dump_frontend_rules import ROOT, run_in_node  # noqa: E402

OUT = ROOT / "tests" / "vectors" / "settings_more_rules.json"

ENTRY = r"""
import { z } from '__SHARED__/../node_modules/zod'
import { EMAIL_TEMPLATES, EMAIL_VARIABLES } from '__SHARED__/types/emails.ts'
import { SSO_PROVIDERS, SSO_PROTOCOL } from '__SHARED__/types/sso.ts'
import { DATA_REGIONS } from '__SHARED__/utils/platform/regions.ts'
import { RETENTION_DAYS } from '__SHARED__/types/privacy.ts'
import { emailTextSchema, isEmailDomain } from '__SHARED__/utils/settings/schemas.ts'

// ── Copied from server/mock/routes/*.ts ──
const previewSchema = emailTextSchema.extend({ key: z.enum(EMAIL_TEMPLATES), language: z.string().max(10) })
const addressSchema = z.object({ address: z.string().trim().toLowerCase().max(200).pipe(z.email()) })
const HOST = /^(?=.{1,253}$)([a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)*[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$/
const smtpSchema = z.object({
  host: z.string().trim().toLowerCase().max(253).refine(value => HOST.test(value), 'host'),
  port: z.number().int().min(1).max(65535),
  security: z.enum(['starttls', 'tls', 'none']),
  username: z.string().trim().max(200).nullable().transform(value => value || null),
  password: z.string().max(500).nullable().optional(),
  from_address: z.string().trim().toLowerCase().max(200).pipe(z.email()),
})
const modeSchema = z.object({ mode: z.enum(['formalie', 'domain', 'smtp']) })
const url = z.string().trim().max(500).nullable().transform(value => value || null).refine(value => !value || /^https:\/\/[^\s]+$/i.test(value), 'https')
const text = max => z.string().trim().max(max).nullable().transform(value => value || null)
const ssoSaveSchema = z.object({
  provider: z.enum(SSO_PROVIDERS),
  label: z.string().trim().min(1).max(40),
  saml: z.object({ metadata_url: url, entity_id: text(500), sso_url: url, certificate: text(10_000) }).partial().optional(),
  oidc: z.object({ issuer: url, client_id: text(300), client_secret: z.string().max(1000).nullable().optional() }).optional(),
  domains: z.array(z.string().trim().toLowerCase().transform(value => value.replace(/^@/, '')).refine(isEmailDomain, 'domain')).max(20),
  enforce: z.boolean(),
  auto_create: z.boolean(),
  default_role: z.string().min(1).max(100),
})
const statusSchema = z.object({ active: z.boolean() })
const subdomainSchema = z.object({ subdomain: z.string().trim().toLowerCase().min(3).max(63), confirm: z.string().trim().toLowerCase() })
const domainSchema = z.object({ domain: z.string().trim().toLowerCase().transform(value => value.replace(/^https?:\/\//, '').replace(/\/.*$/, '').replace(/\.$/, '')) })
const emailSchema = z.object({ email: z.email().max(200) })
const deleteSchema = emailSchema.extend({ confirm: z.string().max(200) })

const clone = v => JSON.parse(JSON.stringify(v))
const set = (base, path, value) => {
  const out = clone(base)
  const keys = path.split('.')
  let at = out
  for (const k of keys.slice(0, -1)) at = at[k]
  if (value === '__DELETE__') delete at[keys.at(-1)]
  else at[keys.at(-1)] = value
  return out
}
const run = (schema, input) => {
  const r = schema.safeParse(input)
  return r.success ? { input, ok: true, data: r.data } : { input, ok: false, issues: r.error.issues.map(i => ({ path: i.path.join('.'), message: i.message })) }
}
const variants = (base, list) => [base, ...list.map(([p, v]) => set(base, p, v)), 'nonsense', null, 42, [], {}]

const preview = { key: 'signin_code', language: 'en', subject: 'Your code', body: 'It is {{code}}' }
const smtp = { host: 'smtp.acme.test', port: 587, security: 'starttls', username: 'mailer', password: 'p', from_address: 'team@acme.test' }
const oidc = { provider: 'okta', label: 'Okta', oidc: { issuer: 'https://acme.okta.com', client_id: 'c1', client_secret: 's' },
  domains: ['acme.test'], enforce: false, auto_create: false, default_role: 'member' }

const cases = {
  preview: variants(preview, [['subject', '  '], ['subject', 'x'.repeat(201)], ['body', ''], ['key', 'nope'], ['language', 'x'.repeat(11)],
    ['subject', '  Trimmed  '], ['body', 'x'.repeat(10001)], ['key', '__DELETE__'], ['language', 5]]),
  address: variants({ address: 'forms@acme.test' }, [['address', ' Forms@Acme.TEST '], ['address', 'nope'], ['address', ''],
    ['address', 'a@b'], ['address', `${'x'.repeat(195)}@a.test`], ['address', 7]]),
  smtp: variants(smtp, [['host', 'bad host!'], ['host', ' SMTP.Acme.TEST '], ['host', ''], ['host', '127.0.0.1'], ['host', `${'a'.repeat(64)}.test`],
    ['port', 0], ['port', 70000], ['port', 25.5], ['port', '25'], ['security', 'ssl'], ['security', 'tls'], ['username', ''], ['username', null],
    ['username', '  mailer  '], ['password', '__DELETE__'], ['password', null], ['password', ''], ['password', 'x'.repeat(501)],
    ['from_address', 'nope'], ['from_address', ' A@Acme.TEST '], ['host', '__DELETE__'], ['username', '__DELETE__']]),
  mode: variants({ mode: 'domain' }, [['mode', 'smtp'], ['mode', 'formalie'], ['mode', 'own'], ['mode', null]]),
  sso: variants(oidc, [['provider', 'auth0'], ['label', ' '], ['label', 'x'.repeat(41)], ['label', '  Okta  '],
    ['oidc.issuer', 'http://acme.okta.com'], ['oidc.issuer', ''], ['oidc.issuer', null], ['oidc.client_id', '  '], ['oidc.client_secret', '__DELETE__'],
    ['oidc.client_secret', null], ['oidc', '__DELETE__'], ['domains', ['@Acme.TEST', 'b.test']], ['domains', ['not a domain']], ['domains', []],
    ['domains', Array.from({ length: 21 }, (_, i) => `d${i}.test`)], ['enforce', 'yes'], ['auto_create', null], ['default_role', ''],
    ['default_role', 'x'.repeat(101)], ['saml', { metadata_url: 'https://idp.test/meta' }], ['saml', { metadata_url: 'ftp://idp.test' }],
    ['saml', { entity_id: '  urn:idp  ', sso_url: 'https://idp.test/sso', certificate: '  MIIB  ' }], ['saml', { entity_id: '' }],
    ['saml', {}], ['saml', null], ['domains', '__DELETE__']]),
  status: variants({ active: true }, [['active', false], ['active', 'true'], ['active', null]]),
  subdomain: variants({ subdomain: 'acme', confirm: 'acme' }, [['subdomain', ' ACME '], ['subdomain', 'ab'], ['subdomain', 'x'.repeat(64)],
    ['confirm', ' Acme '], ['confirm', '__DELETE__'], ['subdomain', 5]]),
  domain: variants({ domain: 'forms.acme.test' }, [['domain', ' HTTPS://Forms.Acme.TEST./path?x=1 '], ['domain', 'http://a.b/'], ['domain', ''],
    ['domain', 'forms.acme.test.'], ['domain', null]]),
  email: variants({ email: 'ana@example.org' }, [['email', ' ana@example.org'], ['email', 'nope'], ['email', `${'x'.repeat(195)}@a.test`],
    ['email', 'Ana@Example.ORG'], ['email', '']]),
  delete: variants({ email: 'ana@example.org', confirm: 'ana@example.org' }, [['confirm', 'x'.repeat(201)], ['confirm', '__DELETE__'],
    ['email', 'nope'], ['confirm', 7]]),
}
const schemas = { preview: previewSchema, address: addressSchema, smtp: smtpSchema, mode: modeSchema, sso: ssoSaveSchema,
  status: statusSchema, subdomain: subdomainSchema, domain: domainSchema, email: emailSchema, delete: deleteSchema }

console.log(JSON.stringify({
  email_variables: EMAIL_VARIABLES, sso_providers: SSO_PROVIDERS, sso_protocol: SSO_PROTOCOL, data_regions: DATA_REGIONS,
  retention_days: RETENTION_DAYS,
  schemas: Object.fromEntries(Object.entries(cases).map(([k, list]) => [k, list.map(i => run(schemas[k], i))])),
}))
"""


def main() -> None:
    data = run_in_node(ENTRY)
    data["about"] = "Recorded from the frontend by scripts/dump_settings_more_rules.py. Do not edit."
    OUT.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {OUT.relative_to(ROOT)}: {sum(len(v) for v in data['schemas'].values())} schema cases")


if __name__ == "__main__":
    main()
