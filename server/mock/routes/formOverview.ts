/**
 * Mock form overview (docs/API-CONTRACT.md → Forms): statistics, a 30-day response trend,
 * structure, latest versions and the template the form came from. Numbers are made up but stable
 * per form (seeded by its id) and agree with the form's response count; drafts have no traffic.
 * The real API computes them from responses and analytics (F11 / F18).
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
  const live = form.status !== 'draft' && form.responses_count > 0

  // Last 30 days: a share of all responses, spread with a weekly rhythm.
  const today = Date.parse(new Date().toISOString().slice(0, 10))
  const recentTotal = live ? Math.round(form.responses_count * (0.15 + random() * 0.25)) : 0
  const weights = Array.from({ length: 30 }, (_, i) => {
    const weekday = new Date(today - (29 - i) * DAY).getUTCDay()
    return (weekday === 0 || weekday === 6 ? 0.45 : 1) * (0.5 + random())
  })
  const sum = weights.reduce((a, b) => a + b, 0)
  const daily = weights.map((w, i) => ({
    date: new Date(today - (29 - i) * DAY).toISOString().slice(0, 10),
    count: Math.round((w / sum) * recentTotal),
  }))
  const lastActive = [...daily].reverse().find(day => day.count > 0)

  const starts = live ? Math.round(form.responses_count / Math.max(0.05, form.completion_rate / 100)) : 0
  const stats = schemaStats(schema)
  const templateName = form.template_key
    ? (systemTemplate(form.template_key)?.name ?? findWorkspaceTemplate(tenant, form.template_key)?.name ?? null)
    : null

  const overview: FormOverview = {
    stats: {
      views: live ? Math.round(starts * (1.3 + random() * 0.9)) : 0,
      starts,
      responses: form.responses_count,
      completion_rate: form.completion_rate,
      avg_seconds: live ? Math.round(stats.fields * (14 + random() * 10)) : null,
      last_response_at: lastActive ? new Date(Date.parse(lastActive.date) + Math.floor(random() * 10) * 3_600_000).toISOString() : null,
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
