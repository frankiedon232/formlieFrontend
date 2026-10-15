/**
 * Mock form overview (docs/API-CONTRACT.md → Forms): statistics, a 30-day response trend,
 * structure, latest versions and the template the form came from. Responses, the trend and the
 * last response come from the response data (F11, decision 100); views, starts and the completion
 * rate from the fill-in page's recorded events (owner decision 2026-10-15; zeros without events).
 */
import type { FormOverview } from '#shared/types/forms'
import { previewLabels, schemaStats, systemTemplate } from '#shared/templates'
import { requireAuth } from '../core/auth'
import { MockError, ok } from '../core/respond'
import { defineMockRoute } from '../core/route'
import { formsOf } from '../data/formStore'
import { requireLevel } from '../data/formPermissions'
import { findWorkspaceTemplate } from '../data/templateStore'
import { ensureSchema } from './formDraft'
import { formResponses } from '../data/responseData'
import { formFillEvents } from '../data/fillEventStore'
import { completionRate, visitCounts } from '#shared/utils/analytics/events'

const DAY = 86_400_000
const medianSeconds = (entries: { duration_seconds: number | null }[]) => {
  const times = entries.map(entry => entry.duration_seconds).filter((n): n is number => n != null).sort((a, b) => a - b)
  if (!times.length) return null
  const mid = Math.floor(times.length / 2)
  return Math.round(times.length % 2 ? times[mid]! : (times[mid - 1]! + times[mid]!) / 2)
}

export const getFormOverview = defineMockRoute(({ event }) => {
  const { tenant, user } = requireAuth(event)
  const form = formsOf(tenant).forms.find(item => item.id === getRouterParam(event, 'id'))
  if (form) requireLevel(form, user, 'responses')
  if (!form) throw new MockError('FRM-GEN-1004')
  const schema = ensureSchema(form, tenant)
  // Responses, trend and last response from the real response data (decision 100), so a new
  // submission shows here at once and agrees with the Responses page.
  const entries = formResponses(tenant, form)
  const today = Date.parse(new Date().toISOString().slice(0, 10))
  const daily = Array.from({ length: 30 }, (_, i) => ({ date: new Date(today - (29 - i) * DAY).toISOString().slice(0, 10), count: 0 }))
  for (const entry of entries) {
    const index = 29 - Math.floor((today + DAY - 1 - entry.at) / DAY)
    if (index >= 0 && index < 30) daily[index]!.count++
  }

  // Every visit the form has had (distinct visit ids with a view / start).
  const { views, starts } = visitCounts(formFillEvents(tenant, form).events)
  const stats = schemaStats(schema)
  const templateName = form.template_key
    ? (systemTemplate(form.template_key)?.name ?? findWorkspaceTemplate(tenant, form.template_key)?.name ?? null)
    : null

  const overview: FormOverview = {
    stats: {
      views,
      starts,
      responses: entries.length,
      completion_rate: completionRate(entries.length, starts),
      // Median time to fill in, from the responses (the Responses page shows the same).
      avg_seconds: medianSeconds(entries),
      last_response_at: entries[0] ? new Date(entries[0].at).toISOString() : null,
    },
    daily,
    structure: stats,
    versions: (form.versions ?? []).slice(0, 3).map(({ change_summary: _c, schema: _s, ...version }) => version),
    template: form.template_key && templateName ? { key: form.template_key, name: templateName } : null,
    theme: (schema.theme ?? {}) as Record<string, unknown>,
    preview: previewLabels(schema),
  }
  return ok(overview)
})
