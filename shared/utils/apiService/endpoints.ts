/**
 * Endpoint rules shared by the wizard and the server (F13): which questions an endpoint may
 * accept, filter on and return, the defaults for a new endpoint, the name check and the example
 * request / record shown in the portal and the docs. Values in examples are neutral, made up.
 */
import type { ApiEndpointField } from '#shared/types/apiService'
import { allFields, type FormField } from '#shared/utils/forms/build'
import type { FormSchemaV1 } from '#shared/utils/forms/schema'
import { ENDPOINT_PATTERN } from '#shared/utils/urls/public'

/** One question as an endpoint field, with the defaults for a new endpoint. */
export function endpointFieldsOf(schema: FormSchemaV1, saved?: { key: string; accept: boolean; required: boolean; returned: boolean; filter: boolean }[]): ApiEndpointField[] {
  const byKey = new Map((saved ?? []).map(item => [item.key, item]))
  const pageOf = new Map(schema.pages.flatMap((page, index) => page.rows.flatMap(row => row.fields.map(field => [field.id, index] as const))))
  return allFields(schema)
    .filter(field => !LAYOUT_TYPES.includes(field.type))
    .map(field => {
      const acceptable = isAcceptable(field)
      const filterable = FILTER_TYPES.includes(field.type)
      const formRequired = !!field.required && acceptable
      const own = byKey.get(field.key)
      const accept = acceptable && (formRequired || (own ? own.accept : true))
      return {
        key: field.key,
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
      }
    })
}

/** Can be sent through the API: not read-only, disabled, calculated, a file or a payment. */
export function isAcceptable(field: Pick<FormField, 'type' | 'readonly' | 'disabled'>) {
  return !field.readonly && !field.disabled && !NOT_ACCEPTED_TYPES.includes(field.type)
}

/** Why a field can't be sent, for the hint beside it (null = it can). */
export function notAcceptedReason(field: Pick<ApiEndpointField, 'type' | 'acceptable'>): 'file' | 'calculated' | 'payment' | 'locked' | null {
  if (field.acceptable) return null
  if (['file_upload', 'image_upload', 'signature'].includes(field.type)) return 'file'
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
export function sampleValue(field: Pick<ApiEndpointField, 'type' | 'key' | 'label'>): unknown {
  const key = `${field.key} ${field.label}`.toLowerCase()
  switch (field.type) {
    case 'email':
      return 'alex.morgan@example.com'
    case 'phone':
      return '+44 7700 900123'
    case 'url':
    case 'domain':
      return field.type === 'url' ? 'https://example.com' : 'example.com'
    case 'number':
    case 'slider':
      return 42
    case 'currency':
      return { amount: 120.5, currency: 'EUR' }
    case 'percentage':
      return 75
    case 'full_name':
      return { first: 'Alex', last: 'Morgan' }
    case 'date':
      return '2026-10-06'
    case 'time':
      return '09:30'
    case 'datetime':
      return '2026-10-06T09:30:00Z'
    case 'date_range':
      return { from: '2026-10-06', to: '2026-10-10' }
    case 'duration':
      return 'PT1H30M'
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
    case 'signature':
      return { name: 'document.pdf', size: 20480, url: 'https://api.formalie.dev/files/…' }
    case 'long_text':
    case 'rich_text':
      return 'A few sentences of text.'
    default:
      return /name/.test(key) ? 'Alex Morgan' : /company|organi[sz]ation/.test(key) ? 'Example Ltd' : 'Some text'
  }
}

/** The JSON body a POST / PUT sends: every accepted field (required first). */
export function exampleRequestBody(fields: ApiEndpointField[]) {
  const sent = fields.filter(field => field.accept).sort((a, b) => Number(b.required) - Number(a.required))
  return Object.fromEntries(sent.map(field => [field.key, sampleValue(field)]))
}

/** One record as GET returns it: the reference, when, its status and every returned field. */
export function exampleRecord(fields: ApiEndpointField[]) {
  return {
    id: 'rsp_9fK2mQ7xLp',
    submitted_at: '2026-10-06T09:30:00Z',
    status: 'new',
    data: Object.fromEntries(fields.filter(field => field.returned).map(field => [field.key, sampleValue(field)])),
  }
}

/** Largest page a GET list may return. */
export const API_PAGE_SIZE_MAX = 100
/** Layout blocks are not questions. */
export const LAYOUT_TYPES: string[] = ['section', 'paragraph', 'divider', 'image']
/** Never sent through the API in this version: files (upload first, later), calculated values, payments. */
export const NOT_ACCEPTED_TYPES: string[] = ['file_upload', 'image_upload', 'signature', 'calculated', 'payment']
/** Questions a GET list can be narrowed by. */
export const FILTER_TYPES: string[] = ['short_text', 'email', 'phone', 'number', 'currency', 'percentage', 'date', 'datetime', 'dropdown', 'radio', 'multi_select', 'checkbox', 'toggle', 'consent', 'rating', 'scale', 'slider', 'country', 'language', 'hidden']
/** Paths the API service uses itself. */
export const RESERVED_ENDPOINT_NAMES: string[] = ['token', 'files', 'docs', 'health', 'status', 'openapi', 'webhooks']
