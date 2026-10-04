/**
 * Mock form overview (docs/API-CONTRACT.md → Forms): statistics, a 30-day response trend,
 * structure, latest versions and the template the form came from. Responses, the trend and the
 * last response come from the response data (F11, decision 100); views and time to fill in are
 * estimates stable per form until analytics (F18).
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

/** Small seeded generator so a form always shows the same numbers. */
function seeded(text: string) {
  let h = 2166136261
  for (const char of text) h = Math.imul(h ^ char.charCodeAt(0), 16777619)
  return () => {
    h = Math.imul(h ^ (h >>> 15), 2246822507)
    h = Math.imul(h ^ (h >>> 13), 3266489909)
    return ((h ^= h >>> 16) >>> 0) / 4294967296
  }
}

const DAY = 86_400_000

export const getFormOverview = defineMockRoute(({ event }) => {
  const { tenant, user } = requireAuth(event)
  const form = formsOf(tenant).forms.find(item => item.id === getRouterParam(event, 'id'))
  if (form) requireLevel(form, user, 'responses')
  if (!form) throw new MockError('FRM-GEN-1004')
  const schema = ensureSchema(form, tenant)
  const random = seeded(form.id)
  // Responses, trend and last response from the real response data (decision 100), so a new
  // submission shows here at once and agrees with the Responses page.
  const entries = formResponses(tenant, form)
  const live = entries.length > 0
  const today = Date.parse(new Date().toISOString().slice(0, 10))
  const daily = Array.from({ length: 30 }, (_, i) => ({ date: new Date(today - (29 - i) * DAY).toISOString().slice(0, 10), count: 0 }))
  for (const entry of entries) {
    const index = 29 - Math.floor((today + DAY - 1 - entry.at) / DAY)
    if (index >= 0 && index < 30) daily[index]!.count++
  }

  const completion = form.completion_rate || 100
  const starts = live ? Math.round(entries.length / Math.max(0.05, completion / 100)) : 0
  const stats = schemaStats(schema)
  const templateName = form.template_key
    ? (systemTemplate(form.template_key)?.name ?? findWorkspaceTemplate(tenant, form.template_key)?.name ?? null)
    : null

  const overview: FormOverview = {
    stats: {
      views: live ? Math.round(starts * (1.3 + random() * 0.9)) : 0,
      starts,
      responses: entries.length,
      completion_rate: live ? completion : 0,
      avg_seconds: live ? Math.round(stats.fields * (14 + random() * 10)) : null,
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
