/**
 * AI assistant in the mock (F19): the workspace's settings and every request (kept for the workspace's
 * chosen days), in `.data/mock/ai.json`. Seeded workspaces start with a month of believable requests
 * so the overview, history and usage have something to show.
 */
import { AI_KINDS, AI_STATUSES, type AiDraftStats, type AiKind, type AiNote, type AiRequestDetail, type AiRequestRow, type AiSettings, type AiSource, type AiStatus, type AiTarget } from '#shared/types/ai'
import { AI_DEFAULT_MONTHLY_CREDITS, AI_KIND_META } from '#shared/utils/ai/kinds'
import { loadPersisted, savePersisted } from '../core/persist'
import { MockError } from '../core/respond'
import { formsOf } from './formStore'
import { MOCK_FORMS } from './forms'
import { MOCK_USERS, SEEDED_TENANT_IDS, type MockTenant, type MockUser } from './tenants'

export interface StoredAiRequest {
  id: string
  kind: AiKind
  status: AiStatus
  title: string
  by: { id: string; name: string }
  target: AiTarget | null
  credits: number
  prompt: string
  result: string
  read: AiSource[]
  masked: boolean
  created_at: string
  applied_at: string | null
  /** The draft itself (schema, designs …) until it is applied or discarded. */
  output?: unknown
  notes?: AiNote[]
  stats?: AiDraftStats
}

interface TenantAi {
  settings: AiSettings
  requests: StoredAiRequest[]
}

const DAY = 86_400_000
const stores = new Map<string, TenantAi>(Object.entries(loadPersisted<Record<string, TenantAi>>('ai', {})))
export const saveAi = () => savePersisted('ai', () => Object.fromEntries(stores))

const defaultSettings = (): AiSettings => ({
  enabled: true,
  sources: { forms: true, responses: true, data: false },
  mask_personal: true,
  keep_days: 90,
  monthly_credits: AI_DEFAULT_MONTHLY_CREDITS,
  updated_at: null,
  updated_by: null,
})

const nameOf = (user: MockUser) => `${user.first_name} ${user.last_name}`.trim()

/** A month of requests for the sample workspaces: [kind, status, days ago, title, prompt, result, form index]. */
const SEEDS: [AiKind, AiStatus, number, string, string, string, number | null][] = [
  ['form', 'applied', 1, 'Visitor sign-in form', 'A sign-in form for visitors at reception: name, company, who they are visiting, arrival time, a photo and agreement to the site rules.', 'A one-page draft with 7 questions, a required agreement and the arrival time filled in automatically.', null],
  ['analysis', 'proposed', 2, 'Themes in client feedback', 'What are clients saying about our service this month?', 'Four themes: response time (most mentioned), clear communication, fees, and online access. Mostly positive; fees mentioned negatively by 1 in 5.', 0],
  ['translate', 'applied', 3, 'Translate into French and Spanish', 'Translate the form into French and Spanish.', '38 texts translated into 2 languages; 3 left for review (legal wording).', 1],
  ['summary', 'applied', 4, 'Weekly digest', 'Summarise last week’s responses.', '126 responses (up 14%). Completion stayed at 82%. Most answers came on Tuesday.', 0],
  ['builder', 'applied', 5, 'Write help texts', 'Write short help texts for every question.', 'Help texts for 9 questions, plain language, under 20 words each.', 2],
  ['question', 'applied', 6, 'Which office had most requests?', 'Which office had the most requests last month?', 'The Riverside office: 48 requests (31%), then Harbour (36) and Central (29). Filters used: last month, all statuses.', 0],
  ['template', 'discarded', 8, 'Equipment loan template', 'A template for lending equipment to staff: item, serial number, dates, condition on return.', 'A two-page template with a matching neutral design.', null],
  ['rewrite', 'applied', 9, 'Plainer wording', 'Make the questions easier to read.', '6 questions rewritten in plainer words; reading age lowered from 14 to 11.', 2],
  ['theme', 'applied', 11, 'Design from brand colour', 'A design from our brand colour #0F766E.', 'A calm theme with the brand colour for buttons and progress, white page and dark text.', null],
  ['analysis', 'applied', 13, 'Sentiment over time', 'How has satisfaction changed since last quarter?', 'Satisfaction rose from 3.6 to 4.1 out of 5; complaints about waiting times fell by half.', 1],
  ['form', 'failed', 15, 'Import from a document', 'Make a form from the attached policy document.', 'The document had no questions or fields to turn into a form.', null],
  ['summary', 'applied', 18, 'Summary of a response', 'Summarise this response for the case file.', 'A short summary in four lines with the key dates and the request.', 0],
  ['question', 'proposed', 21, 'Average rating by month', 'What is the average rating per month this year?', 'Average rating per month from January to now, with the number of answers each month.', 1],
  ['builder', 'discarded', 24, 'Check my form', 'Check my form for problems.', '3 suggestions: an email question without email checking, two questions asking the same thing, an image without a description.', 2],
  ['translate', 'applied', 27, 'Translate into Arabic', 'Translate the form into Arabic.', '41 texts translated; the form reads right to left in Arabic.', 2],
]

function seed(tenant: MockTenant): StoredAiRequest[] {
  if (!SEEDED_TENANT_IDS.has(tenant.id)) return []
  const people = MOCK_USERS.filter(user => user.tenant_id === tenant.id && !user.disabled)
  // The workspace's sample forms (not something someone made while trying things out)
  const samples = new Set(MOCK_FORMS.map(form => form.id))
  const forms = formsOf(tenant).forms.filter(form => samples.has(form.id) && form.status !== 'archived' && !form.deleted_at)
  if (!people.length) return []
  return SEEDS.map(([kind, status, daysAgo, title, prompt, result, formIndex], index) => {
    const person = people[index % people.length]!
    const created = Date.now() - daysAgo * DAY - (index * 5 + 2) * 3_600_000
    const form = formIndex !== null ? forms[formIndex % Math.max(1, forms.length)] : undefined
    const target: AiTarget | null = form ? { type: 'form', id: form.id, name: form.name } : null
    const read: AiSource[] = kind === 'analysis' || kind === 'question' || kind === 'summary' ? ['forms', 'responses'] : form ? ['forms'] : []
    return {
      id: crypto.randomUUID(),
      kind,
      status,
      title,
      by: { id: person.id, name: nameOf(person) },
      target,
      credits: status === 'failed' ? 0 : AI_KIND_META[kind].credits * (kind === 'translate' && title.includes(' and ') ? 2 : 1),
      prompt,
      result,
      read,
      masked: true,
      created_at: new Date(created).toISOString(),
      applied_at: status === 'applied' ? new Date(created + 6 * 60_000).toISOString() : null,
    }
  })
}

/** The workspace's assistant (settings and requests), requests past the keep setting removed. */
export function aiOf(tenant: MockTenant): TenantAi {
  let store = stores.get(tenant.id)
  if (!store) {
    store = { settings: defaultSettings(), requests: seed(tenant) }
    stores.set(tenant.id, store)
    saveAi()
  }
  const cutoff = Date.now() - store.settings.keep_days * DAY
  const kept = store.requests.filter(request => Date.parse(request.created_at) >= cutoff)
  if (kept.length !== store.requests.length) {
    store.requests = kept
    saveAi()
  }
  return store
}

/** The start of this month (UTC), the allowance's period. */
export const monthStart = (now = new Date()) => new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), 1))

/** Credits used since the start of this month. */
export const creditsUsed = (tenant: MockTenant) => {
  const start = monthStart().getTime()
  return aiOf(tenant).requests.reduce((sum, request) => (Date.parse(request.created_at) >= start ? sum + request.credits : sum), 0)
}

/**
 * Every assistant call starts here: the assistant must be on (FRM-AI-1001), may read what the call needs
 * (FRM-AI-1003) and the month's allowance must cover it (FRM-AI-1002).
 */
export function requireAi(tenant: MockTenant, kind: AiKind, needs: AiSource[] = []): AiSettings {
  const { settings } = aiOf(tenant)
  if (!settings.enabled) throw new MockError('FRM-AI-1001')
  if (needs.some(source => !settings.sources[source])) throw new MockError('FRM-AI-1003')
  if (creditsUsed(tenant) + AI_KIND_META[kind].credits > settings.monthly_credits) throw new MockError('FRM-AI-1002')
  return settings
}

/** Keep a request (the assistant's routes call this once they have a result). */
export function recordAiRequest(tenant: MockTenant, user: MockUser, input: Omit<StoredAiRequest, 'id' | 'by' | 'created_at' | 'applied_at' | 'masked'> & { masked?: boolean }): StoredAiRequest {
  const store = aiOf(tenant)
  const request: StoredAiRequest = {
    ...input,
    masked: input.masked ?? store.settings.mask_personal,
    id: crypto.randomUUID(),
    by: { id: user.id, name: nameOf(user) },
    created_at: new Date().toISOString(),
    applied_at: input.status === 'applied' ? new Date().toISOString() : null,
  }
  store.requests.unshift(request)
  saveAi()
  return request
}

export const toAiRow = (request: StoredAiRequest, user: MockUser): AiRequestRow => ({
  id: request.id,
  kind: request.kind,
  status: request.status,
  title: request.title,
  by: request.by,
  target: request.target,
  credits: request.credits,
  created_at: request.created_at,
  applied_at: request.applied_at,
  mine: request.by.id === user.id,
})

export const toAiDetail = (tenant: MockTenant, request: StoredAiRequest, user: MockUser): AiRequestDetail => ({
  ...toAiRow(request, user),
  prompt: request.prompt,
  result: request.result,
  read: request.read,
  masked: request.masked,
  expires_at: new Date(Date.parse(request.created_at) + aiOf(tenant).settings.keep_days * DAY).toISOString(),
  ...(request.notes ? { notes: request.notes } : {}),
  ...(request.stats ? { stats: request.stats } : {}),
})

export const emptyByKind = () => Object.fromEntries(AI_KINDS.map(kind => [kind, 0])) as Record<AiKind, number>
export const emptyByStatus = () => Object.fromEntries(AI_STATUSES.map(status => [status, 0])) as Record<AiStatus, number>

/** Emails, phone numbers and long digit runs replaced before anything is kept or sent (Settings → Keep personal data out). */
export const maskText = (text: string) =>
  text
    .replace(/[\w.+-]+@[\w-]+(\.[\w-]+)+/g, '[email]')
    // Phone-like runs of digits; dates (2026-03-14) and times stay
    .replace(/\+?\d[\d\s().-]{7,}\d/g, match => (/^\d{4}-\d{2}-\d{2}(T[\d:.]+Z?)?$/.test(match.trim()) ? match : '[number]'))
