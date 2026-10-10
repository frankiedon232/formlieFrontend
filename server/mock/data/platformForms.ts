/**
 * Formalie's own forms (owner 2026-10-10, shared/utils/platform/forms.ts): Contact support and the Enterprise
 * enquiry are published forms of Formalie's workspace, built like any customer's form and filled in through the
 * same public renderer (in the app's browser window). Their responses are what the Formalie team reads in the
 * platform admin. Created once, then kept as they are (the Formalie team edits them like any form).
 */
import type { FormSchemaV1 } from '#shared/utils/forms/schema'
import { PLATFORM_FORMS } from '#shared/utils/platform/forms'
import { HELP_CATEGORIES } from '#shared/types/help'
import { formsOf, saveForms, type StoredForm } from './formStore'
import { MOCK_TENANTS, PLATFORM_TENANT_ID } from './tenants'

type Field = FormSchemaV1['pages'][number]['rows'][number]['fields'][number]
const opt = (value: string, label: string) => ({ value, label })
let n = 0
const f = (type: string, key: string, label: string, extra: Partial<Field> = {}): Field => ({ id: `fld_${key}`, key, type, label, width: 12, required: false, ...extra }) as Field
const row = (...fields: Field[]) => ({ id: `row_${++n}`, fields: fields.map(field => ({ ...field, width: Math.floor(12 / fields.length) })) })
/** Filled in by the app through the address (hidden from people, kept with the response). */
const hidden = (key: string, label: string) => f('hidden', key, label)
const AREA_LABELS: Record<string, string> = { start: 'Getting started', forms: 'Forms', builder: 'Form builder', design: 'Design and themes', templates: 'Templates', sharing: 'Sharing', responses: 'Responses', analytics: 'Analytics', lists: 'Lists', data: 'Data sources', api: 'API service', people: 'People and roles', settings: 'Settings', audit: 'Audit trail', ai: 'AI assistant' }

function supportSchema(): FormSchemaV1 {
  return {
    schema_version: 1,
    settings: { progress_bar: false, save_resume: false, language: 'en', title: 'Contact support', field_icons: true, label_position: 'top' },
    pages: [
      {
        id: 'pg_support',
        title: 'How can we help?',
        rows: [
          row(
            f('dropdown', 'topic', 'What is it about?', { required: true, options: [opt('question', 'A question'), opt('problem', "Something isn't working"), opt('billing', 'Plans and billing'), opt('account', 'Account and sign-in'), opt('idea', 'An idea or a request'), opt('other', 'Something else')], props: { url_prefill: true } }),
            f('dropdown', 'area', 'Part of Formalie', { options: HELP_CATEGORIES.map(key => opt(key, AREA_LABELS[key] ?? key)), props: { url_prefill: true } }),
          ),
          row(f('short_text', 'subject', 'Subject', { required: true, placeholder: 'In a few words', props: { url_prefill: true } })),
          row(f('long_text', 'message', 'Message', { required: true, help: 'What you did, what you expected and what happened. The more we know, the faster we can help.', props: { rows: 6 } })),
          row(f('toggle', 'urgent', 'Urgent: something is broken for the whole team right now')),
          row(f('full_name', 'name', 'Your name', { props: { url_prefill: true } }), f('email', 'email', 'Reply to', { required: true, props: { url_prefill: true } })),
          row(hidden('workspace', 'Workspace'), hidden('page', 'Page'), hidden('article', 'Help article'), hidden('plan', 'Plan')),
        ],
      },
    ],
    logic: [],
    calculations: [],
    thank_you: { title: 'Sent to support', message: 'Thank you. The Formalie team will reply by email, usually within one business day.', redirect_url: null },
  } as FormSchemaV1
}

function enterpriseSchema(): FormSchemaV1 {
  return {
    schema_version: 1,
    settings: { progress_bar: true, save_resume: false, language: 'en', title: 'Enterprise enquiry', field_icons: true, label_position: 'top' },
    pages: [
      {
        id: 'pg_about',
        title: 'About you',
        rows: [
          row(f('short_text', 'company', 'Company', { required: true, props: { url_prefill: true } }), f('short_text', 'job_title', 'Job title')),
          row(f('full_name', 'name', 'Your name', { required: true, props: { url_prefill: true } }), f('email', 'email', 'Work email', { required: true, props: { url_prefill: true } })),
          row(f('phone', 'phone', 'Phone'), f('country', 'country', 'Country')),
        ],
      },
      {
        id: 'pg_needs',
        title: 'What you need',
        rows: [
          row(
            f('dropdown', 'size', 'Company size', { required: true, options: [opt('1-50', '1 to 50 people'), opt('51-200', '51 to 200 people'), opt('201-1000', '201 to 1,000 people'), opt('1001-5000', '1,001 to 5,000 people'), opt('5000+', 'More than 5,000 people')] }),
            f('dropdown', 'volume', 'Responses a month', { required: true, options: [opt('under_100k', 'Under 100,000'), opt('100k_1m', '100,000 to 1 million'), opt('1m_10m', '1 to 10 million'), opt('over_10m', 'More than 10 million')] }),
          ),
          row(f('checkbox', 'needs', 'What do you need?', { options: [opt('sso', 'Single sign-on'), opt('dedicated', 'Dedicated infrastructure'), opt('residency', 'Data in a specific region'), opt('sla', 'Uptime agreement (SLA)'), opt('security', 'Security and compliance review'), opt('invoice', 'Pay by invoice'), opt('onboarding', 'Onboarding and training'), opt('custom_limits', 'Custom limits')] })),
          row(f('short_text', 'residency', 'Where should the data stay?', { help: 'A country or region, for example the European Union.' }), f('dropdown', 'start', 'When would you start?', { options: [opt('now', 'Right away'), opt('quarter', 'This quarter'), opt('later', 'Later this year')] })),
          row(f('long_text', 'message', 'Anything else we should know?', { required: true, help: 'Your use, formats, integrations or security requirements.', props: { rows: 5 } })),
          row(hidden('workspace', 'Workspace'), hidden('plan', 'Current plan')),
        ],
      },
    ],
    logic: [],
    calculations: [],
    thank_you: { title: 'Thank you, we have it', message: 'The Formalie team will reply within one business day to prepare your Enterprise offer.', redirect_url: null },
  } as FormSchemaV1
}

const PLATFORM: { key: string; id: string; name: string; schema: () => FormSchemaV1 }[] = [
  { key: PLATFORM_FORMS.support, id: 'f0f0f0f0-0001-4000-8000-00000000c0de', name: 'Contact support', schema: supportSchema },
  { key: PLATFORM_FORMS.enterprise, id: 'f0f0f0f0-0002-4000-8000-00000000c0de', name: 'Enterprise enquiry', schema: enterpriseSchema },
]

/** Makes sure Formalie's workspace has its forms (once; afterwards they are edited like any form). */
export function ensurePlatformForms() {
  const tenant = MOCK_TENANTS.find(item => item.id === PLATFORM_TENANT_ID)
  if (!tenant) return
  const store = formsOf(tenant)
  let added = false
  for (const item of PLATFORM) {
    if (store.forms.some(form => form.public_key === item.key)) continue
    const schema = item.schema()
    const now = new Date().toISOString()
    const form = {
      id: item.id,
      name: item.name,
      slug: item.name.toLowerCase().replace(/[^a-z0-9]+/g, '-'),
      public_key: item.key,
      opens_at: null,
      closes_at: null,
      custom_link: null,
      access: 'public',
      response_limit: null,
      short_code: null,
      status: 'published',
      has_unpublished_changes: false,
      folder: null,
      owner: { id: 'formalie', name: 'Formalie' },
      tags: ['formalie'],
      responses_count: 0,
      completion_rate: 0,
      created_at: now,
      updated_at: now,
      row_version: 1,
      deleted_at: null,
      previous_status: null,
      schema,
      published_schema: structuredClone(schema),
      template_key: null,
      channels: ['link', 'embed'],
    } as unknown as StoredForm
    store.forms.unshift(form)
    added = true
  }
  if (added) saveForms()
}
