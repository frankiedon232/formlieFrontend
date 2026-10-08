/**
 * Endpoint rules shared by the wizard and the server (F13): which questions an endpoint may
 * accept, filter on and return, the defaults for a new endpoint, the name check and the example
 * request / record shown in the portal and the docs. Values in examples are neutral, made up.
 */
import type { ApiEndpointField } from '#shared/types/apiService'
import { allFields, keyFromLabel, type FormField } from '#shared/utils/forms/build'
import { iconFromLabel } from '#shared/utils/forms/label-icons'
import type { FormSchemaV1 } from '#shared/utils/forms/schema'
import { ENDPOINT_PATTERN } from '#shared/utils/urls/public'
import { choiceOut } from './choices'

/** One question as an endpoint field, with the defaults for a new endpoint. */
export function endpointFieldsOf(schema: FormSchemaV1, saved?: { key: string; name?: string; accept: boolean; required: boolean; returned: boolean; filter: boolean }[]): ApiEndpointField[] {
  const byKey = new Map((saved ?? []).map(item => [item.key, item]))
  // API names: the saved one when it is valid and free, else a clean one from the label (first_name, first_name_2)
  const taken = new Set<string>()
  const pageOf = new Map(schema.pages.flatMap((page, index) => page.rows.flatMap(row => row.fields.map(field => [field.id, index] as const))))
  const keyOfId = new Map(allFields(schema).map(field => [field.id, field.key]))
  return allFields(schema)
    .filter(field => !LAYOUT_TYPES.includes(field.type))
    .map(field => {
      const acceptable = isAcceptable(field)
      const filterable = FILTER_TYPES.includes(field.type)
      const formRequired = !!field.required && acceptable
      const own = byKey.get(field.key)
      const accept = acceptable && (formRequired || (own ? own.accept : true))
      const kept = own?.name && !checkApiName(own.name) && !taken.has(own.name) ? own.name : null
      const name = kept ?? keyFromLabel(field.label?.trim() || field.key, [...taken, ...RESERVED_API_NAMES])
      taken.add(name)
      return {
        key: field.key,
        name,
        label: field.label,
        type: field.type,
        page: pageOf.get(field.id) ?? 0,
        form_required: formRequired,
        acceptable,
        filterable,
        accept,
        required: accept && (formRequired || !!own?.required),
        returned: own ? own.returned : true,
        filter: filterable && !!own?.filter,
        ...(field.options?.length ? { options: field.options.map(option => ({ value: option.value, label: option.label, ...(option.parent ? { parent: option.parent } : {}) })) } : {}),
        ...(field.option_parent && keyOfId.get(field.option_parent) ? { depends_on: keyOfId.get(field.option_parent) } : {}),
      }
    })
}

/** Can be sent through the API: not read-only, disabled, calculated, a signature or a payment (files: upload first, M5). */
export function isAcceptable(field: Pick<FormField, 'type' | 'readonly' | 'disabled'>) {
  return !field.readonly && !field.disabled && !NOT_ACCEPTED_TYPES.includes(field.type)
}

/** Why a field can't be sent, for the hint beside it (null = it can). */
export function notAcceptedReason(field: Pick<ApiEndpointField, 'type' | 'acceptable'>): 'signature' | 'calculated' | 'payment' | 'locked' | null {
  if (field.acceptable) return null
  if (field.type === 'signature') return 'signature'
  if (field.type === 'calculated') return 'calculated'
  if (field.type === 'payment') return 'payment'
  return 'locked'
}

/** Problems with an endpoint name: `required`, `pattern` (lower-case words and hyphens, 3 to 64) or `reserved`. */
export function checkEndpointName(name: string): 'required' | 'pattern' | 'reserved' | null {
  if (!name) return 'required'
  if (!ENDPOINT_PATTERN.test(name) || name.includes('--')) return 'pattern'
  if (RESERVED_ENDPOINT_NAMES.includes(name)) return 'reserved'
  return null
}

/** A suggested endpoint name from a form name (`Register account` → `register-account`). */
export function endpointNameFrom(text: string) {
  return text
    .normalize('NFKD')
    .replace(/[̀-ͯ]/g, '')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .slice(0, 64)
    .replace(/-+$/, '')
}

/** A made-up value of the right shape for a question, for examples. */
export function sampleValue(field: Pick<ApiEndpointField, 'type' | 'key' | 'label' | 'options'>): unknown {
  const key = `${field.key} ${field.label}`.toLowerCase()
  // The form's own answer values (owner, 2026-10-06: no made-up option_1)
  const values = (field.options ?? []).map(option => option.value)
  if (values.length && ['dropdown', 'radio'].includes(field.type)) return values[0]
  if (values.length && ['multi_select', 'checkbox', 'ranking'].includes(field.type)) return field.type === 'ranking' ? values : values.slice(0, 2)
  switch (field.type) {
    case 'email':
      return 'alex.morgan@example.com'
    case 'phone':
      return '+44 7700 900123'
    case 'url':
    case 'domain':
      return field.type === 'url' ? 'https://example.com' : 'example.com'
    case 'number': {
      const fromLabel = sampleForLabel(field)
      return typeof fromLabel === 'number' ? fromLabel : 42
    }
    case 'slider':
      return 42
    case 'currency':
      return 120.5
    case 'percentage':
      return 75
    case 'full_name':
      return { first: 'Alex', last: 'Morgan' }
    case 'date':
      return sampleForLabel(field) === '1990-04-12' ? '1990-04-12' : '2026-10-06'
    case 'time':
      return '09:30'
    case 'datetime':
      return '2026-10-06T09:30:00Z'
    case 'date_range':
      return { from: '2026-10-06', to: '2026-10-10' }
    case 'duration':
      return { hours: 1, minutes: 30 }
    case 'multi_select':
    case 'checkbox':
    case 'ranking':
      return ['option_1', 'option_2']
    case 'dropdown':
    case 'radio':
      return 'option_1'
    case 'toggle':
    case 'consent':
      return true
    case 'rating':
    case 'scale':
      return 4
    case 'matrix':
      return { row_1: 'column_2' }
    case 'address':
      return { line1: '1 Example Street', city: 'Sample City', postal_code: '00000', country: 'GB' }
    case 'country':
      return 'GB'
    case 'language':
      return 'en'
    case 'timezone':
      return 'Europe/London'
    case 'iban':
      return 'GB33BUKB20201555555555'
    case 'bic':
      return 'DEUTDEFF'
    case 'currency_code':
      return 'EUR'
    case 'ip_address':
      return '203.0.113.10'
    case 'mac_address':
      return '00:1A:2B:3C:4D:5E'
    case 'color':
      return '#1F2937'
    case 'file_upload':
    case 'image_upload':
      return ['FILE_ID_FROM_FILES_UPLOAD']
    case 'signature':
      return null
    case 'long_text':
    case 'rich_text':
      return 'A few sentences of text.'
    default: {
      const fromLabel = sampleForLabel(field)
      return typeof fromLabel === 'string' ? fromLabel : /name/.test(key) ? 'Alex Morgan' : /company|organi[sz]ation/.test(key) ? 'Example Ltd' : 'Some text'
    }
  }
}

/**
 * Examples for lists with levels (F15 M2): each level's example takes only values under the example
 * chosen one level up (Brazil → São Paulo → Campinas), so an example body is one the API accepts.
 */
export function withLevelSamples(fields: ApiEndpointField[]): ApiEndpointField[] {
  const chosen = new Map<string, unknown>()
  const byKey = new Map(fields.map(field => [field.key, field]))
  const narrowed = new Map<string, ApiEndpointField>()
  const visit = (field: ApiEndpointField): ApiEndpointField => {
    if (narrowed.has(field.key)) return narrowed.get(field.key)!
    let result = field
    const parent = field.depends_on ? byKey.get(field.depends_on) : undefined
    if (parent) {
      visit(parent)
      const above = chosen.get(parent.key)
      const values = Array.isArray(above) ? above : above != null ? [above] : []
      result = { ...field, options: (field.options ?? []).filter(option => option.parent !== undefined && values.includes(option.parent)) }
    }
    narrowed.set(field.key, result)
    chosen.set(field.key, sampleValue(result))
    return result
  }
  return fields.map(visit)
}

/** The JSON body a POST / PUT sends: every accepted field (required first). */
export function exampleRequestBody(fields: ApiEndpointField[]) {
  const sent = withLevelSamples(fields).filter(field => field.accept).sort((a, b) => Number(b.required) - Number(a.required))
  // Choices as their labels, as the API reads and returns them (owner 2026-10-08)
  return Object.fromEntries(sent.map(field => [field.name, choiceOut(field, sampleValue(field))]))
}

/** One record as GET returns it: the reference, when, its status and every returned field. */
export function exampleRecord(fields: ApiEndpointField[]) {
  return {
    id: 'rsp_9fK2mQ7xLp',
    submitted_at: '2026-10-06T09:30:00Z',
    status: 'new',
    data: Object.fromEntries(withLevelSamples(fields).filter(field => field.returned).map(field => [field.name, ['file_upload', 'image_upload'].includes(field.type) ? [{ id: 'f_Hc71mQpZsA', name: 'document.pdf', size: 20480, type: 'application/pdf' }] : choiceOut(field, sampleValue(field))])),
  }
}

/** Largest page a GET list may return. */
export const API_PAGE_SIZE_MAX = 100
/** Layout blocks are not questions. */
export const LAYOUT_TYPES: string[] = ['section', 'paragraph', 'divider', 'image']
/** Never sent through the API: signatures (drawn on the form page), calculated values, payments. Files are uploaded first (`…/files`). */
export const NOT_ACCEPTED_TYPES: string[] = ['signature', 'calculated', 'payment']
/** Questions a GET list can be narrowed by. */
export const FILTER_TYPES: string[] = ['short_text', 'email', 'phone', 'number', 'currency', 'percentage', 'date', 'datetime', 'dropdown', 'radio', 'multi_select', 'checkbox', 'toggle', 'consent', 'rating', 'scale', 'slider', 'country', 'language', 'hidden']
/** Paths the API service uses itself. */
export const RESERVED_ENDPOINT_NAMES: string[] = ['token', 'files', 'docs', 'health', 'status', 'openapi', 'webhooks']

/**
 * What publishing a new version changes for apps calling endpoints that follow the latest version
 * (owner, 2026-10-06): questions added (accepted and returned from then on), removed (no longer
 * accepted), and required that were not before (calls without them start failing). Label and
 * design changes keep the keys, so they change nothing for apps.
 */
export function apiChanges(live: { key: string; label: string; required: boolean; type: string }[], draft: { key: string; label?: string; required?: boolean; type: string; readonly?: boolean; disabled?: boolean }[]) {
  const counts = (field: { type: string }) => !LAYOUT_TYPES.includes(field.type) && !NOT_ACCEPTED_TYPES.includes(field.type)
  const before = new Map(live.filter(counts).map(field => [field.key, field]))
  const after = draft.filter(field => field.key && counts(field))
  const keys = new Set(after.map(field => field.key))
  return {
    added: after.filter(field => !before.has(field.key)).map(field => ({ key: field.key, label: field.label ?? field.key, required: !!field.required })),
    removed: [...before.values()].filter(field => !keys.has(field.key)).map(field => ({ key: field.key, label: field.label })),
    nowRequired: after.filter(field => field.required && before.has(field.key) && !before.get(field.key)!.required && !field.readonly && !field.disabled).map(field => ({ key: field.key, label: field.label ?? field.key })),
  }
}

/** Words an API name can not be: they are the record's own fields and the list options. */
export const RESERVED_API_NAMES = ['id', 'submitted_at', 'status', 'data', 'meta', 'page', 'per_page', 'sort', 'error']
/** An API name: lower-case letters, digits and underscores, starting with a letter, up to 64. */
export function checkApiName(name: string): 'required' | 'pattern' | 'reserved' | null {
  if (!name.trim()) return 'required'
  if (!/^[a-z][a-z0-9_]{0,63}$/.test(name)) return 'pattern'
  return RESERVED_API_NAMES.includes(name) ? 'reserved' : null
}

/** An example text answer that fits the label (owner, 2026-10-06: "First name" → Alex, "City" → a city). */
export function sampleForLabel(field: Pick<ApiEndpointField, 'key' | 'label'>): string | number | null {
  const text = ` ${(field.label || field.key).toLowerCase().replace(/[_-]+/g, ' ')} `
  if (/ (first|given) name /.test(text) || /prénom|vorname|nombre /.test(text)) return 'Alex'
  if (/ (last|family) name | surname /.test(text) || /apellido|nachname/.test(text)) return 'Morgan'
  switch (iconFromLabel(field.label, field.key)) {
    case 'i-lucide-user':
      return 'Alex Morgan'
    case 'i-lucide-mail':
      return 'alex.morgan@example.com'
    case 'i-lucide-phone':
      return '+44 7700 900123'
    case 'i-lucide-building-2':
      return 'Example Ltd'
    case 'i-lucide-briefcase':
      return 'Product designer'
    case 'i-lucide-map-pin':
      return '1 Example Street'
    case 'i-lucide-building':
      return 'Sample City'
    case 'i-lucide-map':
      return 'Sample Region'
    case 'i-lucide-mailbox':
      return '10115'
    case 'i-lucide-earth':
      return 'GB'
    case 'i-lucide-globe':
    case 'i-lucide-link':
      return 'https://example.com'
    case 'i-lucide-cake':
      return '1990-04-12'
    case 'i-lucide-banknote':
      return 1250
    case 'i-lucide-hash':
      return 2
    case 'i-lucide-hourglass':
      return 34
    case 'i-lucide-message-square':
      return 'A few sentences of text.'
    case 'i-lucide-tag':
      return 'General enquiry'
    case 'i-lucide-at-sign':
      return 'alexmorgan'
    case 'i-lucide-receipt':
      return 'INV-2026-0042'
    case 'i-lucide-id-card':
      return 'X1234567'
    default:
      return null
  }
}
