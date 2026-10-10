/**
 * Mock AI assistant, analysing (F19 M4, docs/API-CONTRACT.md → AI assistant). All need ai.analyse, the
 * assistant allowed to read forms and responses, and the person allowed to see the form's responses.
 *
 *   POST /ai/analysis                 { form_id, from?, to? } → AiAnalysis (kind analysis)
 *   POST /ai/digest                   { form_id, period (week · month · quarter) } → AiAnalysis (kind summary)
 *   POST /ai/ask                      { form_id, question } → AiAnswer (kind question)
 *   POST /ai/responses/:id/summary    → AiResponseSummary (kind summary)
 */
import { z } from 'zod'
import type { AiAnalysis, AiAnswer, AiResponseSummary } from '#shared/types/ai'
import { AI_KIND_META } from '#shared/utils/ai/kinds'
import { analyse, ask, summarise } from '../ai/analysisEngine'
import { requireAuth } from '../core/auth'
import { MockError, ok } from '../core/respond'
import { defineMockRoute } from '../core/route'
import { parseBody } from '../core/validate'
import { maskText, recordAiRequest, requireAi } from '../data/aiStore'
import { responsesAllowed } from '../data/formPermissions'
import { formsOf, type StoredForm } from '../data/formStore'
import { findResponse, formResponses } from '../data/responseData'
import type { MockTenant, MockUser } from '../data/tenants'

const DAY = 86_400_000
const today = () => Date.parse(new Date().toISOString().slice(0, 10))
const thinking = () => new Promise(resolve => setTimeout(resolve, 800))

/** A form whose responses this person may see (anything else is "not found"). */
function formFor(tenant: MockTenant, user: MockUser, id: string): StoredForm {
  const form = formsOf(tenant).forms.find(item => item.id === id && !item.deleted_at)
  if (!form || !responsesAllowed(form, user, 'view', tenant)) throw new MockError('FRM-GEN-1004')
  return form
}

const day = z.string().regex(/^\d{4}-\d{2}-\d{2}$/)
const analysisInput = z.object({ form_id: z.string().min(1), from: day.nullish(), to: day.nullish() })

export const analysisRoute = defineMockRoute(async ({ event, body }) => {
  const { tenant, user } = requireAuth(event)
  const settings = requireAi(tenant, 'analysis', ['forms', 'responses'])
  const input = parseBody(analysisInput, body)
  const form = formFor(tenant, user, input.form_id)
  const to = input.to ? Date.parse(input.to) : today()
  const from = input.from ? Date.parse(input.from) : to - 29 * DAY
  await thinking()
  const result = analyse(form, formResponses(tenant, form), Math.min(from, to), Math.max(from, to), settings.mask_personal ? maskText : text => text)
  const request = recordAiRequest(tenant, user, {
    kind: 'analysis',
    status: 'applied',
    title: `Analysis of ${form.name}`,
    title_key: { code: 'analysis', params: { form: form.name } },
    target: { type: 'form', id: form.id, name: form.name },
    credits: AI_KIND_META.analysis.credits,
    prompt: `Analyse the responses from ${result.period.from} to ${result.period.to}`,
    result: `${result.totals.responses} responses, ${result.totals.text_answers} written answers, ${result.themes.length} themes.`,
    read: ['forms', 'responses'],
    notes: result.findings,
  })
  const analysis: AiAnalysis = { ...result, request_id: request.id, credits: request.credits }
  return ok(analysis)
})

const digestInput = z.object({ form_id: z.string().min(1), period: z.enum(['week', 'month', 'quarter']).default('week') })
const LENGTH = { week: 7, month: 30, quarter: 91 } as const

export const digestRoute = defineMockRoute(async ({ event, body }) => {
  const { tenant, user } = requireAuth(event)
  const settings = requireAi(tenant, 'summary', ['forms', 'responses'])
  const input = parseBody(digestInput, body)
  const form = formFor(tenant, user, input.form_id)
  const to = today()
  await thinking()
  const result = analyse(form, formResponses(tenant, form), to - (LENGTH[input.period] - 1) * DAY, to, settings.mask_personal ? maskText : text => text)
  const request = recordAiRequest(tenant, user, {
    kind: 'summary',
    status: 'applied',
    title: `${input.period === 'week' ? 'Weekly' : input.period === 'month' ? 'Monthly' : 'Quarterly'} digest of ${form.name}`,
    title_key: { code: `digest_${input.period}`, params: { form: form.name } },
    target: { type: 'form', id: form.id, name: form.name },
    credits: AI_KIND_META.summary.credits,
    prompt: `Summarise the ${input.period} of responses`,
    result: `${result.totals.responses} responses (${result.totals.previous} the ${input.period} before).`,
    read: ['forms', 'responses'],
    notes: result.findings,
  })
  const digest: AiAnalysis = { ...result, request_id: request.id, credits: request.credits }
  return ok(digest)
})

const askInput = z.object({ form_id: z.string().min(1), question: z.string().trim().min(3).max(500) })

export const askRoute = defineMockRoute(async ({ event, body }) => {
  const { tenant, user } = requireAuth(event)
  const settings = requireAi(tenant, 'question', ['forms', 'responses'])
  const input = parseBody(askInput, body)
  const form = formFor(tenant, user, input.form_id)
  await thinking()
  const result = ask(form, formResponses(tenant, form), input.question)
  const request = recordAiRequest(tenant, user, {
    kind: 'question',
    status: 'applied',
    title: input.question.slice(0, 120),
    target: { type: 'form', id: form.id, name: form.name },
    credits: AI_KIND_META.question.credits,
    prompt: settings.mask_personal ? maskText(input.question) : input.question,
    result: result.kind === 'top' ? result.rows.slice(0, 3).map(row => `${row.label}: ${row.count}`).join(', ') : result.kind === 'trend' ? `${result.rows.length} periods` : String(result.value ?? 'No answer'),
    read: ['forms', 'responses'],
    notes: result.notes,
  })
  const answer: AiAnswer = { ...result, question: input.question, request_id: request.id, credits: request.credits }
  return ok(answer)
})

export const responseSummaryRoute = defineMockRoute(async ({ event }) => {
  const { tenant, user } = requireAuth(event)
  const settings = requireAi(tenant, 'summary', ['forms', 'responses'])
  const found = findResponse(tenant, getRouterParam(event, 'id') ?? '')
  if (!found || !responsesAllowed(found.form, user, 'view', tenant)) throw new MockError('FRM-GEN-1004')
  await thinking()
  const result = summarise(found.form, found.entry, settings.mask_personal ? maskText : text => text)
  const request = recordAiRequest(tenant, user, {
    kind: 'summary',
    status: 'applied',
    title: `Summary of response #${found.entry.number}`,
    title_key: { code: 'response_summary', params: { n: found.entry.number } },
    target: { type: 'response', id: found.entry.id, name: `${found.form.name} #${found.entry.number}` },
    credits: AI_KIND_META.summary.credits,
    prompt: `Summarise response #${found.entry.number}`,
    result: result.points.map(point => `${point.label}: ${point.value}`).join('; '),
    read: ['forms', 'responses'],
  })
  const summary: AiResponseSummary = { ...result, request_id: request.id, credits: request.credits }
  return ok(summary)
})
