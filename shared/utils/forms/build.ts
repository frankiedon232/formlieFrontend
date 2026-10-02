/**
 * Helpers for building FormSchema v1 documents — shared by the builder and the API mock:
 * ids, blank and starter-template schemas, field keys, and the checks that must pass before
 * a form can be published.
 */
import type { StarterTemplateKey } from '../templates/starters'
import { hasOptions, isInputField, type FieldType } from './fields'
import type { FormSchemaV1 } from './schema'

export type FormField = FormSchemaV1['pages'][number]['rows'][number]['fields'][number]
export type FormRow = FormSchemaV1['pages'][number]['rows'][number]
export type FormPage = FormSchemaV1['pages'][number]

const ID_ALPHABET = 'abcdefghijklmnopqrstuvwxyz0123456789'
export function newId(prefix: 'pg' | 'row' | 'fld' | 'rule'): string {
  const bytes = crypto.getRandomValues(new Uint8Array(10))
  return `${prefix}_${Array.from(bytes, b => ID_ALPHABET[b % ID_ALPHABET.length]).join('')}`
}

/** `Full name` → `full_name`, unique among `taken` (`email`, `email_2`, …). */
export function keyFromLabel(label: string, taken: Iterable<string>): string {
  const used = new Set(taken)
  const base =
    label
      .toLowerCase()
      .normalize('NFKD')
      .replace(/[̀-ͯ]/g, '')
      .replace(/[^a-z0-9]+/g, '_')
      .replace(/^_+|_+$/g, '')
      .replace(/^(\d)/, 'f_$1')
      .slice(0, 48) || 'field'
  if (!used.has(base)) return base
  let n = 2
  while (used.has(`${base}_${n}`)) n++
  return `${base}_${n}`
}

export const allFields = (schema: FormSchemaV1): FormField[] =>
  schema.pages.flatMap(page => page.rows.flatMap(row => row.fields))

export function blankSchema(title = 'Page 1'): FormSchemaV1 {
  return {
    schema_version: 1,
    settings: { progress_bar: true, save_resume: false, language: 'en' },
    pages: [{ id: newId('pg'), title, rows: [] }],
    logic: [],
    calculations: [],
    thank_you: { title: 'Thank you!', message: 'Your response has been recorded.', redirect_url: null },
  }
}

type Seed = [FieldType, string, Partial<FormField>?]

function field([type, label, extra]: Seed, taken: Set<string>): FormField {
  const key = keyFromLabel(label, taken)
  taken.add(key)
  return {
    id: newId('fld'),
    key,
    type,
    label,
    width: 12,
    required: false,
    ...(hasOptions(type) && !extra?.options ? { options: options('Option 1', 'Option 2', 'Option 3') } : {}),
    ...extra,
  }
}

const options = (...labels: string[]) =>
  labels.map(label => ({ value: label.toLowerCase().replace(/[^a-z0-9]+/g, '_'), label }))

/** One field per row unless a row lists several (they share the 12-column grid). */
function pages(...defs: { title: string; rows: (Seed | Seed[])[] }[]): FormSchemaV1['pages'] {
  const taken = new Set<string>()
  return defs.map(def => ({
    id: newId('pg'),
    title: def.title,
    rows: def.rows.map(row => {
      const seeds = (Array.isArray(row[0]) ? row : [row]) as Seed[]
      const width = Math.floor(12 / seeds.length)
      return { id: newId('row'), fields: seeds.map(seed => ({ ...field(seed, taken), width })) }
    }),
  }))
}

const STARTERS: Record<StarterTemplateKey, () => FormSchemaV1['pages']> = {
  customer_feedback: () =>
    pages({
      title: 'Your feedback',
      rows: [
        [
          'scale',
          'How likely are you to recommend us to a friend?',
          { required: true, props: { min: 0, max: 10 } },
        ],
        ['rating', 'How satisfied are you overall?', { required: true, props: { max: 5 } }],
        [
          'radio',
          'What did you mainly use?',
          { options: options('Website', 'Mobile app', 'Customer support', 'In person') },
        ],
        ['long_text', 'What could we do better?'],
        [
          ['short_text', 'Name'],
          ['email', 'Email'],
        ],
        ['toggle', 'You may contact me about my feedback'],
      ],
    }),
  event_registration: () =>
    pages(
      {
        title: 'Your details',
        rows: [
          [
            ['short_text', 'First name', { required: true }],
            ['short_text', 'Last name', { required: true }],
          ],
          [
            ['email', 'Email', { required: true }],
            ['phone', 'Phone'],
          ],
          ['short_text', 'Organisation'],
        ],
      },
      {
        title: 'Your attendance',
        rows: [
          [
            'radio',
            'Ticket type',
            { required: true, options: options('Standard', 'Student', 'Speaker', 'Sponsor') },
          ],
          [
            'checkbox',
            'Sessions you plan to attend',
            { options: options('Opening keynote', 'Workshops', 'Panel', 'Networking') },
          ],
          [
            'dropdown',
            'Dietary requirements',
            { options: options('None', 'Vegetarian', 'Vegan', 'Halal', 'Kosher', 'Gluten-free') },
          ],
          ['long_text', 'Accessibility needs'],
        ],
      },
    ),
  job_application: () =>
    pages(
      {
        title: 'About you',
        rows: [
          [
            ['short_text', 'Full name', { required: true }],
            ['email', 'Email', { required: true }],
          ],
          [
            ['phone', 'Phone'],
            ['country', 'Country of residence'],
          ],
          ['url', 'LinkedIn or portfolio'],
        ],
      },
      {
        title: 'Your application',
        rows: [
          [
            'dropdown',
            'Position',
            {
              required: true,
              options: options('Operations', 'Engineering', 'Design', 'Sales', 'Customer success'),
            },
          ],
          ['date', 'Earliest start date'],
          ['file_upload', 'CV / résumé', { required: true }],
          ['long_text', 'Why would you like to join us?'],
          [
            'checkbox',
            'Consent',
            { required: true, options: options('I agree that my data is processed for this application') },
          ],
        ],
      },
    ),
  employee_onboarding: () =>
    pages(
      {
        title: 'Personal details',
        rows: [
          [
            ['short_text', 'Legal first name', { required: true }],
            ['short_text', 'Legal last name', { required: true }],
          ],
          [
            ['date', 'Date of birth'],
            ['phone', 'Mobile number'],
          ],
          ['address', 'Home address'],
        ],
      },
      {
        title: 'Work set-up',
        rows: [
          [
            ['date', 'Start date', { required: true }],
            [
              'dropdown',
              'Team',
              { options: options('Operations', 'Finance', 'People', 'Technology', 'Sales') },
            ],
          ],
          ['radio', 'Laptop', { options: options('Windows', 'macOS', 'No preference') }],
          ['short_text', 'Emergency contact name'],
          ['phone', 'Emergency contact phone'],
          ['image_upload', 'Photo for your ID badge'],
          ['signature', 'Signature', { required: true }],
        ],
      },
    ),
  contact_lead: () =>
    pages({
      title: 'Contact us',
      rows: [
        [
          ['short_text', 'Name', { required: true }],
          ['email', 'Email', { required: true }],
        ],
        ['short_text', 'Company'],
        ['dropdown', 'Topic', { options: options('Sales', 'Partnership', 'Support', 'Press', 'Other') }],
        ['long_text', 'Message', { required: true }],
        ['hidden', 'Source'],
      ],
    }),
  incident_report: () =>
    pages(
      {
        title: 'What happened',
        rows: [
          [
            ['datetime', 'When did it happen?', { required: true }],
            ['short_text', 'Where did it happen?', { required: true }],
          ],
          ['radio', 'Severity', { required: true, options: options('Low', 'Medium', 'High', 'Critical') }],
          ['long_text', 'Describe what happened', { required: true }],
          ['image_upload', 'Photos'],
        ],
      },
      {
        title: 'People involved',
        rows: [
          ['toggle', 'Was anyone injured?'],
          ['long_text', 'Names of people involved or witnesses'],
          [
            ['short_text', 'Reported by', { required: true }],
            ['email', 'Your email'],
          ],
        ],
      },
    ),
}

export function starterSchema(key: StarterTemplateKey): FormSchemaV1 {
  return { ...blankSchema(), pages: STARTERS[key]() }
}

// ── Publish checks ──────────────────────────────────────────────────────────────────

export type PublishIssueCode = 'no_inputs' | 'empty_label' | 'duplicate_key' | 'no_options'

export interface PublishIssue {
  code: PublishIssueCode
  field_id: string | null
}

/** Everything that blocks publishing (an empty list = ready). */
export function publishIssues(schema: FormSchemaV1): PublishIssue[] {
  const fields = allFields(schema)
  const issues: PublishIssue[] = []
  if (!fields.some(f => isInputField(f.type))) issues.push({ code: 'no_inputs', field_id: null })
  const seen = new Map<string, number>()
  for (const f of fields) seen.set(f.key, (seen.get(f.key) ?? 0) + 1)
  for (const f of fields) {
    if (isInputField(f.type) && !f.label.trim()) issues.push({ code: 'empty_label', field_id: f.id })
    if ((seen.get(f.key) ?? 0) > 1) issues.push({ code: 'duplicate_key', field_id: f.id })
    if (hasOptions(f.type) && !f.option_set_id && !(f.options?.length ?? 0))
      issues.push({ code: 'no_options', field_id: f.id })
  }
  return issues
}
