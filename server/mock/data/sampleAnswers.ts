/**
 * Sample answers for the mock (F11): realistic, stable answers that fit each question type, so
 * seeded forms have responses to list, review and chart. Names are international and neutral,
 * emails use example domains, phone numbers the reserved +44 7700 900xxx range, IP and MAC
 * addresses the documentation ranges (CLAUDE.md rule 20). Same form + same index = same answers.
 */
import { allFields, type FormField } from '#shared/utils/forms/build'
import { calculateResult } from '#shared/utils/forms/formula'
import { isInputField } from '#shared/utils/forms/fields'
import type { FormSchemaV1 } from '#shared/utils/forms/schema'

/** A small seeded generator (mulberry32) from a text. */
export function rngOf(text: string) {
  let seed = 2166136261
  for (const char of text) seed = Math.imul(seed ^ char.charCodeAt(0), 16777619)
  return () => {
    seed = (seed + 0x6d2b79f5) | 0
    let t = Math.imul(seed ^ (seed >>> 15), 1 | seed)
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296
  }
}
export type Rng = ReturnType<typeof rngOf>
// ── Sample ids: index in the first block, a marker, the form id's tail in the last ─────
const MARK = '5a3e'
export const tailOf = (formId: string) => formId.replace(/-/g, '').slice(-12)
export const sampleId = (formId: string, index: number) => `${index.toString(16).padStart(8, '0')}-${MARK}-4000-8000-${tailOf(formId)}`
export function parseSampleId(id: string): { index: number; tail: string } | null {
  const parts = id.split('-')
  return parts.length === 5 && parts[1] === MARK ? { index: parseInt(parts[0]!, 16), tail: parts[4]! } : null
}

const pick = <T>(rng: Rng, list: readonly T[]): T => list[Math.floor(rng() * list.length)]!
const between = (rng: Rng, min: number, max: number) => min + Math.floor(rng() * (max - min + 1))

const FIRST = ['Amara', 'Kenji', 'Sofia', 'Lucas', 'Priya', 'Omar', 'Elena', 'Mateo', 'Aisha', 'Liam', 'Yuki', 'Chen', 'Fatima', 'Noah', 'Zara', 'Ivan', 'Leila', 'Diego', 'Hana', 'Tomas', 'Nia', 'Arjun', 'Mei', 'Samuel', 'Ingrid', 'Kwame', 'Lucia', 'Rafael', 'Selin', 'Anya', 'Malik', 'Freya', 'Joon', 'Ama', 'Pablo', 'Sara']
const LAST = ['Okafor', 'Tanaka', 'Rossi', 'Silva', 'Sharma', 'Haddad', 'Petrova', 'Garcia', 'Mensah', 'Nguyen', 'Kim', 'Muller', 'Dubois', 'Novak', 'Santos', 'Ali', 'Johansson', 'Costa', 'Ito', 'Kowalski', 'Laurent', 'Rahman', 'Moreno', 'Lindqvist', 'Adeyemi', 'Fischer', 'Park', 'Hughes', 'Kaya', 'Osei']
const DOMAINS = ['example.com', 'example.org', 'example.net']
const CITIES = ['Lisbon', 'Nairobi', 'Toronto', 'Seoul', 'Melbourne', 'Accra', 'Lyon', 'Osaka', 'Bogota', 'Krakow', 'Dubai', 'Cape Town', 'Oslo', 'Manila', 'Lima', 'Hanoi']
const COUNTRIES = ['PT', 'KE', 'CA', 'KR', 'AU', 'GH', 'FR', 'JP', 'CO', 'PL', 'AE', 'ZA', 'NO', 'PH', 'PE', 'VN', 'DE', 'BR', 'IN', 'GB']
const COMPANIES = ['Northwind Trading', 'Bluebird Studio', 'Harbour & Co', 'Summit Logistics', 'Greenleaf Foods', 'Atlas Engineering', 'Riverstone Health', 'Brightpath Learning', 'Cedar Legal', 'Orbit Media']
const ROLES = ['Operations lead', 'Product designer', 'Office manager', 'Teacher', 'Nurse', 'Software engineer', 'Accountant', 'Sales manager', 'Researcher', 'Student']
const SHORT = ['Looks good', 'Happy to help', 'Not sure yet', 'Next week works', 'All set', 'Please call me', 'Morning is best', 'As discussed', 'No preference', 'See attached']
const LONG = [
  'The process was quick and clear. I liked that I could see every step before sending.',
  'Everything worked well on my phone. The only thing I would add is a way to save a draft.',
  'Friendly team and fast answers. I would recommend it to colleagues.',
  'It took a moment to find the right option, but the help text explained it.',
  'Great experience overall. Delivery was a day later than expected.',
  'I would like more choices for the time slot, mornings are hard for me.',
  'Clear instructions and a simple form. Thank you for making it easy.',
  'The price was fair and the quality better than I expected.',
  'Could you send a copy of my answers by email? That would help with my records.',
  'Some questions felt repetitive, otherwise all good.',
  'Very professional. I will come back for the next session.',
  'The location was easy to reach and the staff were welcoming.',
]
const TIMEZONES = ['Europe/Lisbon', 'Africa/Nairobi', 'America/Toronto', 'Asia/Seoul', 'Australia/Melbourne', 'Europe/Paris', 'Asia/Tokyo', 'America/Bogota']
const CURRENCIES = ['EUR', 'USD', 'GBP', 'JPY', 'KES', 'CAD', 'AUD', 'BRL', 'INR', 'ZAR']
const LANGUAGES = ['en', 'fr', 'es', 'pt', 'de', 'ja', 'ar', 'sw', 'hi', 'ko']
const SOURCES = ['newsletter', 'website', 'partner', 'social', 'event']

/** The person behind a sample response (also used for its name and email answers). */
export interface SamplePerson {
  first: string
  last: string
  email: string
  phone: string
}
export function samplePerson(rng: Rng): SamplePerson {
  const first = pick(rng, FIRST)
  const last = pick(rng, LAST)
  return {
    first,
    last,
    email: `${first}.${last}${between(rng, 1, 99)}@${pick(rng, DOMAINS)}`.toLowerCase(),
    phone: `+44 7700 900${String(between(rng, 0, 999)).padStart(3, '0')}`,
  }
}

/** Uneven but stable weights per option, so charts show a real spread. */
function weightsFor(seed: string, count: number) {
  const rng = rngOf(seed)
  const favourite = Math.floor(rng() * count)
  return Array.from({ length: count }, (_, i) => (0.25 + rng()) * (i === favourite ? 1.6 : 1))
}
function weighted<T>(rng: Rng, items: readonly T[], weights: number[]): T {
  const total = weights.reduce((a, b) => a + b, 0)
  let roll = rng() * total
  for (let i = 0; i < items.length; i++) if ((roll -= weights[i]!) <= 0) return items[i]!
  return items[items.length - 1]!
}
/** Ratings lean positive, like real feedback. */
const leanHigh = (rng: Rng, min: number, max: number) => Math.min(max, Math.max(min, Math.round(max - Math.abs(rng() + rng() - 1) * (max - min) * 1.1)))

const pad = (n: number) => String(n).padStart(2, '0')
const dayBefore = (at: number, rng: Rng, days: number) => new Date(at - Math.floor(rng() * days) * 86_400_000).toISOString().slice(0, 10)

function answerFor(field: FormField, rng: Rng, person: SamplePerson, at: number, formSeed: string, index: number): unknown {
  const label = (field.label ?? '').toLowerCase()
  const p = (field.props ?? {}) as Record<string, unknown>
  const options = (field.options ?? []).map(option => option.value)
  const weights = weightsFor(`${formSeed}:${field.id}`, options.length)
  switch (field.type) {
    case 'short_text':
      if (/first|given/.test(label)) return person.first
      if (/last|family|surname/.test(label)) return person.last
      if (/name/.test(label)) return `${person.first} ${person.last}`
      if (/company|organi[sz]ation|business|employer/.test(label)) return pick(rng, COMPANIES)
      if (/city|town/.test(label)) return pick(rng, CITIES)
      if (/title|role|job|position/.test(label)) return pick(rng, ROLES)
      return pick(rng, SHORT)
    case 'long_text':
      return pick(rng, LONG)
    case 'rich_text':
      return `<p>${pick(rng, LONG)}</p>`
    case 'email':
      return person.email
    case 'phone':
      return person.phone
    case 'url':
    case 'domain':
      return field.type === 'url' ? `https://www.example.org/${person.last.toLowerCase()}` : 'example.org'
    case 'full_name':
      return { first: person.first, last: person.last }
    case 'number':
    case 'percentage': {
      const min = Number((field.validation as Record<string, unknown> | undefined)?.min ?? (field.type === 'percentage' ? 0 : 1))
      const max = Number((field.validation as Record<string, unknown> | undefined)?.max ?? (field.type === 'percentage' ? 100 : 50))
      return between(rng, Math.min(min, max), Math.max(min, max))
    }
    case 'currency':
      return Math.round((20 + rng() * rng() * 4980) * 100) / 100
    case 'date':
      return dayBefore(at, rng, 400)
    case 'time':
      return `${pad(between(rng, 8, 19))}:${pick(rng, ['00', '15', '30', '45'])}`
    case 'datetime':
      return `${dayBefore(at, rng, 60)}T${pad(between(rng, 8, 19))}:${pick(rng, ['00', '30'])}`
    case 'date_range': {
      const from = dayBefore(at, rng, 30)
      return { from, to: new Date(Date.parse(from) + between(rng, 1, 14) * 86_400_000).toISOString().slice(0, 10) }
    }
    case 'duration':
      return { hours: between(rng, 0, 8), minutes: pick(rng, [0, 15, 30, 45]) }
    case 'dropdown':
    case 'radio':
      return options.length ? weighted(rng, options, weights) : null
    case 'checkbox':
    case 'multi_select': {
      if (!options.length) return null
      const chosen = options.filter((_, i) => rng() < Math.min(0.85, weights[i]! / 2.2))
      return chosen.length ? chosen : [weighted(rng, options, weights)]
    }
    case 'ranking':
      return [...options].sort(() => rng() - 0.5)
    case 'matrix': {
      const rows = ((p.rows as string[] | undefined) ?? []).filter(Boolean)
      return options.length ? Object.fromEntries(rows.map(row => [row, weighted(rng, options, weights)])) : null
    }
    case 'toggle':
      return rng() < 0.62
    case 'consent':
      return true
    case 'rating':
      return leanHigh(rng, 1, Number(p.max ?? 5))
    case 'scale':
      return leanHigh(rng, Number(p.min ?? 0), Number(p.max ?? 10))
    case 'slider': {
      const min = Number(p.min ?? 0)
      const max = Number(p.max ?? 100)
      return Math.round(min + (max - min) * (0.3 + rng() * 0.6))
    }
    case 'file_upload':
    case 'image_upload': {
      const picture = field.type === 'image_upload'
      const name = picture ? `photo-${index % 97}.jpg` : pick(rng, ['cv.pdf', 'certificate.pdf', 'invoice.pdf', 'plan.docx', 'id-scan.pdf'])
      return [{ id: '', name, size: between(rng, 40_000, 2_400_000), type: picture ? 'image/jpeg' : name.endsWith('.docx') ? 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' : 'application/pdf', sample: true }]
    }
    case 'signature':
      return null
    case 'address':
      return { line1: `${between(rng, 1, 240)} ${pick(rng, ['Harbour Road', 'Park Avenue', 'Station Street', 'Garden Lane', 'Market Square'])}`, city: pick(rng, CITIES), region: '', postal_code: String(between(rng, 10000, 99999)), country: pick(rng, COUNTRIES) }
    case 'country':
      return pick(rng, COUNTRIES)
    case 'language':
      return pick(rng, LANGUAGES)
    case 'timezone':
      return pick(rng, TIMEZONES)
    case 'currency_code':
      return pick(rng, CURRENCIES)
    case 'ip_address':
      return `192.0.2.${between(rng, 1, 254)}`
    case 'mac_address':
      return `00:00:5E:00:53:${pad(between(rng, 10, 99))}`
    case 'color':
      return `#${Math.floor(rng() * 0xffffff).toString(16).padStart(6, '0')}`
    case 'iban':
      return 'GB82 WEST 1234 5698 7654 32'
    case 'bic':
      return 'FRMLGB2L'
    case 'hidden':
      return pick(rng, SOURCES)
    default:
      return null
  }
}

/** Every answer of one sample response: required questions always, optional ones most of the time. */
export function sampleAnswers(schema: FormSchemaV1, formSeed: string, index: number, person: SamplePerson, at: number): Record<string, unknown> {
  const rng = rngOf(`${formSeed}:answers:${index}`)
  const fields = allFields(schema).filter(field => isInputField(field.type) && field.type !== 'calculated' && field.type !== 'payment')
  const data: Record<string, unknown> = {}
  for (const field of fields) {
    if (!field.required && rng() > 0.78) continue
    const value = answerFor(field, rng, person, at, formSeed, index)
    if (value != null) data[field.key] = value
  }
  // Calculated questions: worked out from the answers, like on the real form.
  const byKey = new Map(allFields(schema).map(field => [field.key, field]))
  for (const field of allFields(schema).filter(item => item.type === 'calculated')) {
    const value = calculateResult(String(field.props?.formula ?? ''), data, byKey)
    if (value != null && value !== '') data[field.key] = value
  }
  return data
}
