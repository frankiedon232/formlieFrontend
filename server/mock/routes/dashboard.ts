/**
 * Dashboard, Workspace view (F21 M1, docs/API-CONTRACT.md → Dashboard). Any signed-in member; every number follows
 * the person's role and folder access (responses only of forms they may see responses of; data sources, the API
 * service and the plan only when their role reaches them).
 *
 *   GET /dashboard?from=YYYY-MM-DD&to=YYYY-MM-DD&group=day|week|month|year
 *     (default: the last 30 days, grouped to fit) → WorkspaceDashboard
 */
import { DASHBOARD_GROUPS, type AttentionItem, type DashboardGroup, type DashboardPoint, type TimelineItem, type WorkspaceDashboard } from '#shared/types/dashboard'
import { bucketStart, bucketsOf, groupFor } from '#shared/utils/dashboard/buckets'
import { requireAuth } from '../core/auth'
import { ok } from '../core/respond'
import { defineMockRoute } from '../core/route'
import { advance } from '../data/billingLifecycle'
import { currentPlan } from '../data/billingStore'
import { creditsUsed } from '../data/aiStore'
import { dataSourcesOf, statusOf } from '../data/dataSourceStore'
import { canSee, responsesAllowed } from '../data/formPermissions'
import { formsOf } from '../data/formStore'
import { integrationsOf } from '../data/integrationStore'
import { apiOf } from '../data/apiStore'
import { logsOf } from '../data/apiTraffic'
import { permissionsOf } from '../data/rolesStore'
import { formResponses } from '../data/responseData'

const DAY = 86_400_000
const iso = (time: number) => new Date(time).toISOString().slice(0, 10)
const parseDay = (value: unknown) => (typeof value === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(value) ? Date.parse(value) : NaN)

export const workspaceDashboard = defineMockRoute(({ event, query }) => {
  const { tenant, user } = requireAuth(event)
  const can = permissionsOf(user, tenant)
  const today = Date.parse(iso(Date.now()))
  let to = parseDay(query.to)
  let from = parseDay(query.from)
  if (!Number.isFinite(to)) to = today
  if (!Number.isFinite(from) || from > to) from = to - 29 * DAY
  const days = Math.round((to - from) / DAY) + 1
  const group: DashboardGroup = DASHBOARD_GROUPS.includes(query.group as DashboardGroup) ? (query.group as DashboardGroup) : groupFor(days)
  const prevFrom = from - days * DAY
  const end = to + DAY - 1
  const buckets = bucketsOf(from, to, group)
  const index = new Map(buckets.map((start, i) => [start, i]))
  const series: DashboardPoint[] = buckets.map(start => ({ start, responses: 0, starts: 0, api_calls: 0 }))

  // Forms and their responses (only forms whose responses this person may see count)
  const forms = formsOf(tenant).forms.filter(form => !form.deleted_at && canSee(form, user))
  const withResponses = forms.filter(form => responsesAllowed(form, user, 'view', tenant))
  let responses = 0
  let previous = 0
  let starts = 0
  let prevStarts = 0
  let toReview = 0
  let active = 0
  let prevActive = 0
  const top: WorkspaceDashboard['top_forms'] = []
  for (const form of withResponses) {
    const rate = Math.min(0.95, Math.max(0.2, (form.completion_rate || 68) / 100))
    const entries = formResponses(tenant, form)
    const trend = buckets.map(() => 0)
    let own = 0
    let ownPrev = 0
    let ownNew = 0
    for (const entry of entries) {
      if (entry.status === 'new') ownNew++
      if (entry.at >= from && entry.at <= end) {
        own++
        const i = index.get(iso(bucketStart(entry.at, group)))
        if (i !== undefined) {
          series[i]!.responses++
          trend[i]!++
        }
      } else if (entry.at >= prevFrom && entry.at < from) ownPrev++
    }
    responses += own
    previous += ownPrev
    starts += Math.round(own / rate)
    prevStarts += Math.round(ownPrev / rate)
    toReview += ownNew
    if (own) active++
    if (ownPrev) prevActive++
    for (let i = 0; i < series.length; i++) series[i]!.starts += Math.round(trend[i]! / rate)
    if (own || ownNew) top.push({ id: form.id, name: form.name, status: form.status, responses: own, previous: ownPrev, completion_rate: Math.round(rate * 1000) / 10, to_review: ownNew, trend })
  }
  top.sort((a, b) => b.responses - a.responses || b.to_review - a.to_review)
  const rate = (sent: number, began: number) => (began ? Math.round((sent / began) * 1000) / 10 : 0)

  // What needs attention, most urgent first
  const attention: AttentionItem[] = []
  const now = Date.now()
  const inDays = (n: number) => now + n * DAY
  for (const form of forms) {
    if (form.status !== 'published') continue
    if (form.closes_at && Date.parse(form.closes_at) > now && Date.parse(form.closes_at) < inDays(7)) attention.push({ kind: 'form_closing', name: form.name, count: null, at: form.closes_at, link: `/forms/${form.id}/share` })
    if (form.response_limit && form.responses_count >= form.response_limit * 0.9) attention.push({ kind: 'form_full', name: form.name, count: form.response_limit, at: null, link: `/forms/${form.id}/share` })
  }
  const data = can.has('data.view') ? dataSourcesOf(tenant) : null
  if (data)
    for (const source of data) {
      const status = statusOf(source)
      if (status === 'failing' || status === 'attention') attention.push({ kind: status === 'failing' ? 'connection_failing' : 'connection_attention', name: source.name, count: null, at: null, link: `/data-sources/connections/${source.id}` })
    }
  const api = can.has('api.view')
  if (api)
    for (const webhook of integrationsOf(tenant).webhooks)
      if (webhook.enabled && webhook.consecutive_failures > 0) attention.push({ kind: 'webhook_failing', name: webhook.name, count: webhook.consecutive_failures, at: null, link: '/api-service/webhooks' })
  const billing = can.has('settings.view') ? advance(tenant) : null
  const plan = billing ? currentPlan(tenant) : null
  if (billing && plan) {
    const sub = billing.subscription
    const allForms = formsOf(tenant).forms.filter(form => !form.deleted_at).length
    if (plan.limits.forms !== null && allForms >= plan.limits.forms * 0.8) attention.push({ kind: 'plan_forms', name: null, count: plan.limits.forms, at: null, link: '/settings/plans' })
    if (sub.status === 'past_due') attention.push({ kind: 'payment_due', name: null, count: null, at: sub.grace_until, link: '/settings/subscription' })
    const card = sub.payment_method
    if (card && Date.UTC(card.exp_year, card.exp_month, 0) < inDays(45)) attention.push({ kind: 'card_expiring', name: null, count: null, at: new Date(Date.UTC(card.exp_year, card.exp_month, 0)).toISOString(), link: '/settings/subscription' })
  }
  const RANK: Record<AttentionItem['kind'], number> = { payment_due: 0, connection_failing: 1, webhook_failing: 2, form_full: 3, plan_forms: 4, form_closing: 5, card_expiring: 6, connection_attention: 7, to_review: 8 }
  attention.sort((a, b) => RANK[a.kind] - RANK[b.kind])
  if (toReview) attention.push({ kind: 'to_review', name: null, count: toReview, at: null, link: '/responses?review=new' })

  // What is coming up (the next 60 days)
  const timeline: TimelineItem[] = []
  for (const form of forms) {
    if (form.opens_at && Date.parse(form.opens_at) > now && Date.parse(form.opens_at) < inDays(60)) timeline.push({ kind: 'opens', name: form.name, at: form.opens_at, link: `/forms/${form.id}` })
    if (form.status === 'published' && form.closes_at && Date.parse(form.closes_at) > now && Date.parse(form.closes_at) < inDays(60)) timeline.push({ kind: 'closes', name: form.name, at: form.closes_at, link: `/forms/${form.id}` })
  }
  if (billing) {
    const sub = billing.subscription
    if (sub.next_charge && Date.parse(sub.next_charge.at) < inDays(60)) timeline.push({ kind: 'renews', name: plan ? plan.id : null, at: sub.next_charge.at, link: '/settings/subscription' })
    if (sub.scheduled) timeline.push({ kind: 'plan_change', name: sub.scheduled.plan, at: sub.scheduled.at, link: '/settings/subscription' })
  }
  timeline.sort((a, b) => Date.parse(a.at) - Date.parse(b.at))

  // The API service's calls in the chart and at a glance
  let apiArea: WorkspaceDashboard['areas']['api'] = null
  if (api) {
    const logs = logsOf(tenant, prevFrom, end)
    let calls = 0
    let before = 0
    let errors = 0
    for (const log of logs) {
      const time = Date.parse(log.at)
      if (time >= from) {
        calls++
        if (log.status >= 400) errors++
        const i = index.get(iso(bucketStart(time, group)))
        if (i !== undefined) series[i]!.api_calls++
      } else before++
    }
    apiArea = { calls, previous: before, errors, services: apiOf(tenant).services.length }
  }

  const byStatus = (status: string) => forms.filter(form => form.status === status).length
  const result: WorkspaceDashboard = {
    from: iso(from),
    to: iso(to),
    group,
    kpis: {
      responses: { value: responses, previous },
      completion_rate: { value: rate(responses, starts), previous: prevStarts ? rate(previous, prevStarts) : null },
      active_forms: { value: active, previous: prevActive },
      to_review: { value: toReview, previous: null },
      attention: { value: attention.filter(item => item.kind !== 'to_review').length, previous: null },
    },
    series,
    top_forms: top.slice(0, 6),
    attention: attention.slice(0, 8),
    timeline: timeline.slice(0, 6),
    areas: {
      forms: { total: forms.length, published: byStatus('published'), drafts: byStatus('draft'), closed: byStatus('closed') },
      data: data ? { connections: data.length, connected: data.filter(source => statusOf(source) === 'connected').length, failing: data.filter(source => statusOf(source) === 'failing').length } : null,
      api: apiArea,
      plan: plan ? { plan: plan.id, forms: formsOf(tenant).forms.filter(form => !form.deleted_at).length, forms_limit: plan.limits.forms, ai_used: creditsUsed(tenant), ai_limit: plan.limits.ai_credits } : null,
    },
  }
  return ok(result)
})
