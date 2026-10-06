/**
 * Personal answers masked wherever the mock keeps a copy of a body (API request log, webhook
 * deliveries): `a•••z` for text, `•••` for anything else, structure kept.
 */
export const PERSONAL_TYPES = new Set(['email', 'phone', 'full_name', 'address', 'iban', 'bic', 'ip_address', 'signature', 'date'])

const maskText = (value: unknown): unknown =>
  typeof value === 'string' ? (value.length <= 2 ? '••' : `${value[0]}•••${value.slice(-1)}`) : Array.isArray(value) ? value.map(maskText) : value && typeof value === 'object' ? Object.fromEntries(Object.entries(value).map(([k, v]) => [k, maskText(v)])) : value == null ? value : '•••'

/** Masks the values of the given question keys at any depth. */
export function maskAnswers(value: unknown, personal: Set<string>): unknown {
  if (Array.isArray(value)) return value.map(item => maskAnswers(item, personal))
  if (!value || typeof value !== 'object') return value
  return Object.fromEntries(Object.entries(value as Record<string, unknown>).map(([key, item]) => [key, personal.has(key) ? maskText(item) : maskAnswers(item, personal)]))
}
