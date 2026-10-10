/**
 * Pure text helpers for the mock assistant's analysis (F19 M4): what written answers are about (themes),
 * their tone (sentiment) and the period a question names. Word lists, no outside service.
 */
import type { AiSentiment, AiTheme } from '#shared/types/ai'
import type { FormField } from '#shared/utils/forms/build'

const DAY = 86_400_000
const isoDay = (ms: number) => new Date(ms).toISOString().slice(0, 10)

const THEME_WORDS: Record<Exclude<AiTheme, 'other'>, RegExp> = {
  speed: /\b(quick|quickly|fast|slow|wait|waiting|delay|delayed|took|later than|on time|minutes?|hours?)\b/i,
  ease: /\b(easy|simple|clear|instructions?|confus\w*|repetitive|find|understand|steps?|help text|complicated)\b/i,
  staff: /\b(team|staff|friendly|welcoming|professional|helpful|rude|polite|people|service)\b/i,
  price: /\b(price|prices|cost|costs|fee|fees|expensive|cheap|value|fair|afford\w*)\b/i,
  quality: /\b(quality|great|excellent|poor|better|worse|best|experience)\b/i,
  mobile: /\b(phone|mobile|app|online|website|laptop|screen)\b/i,
  communication: /\b(email|e-mail|call|copy|contact|reply|replies|answer|answers|update|records)\b/i,
  scheduling: /\b(time slot|slots?|morning|mornings|evening|schedule|session|booking|appointment|draft)\b/i,
  location: /\b(location|reach|parking|place|site|building|room)\b/i,
  delivery: /\b(delivery|deliveries|shipping|shipped|arrived|parcel)\b/i,
}
const POSITIVE = /\b(good|great|quick|fast|friendly|easy|clear|liked|love|loved|excellent|fair|better than|welcoming|professional|recommend|happy|thank|thanks|simple|well|helpful|polite|on time)\b/gi
const NEGATIVE = /\b(slow|late|later than|hard|difficult|confus\w*|repetitive|expensive|poor|bad|rude|problem|issue|wait\w*|delay\w*|worse|missing|broken|disappoint\w*|took a moment)\b/gi

/** The written answers in a response (short and long text, and rich text without tags). */
export function textOf(fields: FormField[], data: Record<string, unknown>): string[] {
  return fields
    .filter(field => ['long_text', 'rich_text'].includes(field.type) || (field.type === 'short_text' && !/\b(name|email|phone|company|city|title|role|job|reference)\b/i.test(field.label)))
    .map(field => data[field.key])
    .filter((value): value is string => typeof value === 'string' && value.trim().length > 3)
    .map(value => value.replace(/<[^>]+>/g, ' ').trim())
}

export const themesOf = (text: string): AiTheme[] => {
  const found = (Object.keys(THEME_WORDS) as Exclude<AiTheme, 'other'>[]).filter(key => THEME_WORDS[key].test(text))
  return found.length ? found : ['other']
}

export function sentimentOf(text: string): keyof AiSentiment {
  const positive = text.match(POSITIVE)?.length ?? 0
  const negative = text.match(NEGATIVE)?.length ?? 0
  return positive > negative ? 'positive' : negative > positive ? 'negative' : 'neutral'
}

const MONTHS = ['january', 'february', 'march', 'april', 'may', 'june', 'july', 'august', 'september', 'october', 'november', 'december']

/** The period a question names ("last month", "this week", "in March", "last 30 days"), else null. */
export function periodIn(question: string, now = Date.now()): { from: number; to: number; label: string } | null {
  const q = question.toLowerCase()
  const today = Date.parse(isoDay(now))
  const date = new Date(today)
  const startOfWeek = today - ((date.getUTCDay() + 6) % 7) * DAY
  const month = (offset: number) => {
    const start = Date.UTC(date.getUTCFullYear(), date.getUTCMonth() + offset, 1)
    const end = Date.UTC(date.getUTCFullYear(), date.getUTCMonth() + offset + 1, 1) - DAY
    return { from: start, to: Math.min(end, today) }
  }
  const days = q.match(/\b(?:last|past)\s+(\d{1,3})\s+days?\b/)
  if (days) return { from: today - (Number(days[1]) - 1) * DAY, to: today, label: `last ${days[1]} days` }
  if (/\btoday\b/.test(q)) return { from: today, to: today, label: 'today' }
  if (/\byesterday\b/.test(q)) return { from: today - DAY, to: today - DAY, label: 'yesterday' }
  if (/\bthis week\b/.test(q)) return { from: startOfWeek, to: today, label: 'this week' }
  if (/\blast week\b/.test(q)) return { from: startOfWeek - 7 * DAY, to: startOfWeek - DAY, label: 'last week' }
  if (/\bthis month\b/.test(q)) return { ...month(0), label: 'this month' }
  if (/\blast month\b/.test(q)) return { ...month(-1), label: 'last month' }
  if (/\bthis year\b/.test(q)) return { from: Date.UTC(date.getUTCFullYear(), 0, 1), to: today, label: 'this year' }
  if (/\blast year\b/.test(q)) return { from: Date.UTC(date.getUTCFullYear() - 1, 0, 1), to: Date.UTC(date.getUTCFullYear(), 0, 1) - DAY, label: 'last year' }
  const named = MONTHS.findIndex(name => new RegExp(`\\b(in )?${name}\\b`).test(q))
  if (named >= 0) {
    const year = named > date.getUTCMonth() ? date.getUTCFullYear() - 1 : date.getUTCFullYear()
    return { from: Date.UTC(year, named, 1), to: Math.min(Date.UTC(year, named + 1, 1) - DAY, today), label: MONTHS[named]! }
  }
  return null
}

